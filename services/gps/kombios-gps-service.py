#!/usr/bin/env python3
import time
import serial  # pip install pyserial
import os

SERIAL_PORT = "/dev/serial0" 
BAUD_RATE = 9600
LOG_FILE = "/var/log/kombios/gps/data.log"

# Garantir que o diretório do log exista
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

def read_gps():
    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
            while True:
                linha = ser.readline().decode('utf-8').strip()
                if linha:
                    with open(LOG_FILE, "a") as f:
                        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {linha}\n")
    except Exception as e:
        with open(LOG_FILE, "a") as f:
            f.write(f"Erro: {e}\n")

if __name__ == "__main__":
    read_gps()
