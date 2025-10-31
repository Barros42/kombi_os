import socket
import subprocess
import shutil
import re
import psutil
import time

class NetworkService:
    
    def get_local_ip(self):
        """Retorna o IP local (LAN)"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))  # conecta sem enviar pacotes
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def get_public_ip(self):
        """Retorna o IP público (externo)"""
        try:
            ip = requests.get("https://api.ipify.org", timeout=2).text
            return ip
        except Exception:
            return "Unavailable"

    def get_ip_address(self):
        """Retorna ambos IPs em um dicionário"""
        return {
            "local_ip": self.get_local_ip(),
            "public_ip": self.get_public_ip(),
        }
        
    def is_online(self, host="8.8.8.8", port=53, timeout=2):
        """
        Verifica se há conexão com a Internet.
        Faz uma tentativa de conexão TCP sem enviar dados.
        Retorna True se estiver online, False caso contrário.
        """
        try:
            socket.setdefaulttimeout(timeout)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, port))
            s.close()
            return True
        except OSError:
            return False
    
    def _run(self, cmd):
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
            return out.strip()
        except Exception:
            return ""
    
    def _wifi_iface(self):
        # Descobre a interface wireless "managed" (ex.: wlan0)
        if shutil.which("iw"):
            out = self._run(["iw", "dev"])
            m = re.search(r"Interface\s+([^\s]+).*?type\s+managed", out, re.S)
            if m:
                return m.group(1)
        return "wlan0"  # padrão típico no Raspberry Pi OS
    
    def get_wifi_info(self):
        iface = self._wifi_iface()

        # 1) Tenta iwgetid (retorna somente SSID)
        if shutil.which("iwgetid"):
            ssid = self._run(["iwgetid", "-r"])
            if ssid:
                info = {"ssid": ssid, "bssid": None, "rssi_dbm": None}
                # Pega BSSID/RSSI via iw link (opcional)
                if shutil.which("iw"):
                    link = self._run(["iw", "dev", iface, "link"])
                    m_bssid = re.search(r"Connected to\s+([0-9a-f:]{17})", link, re.I)
                    m_sig   = re.search(r"signal:\s*(-?\d+)\s*dBm", link, re.I)
                    if m_bssid: info["bssid"] = m_bssid.group(1).lower()
                    if m_sig:   info["rssi_dbm"] = int(m_sig.group(1))
                return info

        # 2) Fallback: iw link (pega tudo de uma vez)
        if shutil.which("iw"):
            link = self._run(["iw", "dev", iface, "link"])
            if "Connected to" in link:
                m_ssid  = re.search(r"SSID:\s*(.+)", link)
                m_bssid = re.search(r"Connected to\s+([0-9a-f:]{17})", link, re.I)
                m_sig   = re.search(r"signal:\s*(-?\d+)\s*dBm", link, re.I)
                return {
                    "ssid": m_ssid.group(1).strip() if m_ssid else None,
                    "bssid": m_bssid.group(1).lower() if m_bssid else None,
                    "´": int(m_sig.group(1)) if m_sig else None,
                }

        # 3) Fallback: wpa_cli
        if shutil.which("wpa_cli"):
            out = NetworkService._run(["wpa_cli", "-i", iface, "status"])
            if "wpa_state=COMPLETED" in out:
                m_ssid  = re.search(r"^ssid=(.+)$", out, re.M)
                m_bssid = re.search(r"^bssid=([0-9a-f:]{17})$", out, re.M|re.I)
                return {
                    "ssid": m_ssid.group(1).strip() if m_ssid else None,
                    "bssid": m_bssid.group(1).lower() if m_bssid else None,
                    "rssi_dbm": None,  # wpa_cli não traz RSSI aqui por padrão
                }

        return {"ssid": None, "bssid": None, "rssi_dbm": None}
    
    def get_network_usage(self, interval=1):
        net1 = psutil.net_io_counters()
        time.sleep(interval)
        
        net2 = psutil.net_io_counters()

        download_speed = (net2.bytes_recv - net1.bytes_recv) / interval
        upload_speed   = (net2.bytes_sent - net1.bytes_sent) / interval

        return download_speed, upload_speed