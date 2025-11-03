#!/usr/bin/env python3
import os
import time
import json
import hashlib
import requests
import msgpack
import gzip
from datetime import datetime


# ==========================
# Configurações globais
# ==========================
FILE_PATH = "/var/log/kombios/network/current.data"
SERVER_URL = os.getenv("SERVER_URL")
POST_URL = f"{SERVER_URL}/network"
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))


# ==========================
# Funções utilitárias
# ==========================

def log(level: str, message: str):
    """Log formatado com timestamp."""
    print(f"[{datetime.now().isoformat(timespec='seconds')}] [{level}] {message}")


def system_serial() -> str:
    """Obtém o serial do dispositivo (ex: Raspberry Pi)."""
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if line.startswith("Serial"):
                    return line.split(":")[1].strip()
    except Exception:
        pass
    return "unknown"


def file_hash(path: str):
    """Calcula o hash SHA-256 e retorna também o conteúdo decodificado."""
    try:
        with open(path, "rb") as f:
            content = f.read()
            return hashlib.sha256(content).hexdigest(), content.decode(errors="ignore")
    except FileNotFoundError:
        return None, None


def get_compact_payload(content: str):
    """Extrai apenas os valores na ordem esperada e empacota em binário compactado."""
    data = json.loads(content)
    values = [
        data.get("status"),
        data.get("local_ip"),
        data.get("public_ip"),
        data.get("ssid"),
        data.get("wifi_status"),
        data.get("lte_status"),
        data.get("bluetooth_status"),
        data.get("wifi_signal_strength"),
    ]

    packed = msgpack.packb(values, use_bin_type=True)
    return gzip.compress(packed)

def post_binary(data: bytes):
    headers = {
        "Content-Type": "application/x-msgpack+gzip",
        "User-Agent": f"KombiOS/1.0.0 ({system_serial()})",
        "Kombi-Id": system_serial()
    }
    try:
        r = requests.post(POST_URL, data=data, headers=headers, timeout=5)
        log("INFO", f"Response: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        log("ERROR", str(e))
        return False


# ==========================
# Lógica principal
# ==========================

def main():
    log("INFO", "Starting ultra-compact KombiOS sender")
    last_hash = None

    while True:
        current_hash, content = file_hash(FILE_PATH)
        if current_hash and current_hash != last_hash:
            try:
                payload = get_compact_payload(content)
                if post_binary(payload):
                    log("INFO", "Data sent successfully (compressed binary).")
                    last_hash = current_hash
            except Exception as e:
                log("ERROR", str(e))
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("INFO", "Service interrupted by user. Exiting gracefully.")
