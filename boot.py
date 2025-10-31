
import os
import time
from concurrent.futures import ThreadPoolExecutor

from rich import print
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.console import Console
from rich.text import Text
from rich.table import Column, Table
from rich.console import Group

from datetime import datetime
from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from external.hardware_service import HardwareService
from external.network_service import NetworkService
from external.time_service import TimeService
from external.gps_service import GpsService

from helpers.network_helper import NetworkHelper

# Services
hardware_service = HardwareService()
network_service = NetworkService()
time_service = TimeService()
gps_service = GpsService()


ASCII_PATH = "/home/kombios/kombi_os/files/ascii/kombi_ascii.txt"
def read_ascii_art():
    if os.path.exists(ASCII_PATH):
        with open(ASCII_PATH, "r") as f:
            return f.read()
    return "(sem ASCII art ainda)"


def build_raspberry_pi_grid():
    ram = hardware_service.get_ram_usage()
    cpu_temp = hardware_service.get_cpu_temp()
    cpu_usage = hardware_service.get_cpu_usage()
    disk = hardware_service.get_disk_usage()
    uptime = hardware_service.get_uptime()
    voltage = hardware_service.get_throttle_status()

    grid = Table.grid(expand=True, pad_edge=True)
    grid.padding = (0, 0, 2, 0)
    
    grid.add_column(justify="left")
    grid.add_column(justify="right")
    
    grid.add_row("🕒 Uptime", f"{uptime}")
    grid.add_row("🧠 CPU Usage", f"{cpu_usage}%")
    grid.add_row("📊 RAM Usage", f"{ram['used_mb']}/{ram['total_mb']} MB - {ram['percent']}%")
    grid.add_row("📀 Disk", f"{disk['used_gb']}/{disk['total_gb']}GB - {disk['percent']}%")
    grid.add_row("🔥 CPU Temp", f"{cpu_temp}")
    grid.add_row("⚡ Energy", f"{voltage}")
    
    return grid

def build_gps_grid():
    
    gps_response = gps_service.get_gps_coords()

    lat = gps_response.get("lat", 0)
    lon = gps_response.get("lon", 0)
    raw_message = gps_response.get("raw_message", "")
    num_satellites = gps_response.get("num_satellites", 0)

    is_lat_lon_defined = lat is not None and lon is not None
    gps_data = f"{lat}, {lon}" if is_lat_lon_defined else "No Singnal 🔴"

    data = gps_service.get_data_from_coords(lat,lon) if is_lat_lon_defined else {}
    city = data.get('address', {}).get('city', 'Not Found')
    state = data.get('address', {}).get('state', 'Not Found')
    road = data.get('address', {}).get('road', 'Not Found')
    postal_code = data.get('address', {}).get('postcode', 'Not Found')
    
    grid = Table.grid(expand=True, pad_edge=True)
    grid.padding = (0, 0, 2, 0)
    
    grid.add_column(justify="left")
    grid.add_column(justify="right")

    grid.add_row("🛰️ Satellites", f"{num_satellites}")
    grid.add_row("📍 Lat/Lon", f"{gps_data}")
    grid.add_row("🌎 State", f"{state}")
    grid.add_row("🏘️ City", f"{city}")
    grid.add_row("🛣️ Street", f"{road}")
    grid.add_row("📮 ZIP", f"{postal_code}")

    return grid

def build_network_grid():
    
    network_helper = NetworkHelper()
    
    bluetooth = "ON 🟢" if hardware_service.is_bluetooth_on() else "OFF 🔴"
    bluetooth_device_name = hardware_service.get_connected_bluetooth_device_name()
    wifi_data = network_service.get_wifi_info()
    wifi =  network_helper.wifi_status(wifi_data['ssid'], wifi_data['rssi_dbm']) 
    
    ip_data = network_service.get_ip_address()
    is_online = network_service.is_online()
    
    download_speed, upload_speed = network_service.get_network_usage()
    
    grid = Table.grid(expand=True, pad_edge=True)
    grid.padding = (0, 0, 2, 0)
    
    grid.add_column(justify="left")
    grid.add_column(justify="right")

    grid.add_row("🌐 Status", f"{"ON 🟢" if is_online else "OFF 🔴"}")
    grid.add_row("🌐 IP", f"{ip_data["local_ip"]}")
    grid.add_row("🛜 Wifi", f"{wifi}")
    grid.add_row("📶 LTE", "OFF 🔴")
    grid.add_row("🔵 Bluetooth", f"{bluetooth} {bluetooth_device_name}")
    grid.add_row("⬆️ Upload", f"{upload_speed/1024:.2f} KB/s")
    grid.add_row("⬇️ Download", f"{download_speed/1024:.2f} KB/s")
        
    return grid

