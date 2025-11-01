import time
import requests
import hashlib
import json

FILE_PATH = "/var/log/kombios/gps/last.position"
POST_URL = "https://play.svix.com/in/e_EdlDj9CJQaVBKc1LeAJtngzS2hh/"

def file_hash(path):
    try:
        with open(path, "rb") as f:
            content = f.read()
            return hashlib.sha256(content).hexdigest(), content.decode(errors="ignore")
    except FileNotFoundError:
        return None, None

def main():
    last_hash = None

    while True:
        current_hash, content = file_hash(FILE_PATH)
        if current_hash and current_hash != last_hash:
            try:
                print(f"[INFO] Arquivo alterado, enviando dados para {POST_URL}...")
                response = requests.post(POST_URL, data=content, timeout=5)
                print(f"[INFO] Resposta do servidor: {response.status_code}")
            except requests.RequestException as e:
                print(f"[ERRO] Falha ao enviar POST: {e}")
            last_hash = current_hash

        time.sleep(10)

if __name__ == "__main__":
    main()
