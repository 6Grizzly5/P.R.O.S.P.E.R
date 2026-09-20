import json

from app.ai.gemini import ask_gemini


AVAILABLE_ACTIONS = [
    "system",
    "time",
    "pwd",
    "open",
    "close",
    "create",
    "delete",
    "list",
    "find",
    "remember",
    "forget",
    "memory",
    "history"
]


SYSTEM_PROMPT = """
Tu es le moteur de compréhension de P.R.O.S.P.E.R.,
un assistant personnel pour ordinateur Windows.

Ton rôle est uniquement de transformer la demande de
l'utilisateur en une intention structurée.

Tu ne dois jamais exécuter une action.

Actions disponibles :

system
time
pwd
open
close
create
delete
list
find
remember
forget
memory
history

Tu dois répondre UNIQUEMENT avec un objet JSON valide.

Format obligatoire :

{
    "action": "nom_de_l_action",
    "argument": "argument_de_l_action"
}

Si aucune action ne correspond à la demande :

{
    "action": "unknown",
    "argument": ""
}

Exemples :

Utilisateur :
"Quelle heure est-il ?"

Réponse :
{
    "action": "time",
    "argument": ""
}

Utilisateur :
"Ouvre VS Code"

Réponse :
{
    "action": "open",
    "argument": "vscode"
}

Utilisateur :
"Lance mon éditeur de code"

Réponse :
{
    "action": "open",
    "argument": "vscode"
}

Utilisateur :
"Crée un dossier appelé test"

Réponse :
{
    "action": "create",
    "argument": "test"
}

Utilisateur :
"Supprime le dossier test"

Réponse :
{
    "action": "delete",
    "argument": "test"
}

Utilisateur :
"Souviens-toi que mon éditeur préféré est VS Code"

Réponse :
{
    "action": "remember",
    "argument": "favorite_editor VS Code"
}

Ne donne aucune explication.
Ne donne aucun texte avant ou après le JSON.
"""


def understand(command):

    prompt = f"""
{SYSTEM_PROMPT}

Demande de l'utilisateur :

"{command}"
"""

    response = ask_gemini(prompt)

    try:
        intent = json.loads(response)

    except json.JSONDecodeError:

        return {
            "success": False,
            "action": "unknown",
            "argument": "",
            "error": "Le LLM n'a pas retourné un JSON valide."
        }

    action = intent.get("action", "unknown")
    argument = intent.get("argument", "")

    if action != "unknown" and action not in AVAILABLE_ACTIONS:

        return {
            "success": False,
            "action": "unknown",
            "argument": "",
            "error": f"Action non autorisée : {action}"
        }

    return {
        "success": True,
        "action": action,
        "argument": argument
    }