"""Lance P.R.O.S.P.E.R en mode terminal (appelle le CLI existant, inchangé)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.interface.cli import start_cli  # noqa: E402

if __name__ == "__main__":
    start_cli()
