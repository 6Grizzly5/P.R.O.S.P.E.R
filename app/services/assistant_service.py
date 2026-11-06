"""Pont entre l'interface et l'assistant existant.

Reproduit fidèlement le flux de app/interface/cli.py (lettre → intention Gemini →
conversation ou action du CommandRouter → reformulation) en réutilisant les mêmes modules :
app.ai.intent, app.ai.response, app.core.router, app.memory.memory.
Aucune nouvelle implémentation de Gemini. Les imports IA sont paresseux : l'interface
s'ouvre même si la clé API est absente (elle se configure dans les Paramètres).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from app.core.router import CommandRouter
from app.memory.memory import add_history, get_history
from app.services.letters_service import LettersService
from app.services.logging_setup import mask_secrets

log = logging.getLogger("prosper.assistant")


@dataclass
class Plan:
    kind: str                  # "letter" | "conversation" | "action" | "error"
    message: str = ""
    action: str = ""
    argument: object = None
    company: str = ""          # pour kind == "letter"
    error: str = ""

    @property
    def needs_confirmation(self) -> bool:
        return self.kind == "action" and self.action == "delete"


class AssistantService:
    def __init__(self, letters: LettersService):
        self.letters = letters
        self.router = CommandRouter()

    # ------------------------------------------------------------------ #
    @staticmethod
    def _friendly(exc: Exception) -> str:
        text = mask_secrets(str(exc))
        if isinstance(exc, RuntimeError) and "GEMINI" in text.upper():
            return ("La clé API Gemini est manquante ou invalide. "
                    "Ajoutez-la dans Paramètres › Intelligence artificielle.")
        return text or exc.__class__.__name__

    def ai_ready(self) -> bool:
        try:
            import app.ai.gemini  # noqa: F401
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    # Étape 1 — comprendre (réseau : à exécuter dans un thread)
    # ------------------------------------------------------------------ #
    def plan(self, message: str) -> Plan:
        message = message.strip()
        add_history(message)  # même historique que le CLI
        if self.letters.is_letter_request(message):
            return Plan("letter", message=message, company=self.letters.extract_company(message))
        try:
            from app.ai.intent import understand
            intent = understand(message)
        except Exception as exc:
            log.exception("Échec de l'analyse d'intention")
            return Plan("error", message=message, error=self._friendly(exc))
        if not intent.get("success"):
            return Plan("error", message=message,
                        error=str(intent.get("error") or "Je n'ai pas compris la demande."))
        if intent.get("type") == "conversation":
            return Plan("conversation", message=message)
        return Plan("action", message=message, action=intent.get("action", ""),
                    argument=intent.get("argument", ""))

    # ------------------------------------------------------------------ #
    # Étape 2 — répondre / exécuter (thread)
    # ------------------------------------------------------------------ #
    def finish(self, plan: Plan) -> str:
        try:
            if plan.kind == "conversation":
                from app.ai.response import generate_conversation
                return generate_conversation(plan.message)
            if plan.kind == "action":
                result = self.router.execute(plan.action, plan.argument)
                if not result.get("success"):  # même comportement que le CLI
                    return str(result.get("message") or "L'action a échoué.")
                try:
                    from app.ai.response import generate_response
                    return generate_response(plan.message, result)
                except Exception as exc:  # l'action a eu lieu : on affiche quand même le résultat
                    log.warning("Reformulation impossible : %s", mask_secrets(str(exc)))
                    return self.format_result(result)
            return plan.error
        except Exception as exc:
            log.exception("Échec de la réponse de l'assistant")
            return f"⚠️ {self._friendly(exc)}"

    @staticmethod
    def format_result(result) -> str:
        """Affichage local de secours (sans IA) d'un résultat du CommandRouter."""
        data = result
        if isinstance(result, dict):
            data = result.get("data", {k: v for k, v in result.items() if k != "success"})
        if isinstance(data, str):
            return data
        try:
            return "```\n" + json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n```"
        except Exception:
            return str(data)

    @staticmethod
    def recent_history(limit: int = 8) -> list[dict]:
        try:
            return list(get_history(limit))
        except Exception:
            return []
