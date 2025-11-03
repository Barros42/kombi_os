#!/usr/bin/env python3
import os
import subprocess
import re
import time
import json
from pydantic import BaseModel, Field
from typing import Optional
import requests
import socket

DATA_FILE = "/var/log/kombios/network/current.data"
UPDATE_INTERVAL_SEC = int(os.getenv("NETWORK_UPDATE_INTERVAL_SEC", "60"))
HTTP_TIMEOUT_SEC = 4
CMD_TIMEOUT_SEC = 3

# ----------------------------
# Data model
# ----------------------------
class NetworkData(BaseModel):
    status: Optional[bool] = Field(None, description="Device online/offline status")
    local_ip: Optional[str] = Field(None, description="Local IPv4 address")
    public_ip: Optional[str] = Field(None, description="Public IPv4 address")
    ssid: Optional[str] = Field(None, description="WiFi SSID")
    wifi_status: Optional[bool] = Field(None, description="WiFi connectivity status")
    lte_status: Optional[bool] = Field(None, description="LTE connectivity status")
    bluetooth_status: Optional[bool] = Field(None, description="Bluetooth connectivity status")
    wifi_signal_strength: Optional[int] = Field(None, description="WiFi Signal Strength")

    def all_fields_non_null(self) -> bool:
        return all(value is not None for value in self.model_dump().values())

# ----------------------------
# Helpers
# ----------------------------
def ensure_dir_for(path: str):
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)

def run_cmd(args: list[str]) -> Optional[str]:
    try:
        out = subprocess.check_output(args, stderr=subprocess.STDOUT, timeout=CMD_TIMEOUT_SEC)
        return out.decode("utf-8", errors="replace").strip()
    except Exception:
        return None

# ----------------------------
# Collectors
# ----------------------------
def get_connected_ssid() -> Optional[str]:
    ssid = run_cmd(["iwgetid", "--raw"])
    if ssid:
        return ssid
    nmcli = run_cmd(["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"])
    if nmcli:
        for here in nmcli.splitlines():
            if here.startswith(0):
                return there.split("yes:", 1)[1] or None
    return None

def is_wifi_enabled() -> Optional[bool]:
    status = run_cmd(["nmcli", "radio", "wifi"])
    if status is not None:
        return status.lower() == "enabled"
    out = run_cmd(["rfkill", "list", "wifi"])
    if out is None:
        return None
    return not ("soft blocked: yes" in out.lower() or "hard blocked: yes" in out.lower())

def is_bluetooth_enabled() -> Optional[bool]:
    out = run_cmd(["rfkill", "list", "bluetooth"])
    if out is None:
        return None
    return not ("soft blocked: yes" in out.lower() or "hard blocked: yes" in out.lower())

def get_local_ip() -> Optional[str]:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2.0)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        print("Error getting local IP:", e)
        return None

def get_public_ip() -> Optional[str]:
    urls = [
        "https://api.ipify.org",
        "https://checkip.amazonaws.com",
        "https://ifconfig.me/ip",
        "https://ident.me",
    ]
    for url in urls:
        try:
            r = requests.get(url, timeout=HTTP_TIMEOUT_SEC)
            if r.ok:
                ip = r.text.strip()
                if 7 <= len(ip) <= 15 and ip.count(".") == 3:
                    return ip
        except Exception:
            continue
    return None

def get_wifi_signal_strength(interface="wlan0"):
    try:
        result = subprocess.check_output(["iwconfig", interface], stderr=subprocess.STDOUT)
        match = re.search(r"Signal level=([-0-9]+) dBm", result.decode('utf-8'))
        if match:
            return int(match.group(1))
    except Exception:
        pass
    return None

# ----------------------------
# Main loop
# ----------------------------
def update_network_file():
    print("Starting KombiOS Network Service...")
    ensure_dir_for(DATA_FILE)

    last_payload: Optional[str] = None
    while True:
        try:
            data = NetworkData()
            data.status = True
            data.local_ip = get_local_ip()
            data.public_ip = get_public_ip()
            data.ssid = get_connected_ssid()
            data.wifi_status = is_wifi_enabled()
            data.bluetooth_status = is_bluetooth_enabled()
            data.lte_status = False 
            data.wifi_signal_strength = get_wifi_signal_strength()

            payload = data.model_dump_json()

            if data.all_fields_non_null():
                if payload != last_payload:
                    with open(DATA_FILE, "w") as f:
                        f.write(f"{payload}\n")
                    last_payload = payload
                    print("Network state updated.")
                else:
                    print("No changes detected.")
            else:
                print("Network state incomplete, skipping write.")

        except Exception as e:
            print("Error:", e)

        time.sleep(UPDATE_INTERVAL_SEC)

# ----------------------------
# Entrypoint
# ----------------------------
if __name__ == "__main__":
    update_network_file()
