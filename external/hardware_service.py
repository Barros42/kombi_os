import os
import time
import psutil
import subprocess
from loggers.logger import logger


class HardwareService:
    
    def __init__(self):
        pass
    
    def get_ram_usage(self) -> dict:
        mem = psutil.virtual_memory()
        used_mb = mem.used / 1024 / 1024
        total_mb = mem.total / 1024 / 1024
        percent = mem.percent
        return {
            "used_mb": round(used_mb, 2),
            "total_mb": round(total_mb, 2),
            "percent": percent
        }
        
    def get_cpu_temp(self):

        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = int(f.readline()) / 1000
                return f"{temp:.1f}°C"
        except Exception:
            logger.error(f"Fail in Get CPU Temperature")
            return "N/D"
        
    def get_cpu_usage(self):
        """Return current CPU usage as a percentage."""
        return psutil.cpu_percent(interval=1)
    
    def get_disk_usage(self, path="/"):
        """Return disk usage for a given path (in GB and %)."""
        disk = psutil.disk_usage(path)
        total_gb = disk.total / (1024 ** 3)
        used_gb = disk.used / (1024 ** 3)
        free_gb = disk.free / (1024 ** 3)
        percent = disk.percent
        return {
            "total_gb": round(total_gb, 2),
            "used_gb": round(used_gb, 2),
            "free_gb": round(free_gb, 2),
            "percent": percent
        }
        
    def get_uptime(self):
        """Return system uptime as a human-readable string."""
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time

        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)

        return f"{days}d {hours}h {minutes}m"
    
    def is_bluetooth_on(self) -> bool:
        """Return True if the Bluetooth service is active, False otherwise."""
        try:
            # Checa o status do serviço bluetooth
            result = subprocess.run(
                ["systemctl", "is-active", "bluetooth"],
                capture_output=True,
                text=True,
                check=False
            )

            return result.stdout.strip() == "active"
        except Exception as e:
            print(f"Error checking Bluetooth status: {e}")
            return False
    
    def get_connected_bluetooth_device_name(self) -> str:
        """
        Retorna o nome do dispositivo Bluetooth conectado, se houver.
        Caso não haja conexão, retorna 'No device connected'.
        """
        
        no_device_message = ""
        
        try:
            # Executa bluetoothctl para listar dispositivos conectados
            result = subprocess.run(
                ["bluetoothctl", "info"],
                capture_output=True,
                text=True,
                check=False
            )

            output = result.stdout.strip()

            if not output:
                return no_device_message

            # Procura pelo campo 'Name:'
            for line in output.splitlines():
                if line.strip().startswith("Name:"):
                    return line.split("Name:", 1)[1].strip()

            return no_device_message

        except Exception as e:
            print(f"Error checking connected Bluetooth device: {e}")
            return no_device_message    
    
    def get_throttle_status(self):
        try:
            result = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True, text=True)
            code = int(result.stdout.strip().split('=')[1], 16)
            
            message = None

            if code & 0x40000:
                message = "Throttling has occurred"
            return message or "OK"
        except Exception as e:
            return [f"Error checking throttle status: {e}"]
        