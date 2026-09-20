import json
from datetime import datetime

from app.core.config import MEMORY_FILE, HISTORY_FILE


def load_memory():
    if not MEMORY_FILE.exists():
        return {}

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    except (json.JSONDecodeError, OSError):
        return {}


def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(
            memory,
            file,
            indent=4,
            ensure_ascii=False
        )


def remember(key, value):
    memory = load_memory()

    memory[key] = value

    save_memory(memory)

    return f"J'ai mémorisé '{key}'."


def forget(key):
    memory = load_memory()

    if key not in memory:
        return f"Je ne connais pas '{key}'."

    del memory[key]

    save_memory(memory)

    return f"J'ai oublié '{key}'."


def get_memory():
    return load_memory()


def add_history(command):
    history = load_history()

    entry = {
        "command": command,
        "timestamp": datetime.now().strftime(
            "%d/%m/%Y %H:%M:%S"
        )
    }

    history.append(entry)

    save_history(history)


def load_history():
    if not HISTORY_FILE.exists():
        return []

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    except (json.JSONDecodeError, OSError):
        return []


def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as file:
        json.dump(
            history,
            file,
            indent=4,
            ensure_ascii=False
        )


def get_history(limit=10):
    history = load_history()

    return history[-limit:]