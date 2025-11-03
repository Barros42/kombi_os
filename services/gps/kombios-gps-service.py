#!/usr/bin/env python3
import os
import time

import struct
import pynmea2
import serial 

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date

SERIAL_PORT = "/dev/serial0" 
BAUD_RATE = 9600
HISTORIC_POSITION_FILE = "/var/log/kombios/gps/historic.position"
LAST_POSITION_FILE = "/var/log/kombios/gps/last.position"
CURRENT_POSITION_FILE = "/var/log/kombios/gps/current.position"

# Garantir que o diretório do log exista
os.makedirs(os.path.dirname(HISTORIC_POSITION_FILE), exist_ok=True)
os.makedirs(os.path.dirname(LAST_POSITION_FILE), exist_ok=True)
os.makedirs(os.path.dirname(CURRENT_POSITION_FILE), exist_ok=True)

class GpsData(BaseModel):
    timestamp: Optional[str] = Field(None, description="GPS fix timestamp")
    latitude: Optional[str] = Field(None, description="Latitude in decimal degrees")
    longitude: Optional[str] = Field(None, description="Longitude in decimal degrees")
    altitude: Optional[float] = Field(None, description="Altitude in meters")
    gps_qual: Optional[int] = Field(None, description="Quality of GPS Signal")
    datestamp: Optional[str] = Field(None, description="Date of fix")
    status: Optional[str] = Field(None, description="Status A=active, V=void")
    num_sats: Optional[int] = Field(None, description="Number of satellites used")
    speed: Optional[float] = Field(None, description="Speed in KM/h")

    def all_fields_non_null(self) -> bool:
        """Return True if all fields are non-null, otherwise False."""
        return all(value is not None for value in self.model_dump().values())

    def reset(self):
        """Set all fields to None."""
        print(f"{self.timestamp} Flushing")
        for field in self.model_fields:
            setattr(self, field, None)

def read_gps():
    print("Starting Kombi O.S. Gps Service")
    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
            gps_data = GpsData()
            while True:
                try:
                    nmea_line = ser.readline().decode('utf-8').strip()

                    msg = pynmea2.parse(nmea_line)

                    if hasattr(msg, "timestamp"):
                        gps_data.timestamp = str(msg.timestamp)

                    if hasattr(msg, "latitude"):
                        gps_data.latitude = str(msg.latitude)  

                    if hasattr(msg, "longitude"):
                        gps_data.longitude = str(msg.longitude)  

                    if hasattr(msg, "status"):
                        gps_data.status = str(msg.status)  

                    if hasattr(msg, "datestamp"):
                        gps_data.datestamp = str(msg.datestamp)  

                    if hasattr(msg, "num_sats"):
                        gps_data.num_sats = int(msg.num_sats)  

                    if hasattr(msg, "spd_over_grnd_kmph"):
                        gps_data.speed = float(msg.spd_over_grnd_kmph)  

                    if hasattr(msg, "altitude"):
                        gps_data.altitude = float(msg.altitude)  

                    if hasattr(msg, "gps_qual"):
                        gps_data.gps_qual = int(msg.gps_qual)  

                    if (gps_data.status == "V") or gps_data.all_fields_non_null():

                        if gps_data.all_fields_non_null():
                            with open(LAST_POSITION_FILE,"r+") as f:
                                f.truncate(0)
                                f.write(f"{gps_data.json()}\n")

                        with open(CURRENT_POSITION_FILE, "r+") as f:
                            f.truncate(0)
                            f.write(f"{gps_data.json()}\n")

                        with open(HISTORIC_POSITION_FILE, "a") as f:
                            f.write(f"{gps_data.json()}\n")
                            gps_data.reset()


                except Exception as e:
                    print(f"Error: {e}")
                    pass
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    read_gps()
