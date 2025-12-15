#!/usr/bin/env python3
import os
import json
import hashlib
import requests
from datetime import datetime
from typing import Tuple, Optional
from pydantic import BaseModel, ValidationError

# ==========================
# Global Configurations
# ==========================
FILE_PATH = "/var/log/kombios/telemetry/current.data"

SERVER_URL = os.getenv("SERVER_URL")
if not SERVER_URL:
    raise RuntimeError("SERVER_URL is not defined")

POST_URL = f"{SERVER_URL}/telemetry"
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

def read_last_hash(path: str) -> Optional[str]:
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

def write_last_hash(path: str, value: str):
    with open(path, "w") as f:
        f.write(value)

# ==========================
# Model & Payload Builder
# ==========================
class DeviceTelemetryData(BaseModel):
    uptimeSeconds: int | None = None
    kernelWarnings: int | None = None
    socTemperatureCelsius: float | None = None
    socTempMaxCelsius: float | None = None
    overheatEvents: int | None = None
    cpuUsagePercent: float | None = None
    loadAvg1m: float | None = None
    cpuFreqMhz: int | None = None
    ramUsedMb: int | None = None
    ramTotalMb: int | None = None
    swapUsedMb: int | None = None
    swapTotalMb: int | None = None
    sdFreeMb: int | None = None
    sdTotalMb: int | None = None
    sdUsagePercent: float | None = None
    fsReadonly: bool | None = None
    diskReadBytes: int | None = None
    diskWriteBytes: int | None = None
    ioWaitPercent: float | None = None
    undervoltageDetected: bool | None = None
    throttlingDetected: bool | None = None
    throttledFlags: int | None = None
    deviceId: str | None = None

def build_payload(content: str) -> dict:
    raw = json.loads(content)

    model = DeviceTelemetryData(
        uptimeSeconds=raw.get("uptime_seconds"),
        kernelWarnings=raw.get("kernel_warnings"),
        socTemperatureCelsius=raw.get("soc_temperature_celsius"),
        socTempMaxCelsius=raw.get("soc_temp_max_celsius"),
        overheatEvents=raw.get("overheat_events"),
        cpuUsagePercent=raw.get("cpu_usage_percent"),
        loadAvg1m=raw.get("load_avg_1m"),
        cpuFreqMhz=raw.get("cpu_freq_mhz"),
        ramUsedMb=raw.get("ram_used_mb"),
        ramTotalMb=raw.get("ram_total_mb"),
        swapUsedMb=raw.get("swap_used_mb"),
        swapTotalMb=raw.get("swap_total_mb"),
        sdFreeMb=raw.get("sd_free_mb"),
        sdTotalMb=raw.get("sd_total_mb"),
        sdUsagePercent=raw.get("sd_usage_percent"),
        fsReadonly=raw.get("fs_readonly"),
        diskReadBytes=raw.get("disk_read_bytes"),
        diskWriteBytes=raw.get("disk_write_bytes"),
        ioWaitPercent=raw.get("io_wait_percent"),
        undervoltageDetected=raw.get("undervoltage_detected"),
        throttlingDetected=raw.get("throttling_detected"),
        throttledFlags=raw.get("throttled_flags"),
        deviceId=system_serial(),
    )

    try:
        return model.model_dump(exclude_none=True)
    except AttributeError:
        return model.dict(exclude_none=True)

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
            resp = requests.post(
                POST_URL,
                data=json.dumps(payload),
                headers=headers,
                timeout=5,
            )
            log("INFO", f"Server response: {resp.status_code}")
            if 200 <= resp.status_code < 300:
                return True
            else:
                log("WARN", f"Attempt {attempt}/{MAX_RETRIES} failed: {resp.text}")
        except requests.RequestException as e:
            log("ERROR", f"Attempt {attempt}/{MAX_RETRIES} failed: {e}")

    return False

# ==========================
# One-shot Main
# ==========================
def main():
    log("INFO", "Running KombiOS Telemetry sender (one-shot)")

    current_hash, content = read_file_and_hash(FILE_PATH)
    if current_hash is None or content is None:
        log("WARN", f"Telemetry file not found: {FILE_PATH}")
        return

    last_hash = read_last_hash("/var/log/kombios/telemetry-sync/.last_hash")
    if current_hash == last_hash:
        log("INFO", "Telemetry unchanged, skipping send.")
        return

    try:
        payload = build_payload(content)
    except (json.JSONDecodeError, ValidationError) as e:
        log("ERROR", f"Failed to build payload: {e}")
        return

    if post_json(payload):
        log("INFO", "Telemetry sent successfully.")
        write_last_hash("/var/log/kombios/telemetry-sync/.last_hash", current_hash)
    else:
        log("ERROR", "Failed to send telemetry.")

if __name__ == "__main__":
    main()
