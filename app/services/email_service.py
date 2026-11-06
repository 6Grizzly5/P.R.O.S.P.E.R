"""Couche e-mail : message, validation, construction MIME, fournisseurs d'envoi.

SÉCURITÉ : ce module n'envoie jamais rien tout seul. `EmailService.send()` n'est appelé
que par l'interface, après la fenêtre de confirmation explicite. Aucun mot de passe n'est
stocké : le fournisseur Gmail utilise OAuth 2.0 (jeton dans data/gmail_token.json).
Si un fournisseur n'est pas prêt, l'envoi échoue avec une erreur claire — jamais de faux succès.
"""
from __future__ import annotations

import base64
import logging
import mimetypes
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from email.message import EmailMessage
from pathlib import Path

from app.core.config import DATA_DIR
from app.services.career_db import is_valid_email
from app.services.settings_service import SettingsService

log = logging.getLogger("prosper.email")

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
GMAIL_TOKEN_FILE = DATA_DIR / "gmail_token.json"
MAX_ATTACHMENTS_BYTES = 20 * 1024 * 1024  # Gmail limite à ~25 Mo ; marge de sécurité


class EmailError(Exception):
    """Erreur d'envoi (message lisible par l'utilisateur)."""


class EmailNotConfigured(EmailError):
    """Le fournisseur n'est pas configuré / pas disponible."""


@dataclass
class EmailData:
    to: list[str] = field(default_factory=list)
    cc: list[str] = field(default_factory=list)
    bcc: list[str] = field(default_factory=list)
    subject: str = ""
    body_html: str = ""
    body_text: str = ""
    attachments: list[str] = field(default_factory=list)


def split_addresses(raw: str) -> list[str]:
    return [a.strip() for a in re.split(r"[;,\n]+", raw or "") if a.strip()]


def validate(msg: EmailData) -> tuple[list[str], list[str]]:
    """Retourne (erreurs bloquantes, avertissements)."""
    errors, warnings = [], []
    if not msg.to:
        errors.append("Aucun destinataire.")
    for label, addrs in (("À", msg.to), ("Cc", msg.cc), ("Cci", msg.bcc)):
        for addr in addrs:
            if not is_valid_email(addr):
                errors.append(f"Adresse invalide dans « {label} » : {addr}")
    total = 0
    for att in msg.attachments:
        p = Path(att)
        if not p.is_file():
            errors.append(f"Pièce jointe introuvable : {p.name}")
        else:
            total += p.stat().st_size
    if total > MAX_ATTACHMENTS_BYTES:
        errors.append("Les pièces jointes dépassent 20 Mo au total.")
    if not msg.subject.strip():
        warnings.append("L'objet est vide.")
    if not msg.body_text.strip():
        warnings.append("Le corps du message est vide.")
    if not msg.attachments:
        warnings.append("Aucune pièce jointe.")
    return errors, warnings


def build_mime(msg: EmailData, sender: str = "") -> EmailMessage:
    mime = EmailMessage()
    if sender:
        mime["From"] = sender
    mime["To"] = ", ".join(msg.to)
    if msg.cc:
        mime["Cc"] = ", ".join(msg.cc)
    if msg.bcc:
        mime["Bcc"] = ", ".join(msg.bcc)
    mime["Subject"] = msg.subject
    mime.set_content(msg.body_text or " ")
    if msg.body_html.strip():
        mime.add_alternative(msg.body_html, subtype="html")
    for att in msg.attachments:
        path = Path(att)
        ctype, encoding = mimetypes.guess_type(path.name)
        maintype, subtype = (ctype or "application/octet-stream").split("/", 1)
        if encoding:
            maintype, subtype = "application", "octet-stream"
        mime.add_attachment(path.read_bytes(), maintype=maintype, subtype=subtype,
                            filename=path.name)
    return mime


class EmailProvider(ABC):
    name = "abstract"

    @abstractmethod
    def readiness(self) -> tuple[bool, str]:
        """(prêt ?, explication lisible)."""

    @abstractmethod
    def send(self, msg: EmailData) -> str:
        """Envoie réellement le message. Retourne un identifiant. Lève EmailError sinon."""


class GmailApiProvider(EmailProvider):
    """Envoi via l'API Gmail (OAuth 2.0, portée gmail.send uniquement).

    Prérequis (voir README_GUI.md) : un fichier credentials.json « Application de bureau »
    créé dans Google Cloud Console + `pip install google-api-python-client google-auth-oauthlib`.
    NB : implémenté selon la documentation officielle mais non testé sur un vrai compte.
    """

    name = "Gmail (API OAuth 2.0)"

    def __init__(self, settings: SettingsService):
        self.settings = settings

    def _credentials_file(self) -> Path | None:
        raw = (self.settings.get("gmail_credentials_path") or "").strip()
        return Path(raw) if raw else None

    def readiness(self) -> tuple[bool, str]:
        try:
            import google.oauth2.credentials  # noqa: F401
            import google_auth_oauthlib.flow  # noqa: F401
            import googleapiclient.discovery  # noqa: F401
        except ImportError:
            return False, ("Bibliothèques Google manquantes. Installez-les avec : "
                           "pip install google-api-python-client google-auth-oauthlib")
        creds = self._credentials_file()
        if creds is None:
            return False, "Fichier credentials.json OAuth non configuré (Paramètres › E-mail)."
        if not creds.is_file():
            return False, f"Fichier OAuth introuvable : {creds}"
        return True, "Gmail prêt (une autorisation Google s'ouvrira au premier envoi)."

    def _get_credentials(self):
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow

        creds = None
        if GMAIL_TOKEN_FILE.is_file():
            creds = Credentials.from_authorized_user_file(str(GMAIL_TOKEN_FILE), GMAIL_SCOPES)
        if creds and creds.valid:
            return creds
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self._credentials_file()), GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)  # ouvre le navigateur : consentement humain
        GMAIL_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        GMAIL_TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        return creds

    def send(self, msg: EmailData) -> str:
        ready, why = self.readiness()
        if not ready:
            raise EmailNotConfigured(why)
        from googleapiclient.discovery import build

        try:
            creds = self._get_credentials()
            service = build("gmail", "v1", credentials=creds, cache_discovery=False)
            raw = base64.urlsafe_b64encode(build_mime(msg).as_bytes()).decode("ascii")
            sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
        except EmailError:
            raise
        except Exception as exc:
            log.exception("Échec de l'envoi Gmail")
            raise EmailError(f"Échec de l'envoi Gmail : {exc}") from exc
        message_id = str(sent.get("id", ""))
        if not message_id:
            raise EmailError("Gmail n'a retourné aucun identifiant : envoi non confirmé.")
        log.info("E-mail envoyé via Gmail (id=%s)", message_id)
        return message_id


class EmailService:
    def __init__(self, settings: SettingsService):
        self.settings = settings
        self.provider: EmailProvider = GmailApiProvider(settings)

    def readiness(self) -> tuple[bool, str]:
        return self.provider.readiness()

    def send(self, msg: EmailData) -> str:
        errors, _ = validate(msg)
        if errors:
            raise EmailError("Message invalide : " + " ".join(errors))
        return self.provider.send(msg)
