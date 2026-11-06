"""Paramètres de l'interface graphique (data/settings.json) et gestion de la clé API.

La clé Gemini reste dans `.env` (comme le backend l'attend) : jamais dans le code,
jamais dans settings.json, jamais dans les logs.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

from app.core.config import BASE_DIR, DATA_DIR

log = logging.getLogger("prosper.settings")

SETTINGS_FILE = DATA_DIR / "settings.json"
ENV_FILE = BASE_DIR / ".env"
API_KEY_VAR = "GEMINI_API_KEY"

DEFAULTS: dict = {
    "display_name": "",
    "theme": "dark",           # dark | light
    "accent": "cyan",          # cyan | blue
    "documents_dir": "",       # vide = dossier Candidatures du backend
    "cv_path": "",
    "school_letter_path": "",
    "email_provider": "gmail",
    "email_account": "",
    "gmail_credentials_path": "",
}


class SettingsService:
    def __init__(self, path: Path = SETTINGS_FILE):
        self.path = path
        self._data = dict(DEFAULTS)
        self.load()

    # ------------------------------------------------------------------ #
    def load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                self._data.update({k: v for k, v in raw.items() if k in DEFAULTS})
        except FileNotFoundError:
            pass
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("settings.json illisible, valeurs par défaut utilisées : %s", exc)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def get(self, key: str):
        return self._data.get(key, DEFAULTS.get(key))

    def set(self, key: str, value) -> None:
        if key not in DEFAULTS:
            raise KeyError(key)
        self._data[key] = value

    def update(self, values: dict) -> None:
        for key, value in values.items():
            self.set(key, value)
        self.save()

    # ------------------------------------------------------------------ #
    # Clé API (.env)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _read_env_key() -> str:
        try:
            for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith(f"{API_KEY_VAR}="):
                    return line.split("=", 1)[1].strip().strip("'\"")
        except OSError:
            pass
        return ""

    def api_key_value(self) -> str:
        """Valeur brute — à n'utiliser que pour tester la connexion, jamais pour l'afficher."""
        return os.environ.get(API_KEY_VAR) or self._read_env_key()

    def api_key_status(self) -> tuple[bool, str]:
        """(configurée ?, aperçu masqué du type '••••ab12')."""
        key = self.api_key_value()
        if not key:
            return False, ""
        return True, "•" * 8 + key[-4:]

    def set_api_key(self, key: str) -> None:
        key = key.strip()
        if not key:
            raise ValueError("La clé API est vide.")
        if any(c.isspace() for c in key):
            raise ValueError("La clé API ne doit pas contenir d'espace.")
        from dotenv import set_key  # python-dotenv est déjà une dépendance du backend

        ENV_FILE.touch(exist_ok=True)
        set_key(str(ENV_FILE), API_KEY_VAR, key, quote_mode="never")
        os.environ[API_KEY_VAR] = key
        # Si le client Gemini est déjà chargé, on le recrée avec la nouvelle clé.
        gemini = sys.modules.get("app.ai.gemini")
        if gemini is not None:
            import importlib

            importlib.reload(gemini)
        log.info("Clé API Gemini mise à jour (valeur non journalisée).")
