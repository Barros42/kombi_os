from datetime import datetime

class TimeService:
    
    def __init__(self):
        pass
    
    def get_current_time(self):
        return datetime.now().strftime('%d/%m/%Y %H:%M:%S')
