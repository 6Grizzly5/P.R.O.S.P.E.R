"""Gestion des documents PDF générés (liste, suppression, regroupement par entreprise)."""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.commands.letters import CANDIDATURES_DIR
from app.services.settings_service import SettingsService

log = logging.getLogger("prosper.documents")

_NAME_RE = re.compile(r"^Lettre_stage_(?P<company>.+?)_(?P<date>\d{8})(?:_\d+)?\.pdf$", re.I)


@dataclass
class DocumentInfo:
    name: str
    path: Path
    created: datetime
    size: int
    guessed_company: str


class DocumentsService:
    def __init__(self, settings: SettingsService):
        self.settings = settings

    def docs_dir(self) -> Path:
        custom = (self.settings.get("documents_dir") or "").strip()
        folder = Path(custom) if custom else CANDIDATURES_DIR
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    @staticmethod
    def _created(stat: os.stat_result) -> datetime:
        # Sous Windows st_ctime = date de création ; ailleurs on prend la modification.
        ts = stat.st_ctime if os.name == "nt" else stat.st_mtime
        return datetime.fromtimestamp(ts)

    @staticmethod
    def guess_company(filename: str) -> str:
        match = _NAME_RE.match(filename)
        return match.group("company").replace("_", " ") if match else ""

    def list_documents(self) -> list[DocumentInfo]:
        docs: list[DocumentInfo] = []
        try:
            entries = list(self.docs_dir().glob("*.pdf"))
        except OSError as exc:
            log.error("Lecture du dossier de documents impossible : %s", exc)
            return docs
        for path in entries:
            try:
                st = path.stat()
            except OSError:
                continue
            docs.append(DocumentInfo(path.name, path, self._created(st), st.st_size,
                                     self.guess_company(path.name)))
        docs.sort(key=lambda d: d.created, reverse=True)
        return docs

    def count(self) -> int:
        return len(self.list_documents())

    def delete(self, path: Path | str) -> None:
        path = Path(path).resolve()
        if path.suffix.lower() != ".pdf":
            raise ValueError("Seuls les fichiers PDF peuvent être supprimés ici.")
        if self.docs_dir().resolve() not in path.parents:
            raise ValueError("Ce fichier est en dehors du dossier de documents.")
        path.unlink()
        log.info("Document supprimé : %s", path.name)
