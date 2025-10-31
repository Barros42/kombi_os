import io
import json
import requests
import shelve
import hashlib
import serial
import pynmea2
from loggers.logger import logger

CURRENT_POSITION_FILE = "/var/log/kombios/gps/current.position"

class GpsService:
    def __init__(self, cache_file="/tmp/geo_cache.db"):
        self.url = "https://nominatim.openstreetmap.org/reverse"
        self.headers = {"User-Agent": "KombiOS-GPS/1.0"}
        self.cache_file = cache_file

    def dm_to_decimal(self, dm, direction):
        """Converte ddmm.mmmm para decimal (negativo se S/W)."""
        if not dm or not direction:
            return None
        parts = dm.split('.')
        if len(parts) < 2:
            return None
        degrees = int(parts[0][:-2])
        minutes = float(parts[0][-2:] + '.' + parts[1])
        decimal = degrees + minutes / 60
        if direction in ['S', 'W']:
            decimal *= -1
        return round(decimal, 6)

    def get_gps_coords(self):
        """Lê a última linha do arquivo de log e retorna latitude/longitude válidas."""

        gps_response = {
            "lat": 0,
            "lon": 0,
            "raw_message": None,
            "num_satellites": 0
        }

        try:
            with open(CURRENT_POSITION_FILE, "r") as f:
                last_line = f.readlines()[-1].strip()

            data = json.loads(last_line)
            gps_response["lat"] = round(float(data["latitude"]), 5)
            gps_response["lon"] = round(float(data["longitude"]), 5)
            gps_response["num_satellites"] = str(data["num_sats"])
            gps_response["raw_message"] = data

        except (FileNotFoundError, IndexError, json.JSONDecodeError) as e:
            print(f"Erro ao ler o log do GPS: {e}")

        return gps_response

    
    def _make_key(self, lat, lon):
        key = f"{round(lat, 5)}:{round(lon, 5)}"
        return hashlib.md5(key.encode()).hexdigest()

    def get_data_from_coords(self, lat, lon):
        key = self._make_key(lat, lon)
        with shelve.open(self.cache_file) as cache:
            if key in cache:
                return cache[key]

            params = {
                "lat": lat,
                "lon": lon,
                "format": "json",
                "addressdetails": 1
            }
            logger.info(f"Getting GPS location: {lat}, {lon}")

            response = requests.get(self.url, params=params, headers=self.headers)
            data = response.json()
            cache[key] = data
            return data