"""Adaptateur vers le générateur de lettres existant (app.commands.letters).

La logique PDF n'est pas recopiée : on appelle `_choose_template` et `_make_pdf`
du backend. Seul l'assistant interactif (input()) est remplacé par un formulaire GUI.
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

from app.commands import letters as backend_letters
from app.services.documents_service import DocumentsService

log = logging.getLogger("prosper.letters")


class LettersService:
    def __init__(self, documents: DocumentsService):
        self.documents = documents

    @staticmethod
    def is_letter_request(text: str) -> bool:
        return backend_letters.is_letter_request(text)

    @staticmethod
    def extract_company(text: str) -> str:
        try:
            return backend_letters._extract_company(text) or ""
        except Exception:
            return ""

    def generate(self, company: str, address: str = "", recipient: str = "",
                 service: str = "") -> tuple[Path, str]:
        """Retourne (chemin du PDF, libellé du modèle utilisé)."""
        company = company.strip()
        if not company:
            raise ValueError("Le nom de l'entreprise est obligatoire.")
        template_key = backend_letters._choose_template(company)
        label = backend_letters.TEMPLATES[template_key].get("label", template_key)
        output = backend_letters._make_pdf(company, address.strip(), recipient.strip(),
                                           service.strip(), template_key)
        # Le backend écrit toujours dans Candidatures/ ; on respecte le dossier choisi
        # dans les paramètres en y déplaçant le fichier.
        target_dir = self.documents.docs_dir()
        if output.parent.resolve() != target_dir.resolve():
            dest = target_dir / output.name
            counter = 2
            while dest.exists():
                dest = target_dir / f"{output.stem}_{counter}{output.suffix}"
                counter += 1
            shutil.move(str(output), str(dest))
            output = dest
        log.info("Lettre générée : %s (modèle %s)", output.name, template_key)
        return output, label
