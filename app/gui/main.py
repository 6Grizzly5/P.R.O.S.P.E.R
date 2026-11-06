"""Point d'entrée de l'interface graphique : `launch_gui()`."""
from __future__ import annotations

import logging
import sys
import traceback

from PyQt6.QtWidgets import QApplication, QMessageBox

from app.core.config import APP_NAME
from app.services.logging_setup import mask_secrets, setup_logging


def _install_excepthook(log: logging.Logger) -> None:
    def hook(exc_type, exc, tb):
        text = mask_secrets("".join(traceback.format_exception(exc_type, exc, tb)))
        log.error("Exception non gérée :\n%s", text)
        try:
            QMessageBox.critical(None, APP_NAME, "Une erreur inattendue est survenue.\n"
                                 "Les détails sont dans data/logs/prosper_gui.log.")
        except Exception:
            pass
    sys.excepthook = hook


def launch_gui() -> int:
    log = setup_logging()
    _install_excepthook(log)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("P.R.O.S.P.E.R")

    from app.gui.context import AppContext
    from app.gui.main_window import MainWindow

    ctx = AppContext.create()
    window = MainWindow(ctx, app)
    window.show()
    log.info("Interface graphique démarrée.")
    code = app.exec()
    log.info("Interface graphique fermée (code %s).", code)
    return code
