"""Journalisation de l'interface graphique (fichier tournant, secrets masqués)."""
from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler

from app.core.config import DATA_DIR

LOG_DIR = DATA_DIR / "logs"
LOG_FILE = LOG_DIR / "prosper_gui.log"

# Clés Google (AIza...), jetons OAuth (ya29...), paramètres key=... dans une URL.
_SECRET_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),
    re.compile(r"ya29\.[0-9A-Za-z_\-]{20,}"),
    re.compile(r"(?i)(api[_-]?key|key|token|secret)=([^&\s'\"]+)"),
]


def mask_secrets(text: str) -> str:
    """Remplace tout ce qui ressemble à une clé/jeton par des étoiles."""
    text = str(text)
    text = _SECRET_PATTERNS[0].sub("***", text)
    text = _SECRET_PATTERNS[1].sub("***", text)
    text = _SECRET_PATTERNS[2].sub(lambda m: f"{m.group(1)}=***", text)
    return text


class _MaskingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.msg = mask_secrets(record.getMessage())
            record.args = ()
        except Exception:  # un filtre ne doit jamais casser le logging
            pass
        return True


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("prosper")
    if logger.handlers:
        return logger
    logger.setLevel(level)
    handler = RotatingFileHandler(
        LOG_FILE, maxBytes=512_000, backupCount=2, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
    )
    handler.addFilter(_MaskingFilter())
    logger.addHandler(handler)
    logger.propagate = False
    return logger
