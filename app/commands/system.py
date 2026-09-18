import os
from datetime import datetime


def get_system_info():
    return {
        "system": os.name,
        "platform": os.environ.get("OS", "Unknown")
    }


def get_current_time():
    now = datetime.now()

    return {
        "date": now.strftime("%d/%m/%Y"),
        "time": now.strftime("%H:%M:%S")
    }


def get_current_directory():
    return os.getcwd()