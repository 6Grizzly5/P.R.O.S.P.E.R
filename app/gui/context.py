"""Conteneur des services partagés par toutes les vues (injection simple)."""
from __future__ import annotations

from dataclasses import dataclass

from app.services.assistant_service import AssistantService
from app.services.career_db import CareerDB
from app.services.documents_service import DocumentsService
from app.services.email_service import EmailService
from app.services.letters_service import LettersService
from app.services.settings_service import SettingsService


@dataclass
class AppContext:
    settings: SettingsService
    db: CareerDB
    documents: DocumentsService
    letters: LettersService
    assistant: AssistantService
    email: EmailService

    @classmethod
    def create(cls, db_path=None) -> "AppContext":
        settings = SettingsService()
        db = CareerDB(db_path) if db_path else CareerDB()
        documents = DocumentsService(settings)
        letters = LettersService(documents)
        return cls(settings, db, documents, letters, AssistantService(letters),
                   EmailService(settings))
