import logging
import json
from logging.handlers import RotatingFileHandler

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": self.formatTime(record, "%Y-%m-%d %H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Inclui informações extras, se existirem
        if record.__dict__.get("extra"):
            log_entry.update(record.__dict__["extra"])

        return json.dumps(log_entry, ensure_ascii=False)

def get_logger(name: str = "kombios"):
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = RotatingFileHandler(
            "/home/admin/kombi/kombios.log",
            maxBytes=2_000_000,  # 2MB
            backupCount=5
        )
        formatter = JsonFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger

# Exemplo de uso
logger = get_logger()