"""Exécution en arrière-plan (QRunnable + QThreadPool) pour ne jamais figer l'interface."""
from __future__ import annotations

import logging
from typing import Callable

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal

from app.services.logging_setup import mask_secrets

log = logging.getLogger("prosper.workers")


class WorkerSignals(QObject):
    finished = pyqtSignal(object)   # résultat de la fonction
    failed = pyqtSignal(str)        # message d'erreur (secrets masqués)


class Worker(QRunnable):
    def __init__(self, fn: Callable, *args, **kwargs):
        super().__init__()
        self.fn, self.args, self.kwargs = fn, args, kwargs
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as exc:  # noqa: BLE001 — on remonte tout à l'UI
            log.exception("Erreur dans le thread de travail")
            self.signals.failed.emit(mask_secrets(str(exc)) or exc.__class__.__name__)
        else:
            self.signals.finished.emit(result)


_ACTIVE: set = set()  # garde les workers vivants jusqu'à la livraison des signaux


def run_async(fn: Callable, on_done: Callable | None = None,
              on_error: Callable | None = None, *args, **kwargs) -> Worker:
    worker = Worker(fn, *args, **kwargs)
    _ACTIVE.add(worker)

    def _release(*_):
        _ACTIVE.discard(worker)

    # Les callbacks utilisateur sont connectés avant le nettoyage : ils s'exécutent d'abord.
    if on_done:
        worker.signals.finished.connect(on_done)
    if on_error:
        worker.signals.failed.connect(on_error)
    worker.signals.finished.connect(_release)
    worker.signals.failed.connect(_release)
    QThreadPool.globalInstance().start(worker)
    return worker
