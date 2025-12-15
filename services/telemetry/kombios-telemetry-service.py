#!/usr/bin/env python3
import os
import subprocess
import time
from typing import Optional, Tuple
from pydantic import BaseModel, Field

DATA_FILE = "/var/log/kombios/telemetry/current.data"
UPDATE_INTERVAL_SEC = int(os.getenv("SYSTEM_UPDATE_INTERVAL_SEC", "60"))
CMD_TIMEOUT_SEC = 3

# ----------------------------
# Data model – System Telemetry
# ----------------------------
class SystemTelemetryData(BaseModel):
    uptime_seconds: Optional[int] = Field(None)
    kernel_warnings: Optional[int] = Field(None)

    soc_temperature_celsius: Optional[float] = Field(None)
    soc_temp_max_celsius: Optional[float] = Field(None)
    overheat_events: Optional[int] = Field(None)

    cpu_usage_percent: Optional[float] = Field(None)
    load_avg_1m: Optional[float] = Field(None)
    cpu_freq_mhz: Optional[int] = Field(None)

    ram_used_mb: Optional[int] = Field(None)
    ram_total_mb: Optional[int] = Field(None)
    swap_used_mb: Optional[int] = Field(None)
    swap_total_mb: Optional[int] = Field(None)

    sd_free_mb: Optional[int] = Field(None)
    sd_total_mb: Optional[int] = Field(None)
    sd_usage_percent: Optional[float] = Field(None)
    fs_readonly: Optional[bool] = Field(None)

    disk_read_bytes: Optional[int] = Field(None)
    disk_write_bytes: Optional[int] = Field(None)
    io_wait_percent: Optional[float] = Field(None)

    undervoltage_detected: Optional[bool] = Field(None)
    throttling_detected: Optional[bool] = Field(None)
    throttled_flags: Optional[int] = Field(None)

    def all_fields_non_null(self) -> bool:
        return all(value is not None for value in self.model_dump().values())

# ----------------------------
# Helpers
# ----------------------------
def ensure_dir_for(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)

def run_cmd(args: list[str]) -> Optional[str]:
    try:
        out = subprocess.check_output(
            args, stderr=subprocess.STDOUT, timeout=CMD_TIMEOUT_SEC
        )
        return out.decode().strip()
    except Exception:
        return None

# ----------------------------
# Collectors
# ----------------------------
def get_uptime_seconds() -> Optional[int]:
    out = run_cmd(["cat", "/proc/uptime"])
    if out:
        return int(float(out.split()[0]))
    return None

def get_kernel_warnings() -> Optional[int]:
    out = run_cmd(["dmesg", "--level=warn,err"])
    if out:
        return len(out.splitlines())
    return None

def get_soc_temperature() -> Optional[float]:
    out = run_cmd(["vcgencmd", "measure_temp"])
    if out and "=" in out:
        return float(out.split("=")[1].replace("'C", ""))
    return None

def get_cpu_freq_mhz() -> Optional[int]:
    out = run_cmd(["vcgencmd", "measure_clock", "arm"])
    if out and "=" in out:
        return int(int(out.split("=")[1]) / 1_000_000)
    return None

def get_load_avg_1m() -> Optional[float]:
    out = run_cmd(["cat", "/proc/loadavg"])
    if out:
        return float(out.split()[0])
    return None

def get_cpu_usage_percent() -> Optional[float]:
    out1 = run_cmd(["cat", "/proc/stat"])
    time.sleep(0.5)
    out2 = run_cmd(["cat", "/proc/stat"])
    if not out1 or not out2:
        return None

    def parse(line):
        parts = list(map(int, line.split()[1:]))
        idle = parts[3]
        total = sum(parts)
        return idle, total

    idle1, total1 = parse(out1.splitlines()[0])
    idle2, total2 = parse(out2.splitlines()[0])

    idle_delta = idle2 - idle1
    total_delta = total2 - total1

    if total_delta == 0:
        return None

    return round(100 * (1 - idle_delta / total_delta), 2)

def get_ram_stats() -> Tuple[Optional[int], Optional[int]]:
    out = run_cmd(["free", "-m"])
    if not out:
        return None, None
    parts = out.splitlines()[1].split()
    return int(parts[2]), int(parts[1])

def get_swap_stats() -> Tuple[Optional[int], Optional[int]]:
    out = run_cmd(["free", "-m"])
    if not out:
        return None, None
    parts = out.splitlines()[2].split()
    return int(parts[2]), int(parts[1])

def get_sd_stats():
    out = run_cmd(["df", "-m", "/"])
    if not out:
        return None, None, None, None
    parts = out.splitlines()[1].split()
    total = int(parts[1])
    free = int(parts[3])
    used_pct = round((total - free) / total * 100, 1)
    fs_readonly = "ro," in (run_cmd(["mount"]) or "")
    return free, total, used_pct, fs_readonly

def get_disk_io():
    out = run_cmd(["cat", "/proc/diskstats"])
    if not out:
        return None, None

    for line in out.splitlines():
        if " mmcblk0 " in line:
            parts = line.split()
            return int(parts[5]) * 512, int(parts[9]) * 512
    return None, None

def get_iowait_percent() -> Optional[float]:
    out = run_cmd(["iostat", "-c", "1", "2"])
    if out:
        lines = out.splitlines()
        for line in reversed(lines):
            if line.strip().startswith("avg-cpu"):
                continue
            if "%" not in line and len(line.split()) >= 6:
                return float(line.split()[3])
    return None

def get_throttling():
    out = run_cmd(["vcgencmd", "get_throttled"])
    if not out or "=" not in out:
        return None, None, None

    flags = int(out.split("=")[1], 16)
    undervoltage = bool(flags & 0x1 or flags & 0x10000)
    throttled = bool(flags & 0x2 or flags & 0x20000)

    return undervoltage, throttled, flags

# ----------------------------
# Main
# ----------------------------
def run_once():
    ensure_dir_for(DATA_FILE)

    max_temp = 0.0
    overheat_events = 0

    data = SystemTelemetryData()

    data.uptime_seconds = get_uptime_seconds()
    data.kernel_warnings = get_kernel_warnings()

    temp = get_soc_temperature()
    if temp is not None:
        data.soc_temperature_celsius = temp
        max_temp = temp
        if temp >= 80:
            overheat_events = 1

    data.soc_temp_max_celsius = max_temp
    data.overheat_events = overheat_events

    data.cpu_usage_percent = get_cpu_usage_percent()
    data.load_avg_1m = get_load_avg_1m()
    data.cpu_freq_mhz = get_cpu_freq_mhz()

    data.ram_used_mb, data.ram_total_mb = get_ram_stats()
    data.swap_used_mb, data.swap_total_mb = get_swap_stats()

    (
        data.sd_free_mb,
        data.sd_total_mb,
        data.sd_usage_percent,
        data.fs_readonly,
    ) = get_sd_stats()

    data.disk_read_bytes, data.disk_write_bytes = get_disk_io()
    data.io_wait_percent = get_iowait_percent()

    (
        data.undervoltage_detected,
        data.throttling_detected,
        data.throttled_flags,
    ) = get_throttling()

    if not data.all_fields_non_null():
        print("Telemetry incomplete:", data.model_dump())
        return

    with open(DATA_FILE, "w") as f:
        f.write(data.model_dump_json() + "\n")

    print("System telemetry written successfully.")

# ----------------------------
# Entrypoint
# ----------------------------
if __name__ == "__main__":
    run_once()