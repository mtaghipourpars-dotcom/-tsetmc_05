import json
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path


class Formatter(logging.Formatter):
    def format(self, record):
        return json.dumps({'at': datetime.now(timezone.utc).isoformat(),
                           'level': record.levelname, 'event': record.getMessage()}, ensure_ascii=False)


def configure(path: str):
    logger = logging.getLogger('market')
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        for handler in (logging.StreamHandler(), RotatingFileHandler(path, maxBytes=10_000_000, backupCount=5)):
            handler.setFormatter(Formatter())
            logger.addHandler(handler)
    # HTTPX logs URLs including query strings. Do not enable upstream debug logging.
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    return logger
