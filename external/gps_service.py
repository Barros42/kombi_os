import requests
import shelve
import hashlib
import serial
import pynmea2
from loggers.logger import logger

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

    def get_gps_coords(self, port="/dev/serial0", baud=9600):
        """Lê da serial e retorna a primeira latitude/longitude válidas."""
        with serial.Serial(port, baud, timeout=1) as ser:
            while True:
                line = ser.readline().decode('ascii', errors='replace').strip()
                if line.startswith('$GPGGA') or line.startswith('$GPRMC'):
                    try:
                        msg = pynmea2.parse(line)
                        if hasattr(msg, 'lat') and hasattr(msg, 'lon') and msg.lat and msg.lon:
                            lat = self.dm_to_decimal(msg.lat, msg.lat_dir)
                            lon = self.dm_to_decimal(msg.lon, msg.lon_dir)
                            return lat, lon
                    except pynmea2.ParseError:
                        continue

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