from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent

DATA_DIR = BASE_DIR / "data"

MEMORY_FILE = DATA_DIR / "memory.json"
HISTORY_FILE = DATA_DIR / "history.json"


APP_NAME = "P.R.O.S.P.E.R."
VERSION = "0.2.0"


DATA_DIR.mkdir(exist_ok=True)