def draw_layout() -> Layout:
    layout = Layout(name="root")

    layout.split_column(
        Layout(name="header", ratio=2),
        Layout(name="body", ratio=8),
        Layout(name="footer", ratio=1)
    )

    layout["header"].split_row(
        Layout(Panel(read_ascii_art()), ratio=3),
        Layout(name="header_panel", ratio=7),
    )
    
    layout["header"]["header_panel"].split_row(
        Layout(name="raspberry_pi"),
        Layout(name="network"),
        Layout(name="gps"),
    )


    return layout
  
def main():
    layout = draw_layout()
    # print(layout.tree)

    rasp_ref = layout["header"]["header_panel"]["raspberry_pi"]
    net_ref  = layout["header"]["header_panel"]["network"]
    gps_ref  = layout["header"]["header_panel"]["gps"]

    # agendamento por seção
    SECTIONS = {
        "rasp": {
            "interval": 1.0,
            "ref": rasp_ref,
            "title": "Raspberry Pi 💻",
            "builder": build_raspberry_pi_grid,
            "future": None,
            "next_due": 0.0,
        },
        "net": {
            "interval": 2.0,
            "ref": net_ref,
            "title": "Network 🌐",
            "builder": build_network_grid,
            "future": None,
            "next_due": 0.0,
        },
        "gps": {
            "interval": 1.0,
            "ref": gps_ref,
            "title": "GPS 🧭",
            "builder": build_gps_grid,
            "future": None,
            "next_due": 0.0,
        },
    }

    # executor com 3 workers (uma por seção)
    executor = ThreadPoolExecutor(max_workers=3)

    # título inicial
    panel = Panel(layout, title=f"Kombi O.S. v1.0.0 - {time_service.get_current_time()}")
    with Live(panel, refresh_per_second=10, screen=True, vertical_overflow="visible") as live:
        now = time.monotonic()
        last_title = now - 1.0  # força 1ª atualização do título

        while True:
            now = time.monotonic()

            # 1) Atualiza TÍTULO a cada 1s (barato, no thread principal)
            if now - last_title >= 1.0:
                live.update(Panel(layout, title=f"Kombi O.S. v1.0.0 - {time_service.get_current_time()}"))
                last_title = now

            # 2) Dispara tarefas pendentes (se chegou a hora e não há future rodando)
            for key, cfg in SECTIONS.items():
                if cfg["future"] is None and now >= cfg["next_due"]:
                    # envia para thread: apenas construir o GRID (sem tocar em Rich)
                    cfg["future"] = executor.submit(cfg["builder"])

            # 3) Consome resultados prontos (sem bloquear)
            for key, cfg in SECTIONS.items():
                fut = cfg["future"]
                if fut is not None and fut.done():
                    try:
                        grid = fut.result()  # obter grid pronto
                        # Atualiza o painel no thread principal
                        cfg["ref"].update(Panel(grid, title=cfg["title"]))
                    except Exception as e:
                        # Se algo falhar, exibe erro no painel para não quebrar a UI
                        err = Table.grid()
                        err.add_column()
                        err.add_row(f"[red]Error:[/red] {e}")
                        cfg["ref"].update(Panel(err, title=f"{cfg['title']} (error)"))
                    finally:
                        cfg["future"] = None
                        cfg["next_due"] = now + cfg["interval"]

            # 4) loop leve (cede CPU)
            time.sleep(0.30)

if __name__ == "__main__":
    main()
        
