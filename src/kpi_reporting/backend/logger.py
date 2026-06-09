import logging
from typing import Optional

from .._metadata import app_name

logger = logging.getLogger(app_name)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    if name is None:
        return logger
    return logging.getLogger(name)
