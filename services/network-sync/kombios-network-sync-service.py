#!/usr/bin/env python3
import os
import time
import json
import hashlib
import requests
from datetime import datetime
from typing import Tuple, Optional
from pydantic import BaseModel, ValidationError

# ==========================
# Global Configurations
# ==========================
FILE_PATH = "/var/log/kombios/network/current.data"
SERVER_URL = os.getenv("SERVER_URL")
if not SERVER_URL:
    raise RuntimeError("SERVER_URL is not defined")

POST_URL = f"{SERVER_URL}/network"
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "5"))  # Default to 5 seconds
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# ==========================
# Utility Functions
# ==========================
def log(level: str, message: str):
    print(f"[{datetime.now().isoformat(timespec='seconds')}] [{level}] {message}")

def system_serial() -> str:
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if line.startswith("Serial"):
                    return line.split(":")[1].strip()
    except Exception:
        pass
    return "unknown"

def read_file_and_hash(path: str) -> Tuple[Optional[str], Optional[str]]:
    try:
        with open(path, "rb") as f:
            content_bytes = f.read()
        content_hash = hashlib.sha256(content_bytes).hexdigest()
        content_str = content_bytes.decode(errors="ignore")
        return content_hash, content_str
    except FileNotFoundError:
        return None, None

# ==========================
# Model & Payload Builder
# ==========================
class NetworkData(BaseModel):
    status: bool | None = None
    localIp: str | None = None
    publicIp: str | None = None
    ssid: str | None = None
    wifiStatus: bool | None = None
    wifiSignalStrength: int | None = None
    lteStatus: bool | None = None
    bluetoothStatus: bool | None = None
    deviceId: str | None = None  # Optionally included for backend tracking

def build_payload(content: str) -> dict:
    raw = json.loads(content)

    model = NetworkData(
        status=raw.get("status"),
        localIp=raw.get("local_ip"),
        publicIp=raw.get("public_ip"),
        ssid=raw.get("ssid"),
        wifiStatus=raw.get("wifi_status"),
        wifiSignalStrength=raw.get("wifi_signal_strength"),
        lteStatus=raw.get("lte_status"),
        bluetoothStatus=raw.get("bluetooth_status"),
        deviceId=system_serial(),
    )

    try:
        return model.model_dump()
    except AttributeError:
        return model.dict()

# ==========================
# HTTP POST
# ==========================
def post_json(payload: dict) -> bool:
    headers = {
        "Content-Type": "application/json",
        "User-Agent": f"KombiOS/1.0.0 ({system_serial()})",
        "Kombi-Id": system_serial(),
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(POST_URL, data=json.dumps(payload), headers=headers, timeout=5)
            log("INFO", f"Server response: {resp.status_code}")
            if 200 <= resp.status_code < 300:
                return True
            else:
                try:
                    err = resp.json()
                except Exception:
                    err = resp.text
                log("WARN", f"Attempt {attempt}/{MAX_RETRIES} failed: {err}")
        except requests.RequestException as e:
            log("ERROR", f"Attempt {attempt}/{MAX_RETRIES} failed: {e}")

        if attempt < MAX_RETRIES:
            time.sleep(attempt)

    return False

# ==========================
# Main Loop (watch file hash)
# ==========================
def main():
    log("INFO", "Starting KombiOS Network sender (REST/JSON)")
    last_hash = None

    while True:
        current_hash, content = read_file_and_hash(FILE_PATH)

        if current_hash is None:
            log("WARN", f"File not found: {FILE_PATH}")
        elif current_hash != last_hash and content is not None:
            try:
                log("INFO", f"File changed, sending to {POST_URL}...")
                payload = build_payload(content)
            except (json.JSONDecodeError, ValidationError) as e:
                log("ERROR", f"Failed to build payload: {e}")
                time.sleep(CHECK_INTERVAL)
                continue

            if post_json(payload):
                log("INFO", "Data sent successfully (REST/JSON).")
                last_hash = current_hash
            else:
                log("ERROR", "Failed to send data after retries.")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("INFO", "Service interrupted by user. Exiting.")
