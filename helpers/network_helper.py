class NetworkHelper:
    
    def __init__(self):
        pass
    
    def wifi_status(self, ssid: str, rssi_dbm: int) -> str:

        if rssi_dbm <= -100:
            strength = 0
        elif rssi_dbm >= -50:
            strength = 100
        else:
            strength = int(2 * (rssi_dbm + 100))

        return f"{ssid} | {strength}%"
