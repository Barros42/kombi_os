import time
import requests
import hashlib
import json
import os


SERVER_URL = os.getenv("SERVER_URL")  # não "server_url"
if not SERVER_URL:
    raise RuntimeError("SERVER_URL não definida")


FILE_PATH = "/var/log/kombios/gps/last.position"
POST_URL = os.getenv("SERVER_URL") + "/gps/last-position"

def system_serial():
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if line.startswith("Serial"):
                    return line.split(":")[1].strip()
    except Exception:
        return "unknown"

def file_hash(path):
    try:
        with open(path, "rb") as f:
            content = f.read()
            return hashlib.sha256(content).hexdigest(), content.decode(errors="ignore")
    except FileNotFoundError:
        return None, None

def get_json_payload(content):
    content_json = json.loads(content)
    gps_data = {
        "timestamp": content_json.get("timestamp"),
        "latitude": content_json.get("latitude"),
        "longitude": content_json.get("longitude"),
        "altitude": content_json.get("altitude"),
        "gpsQuality": content_json.get("gps_qual"),
        "datestamp": content_json.get("datestamp"),
        "status": content_json.get("status"),
        "numberOfSatellites": content_json.get("num_sats"),
        "speed": content_json.get("speed"),
        "deviceId": system_serial()
    }
    return json.dumps(gps_data)

def main():
    last_hash = None

    while True:
        current_hash, content = file_hash(FILE_PATH)
        if current_hash and current_hash != last_hash:
            try:
                print(f"[INFO] File changed, sending data to {POST_URL}...")
                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": f"KombiOS/1.0.0 ({system_serial()})",
                    "Kombi-Id": system_serial()
                }
                response = requests.post(POST_URL, data=get_json_payload(content), headers=headers, timeout=5)
                print(f"[INFO] Server response: {response.status_code}")
            except requests.RequestException as e:
                print(f"[ERROR] Failed to send POST: {e}")
            last_hash = current_hash

        time.sleep(5)

if __name__ == "__main__":
    main()
