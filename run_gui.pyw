"""Lance P.R.O.S.P.E.R en mode graphique (.pyw = sans fenêtre de terminal avec pythonw)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from app.gui.main import launch_gui  # noqa: E402

if __name__ == "__main__":
    sys.exit(launch_gui())
