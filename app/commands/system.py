import os
import platform
import shutil

import psutil


def get_system_info():
    memory = psutil.virtual_memory()
    disk = shutil.disk_usage(os.path.abspath(os.sep))

    return {
        "os": platform.system(),
        "os_version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "ram_total": round(memory.total / (1024 ** 3), 2),
        "ram_available": round(memory.available / (1024 ** 3), 2),
        "disk_total": round(disk.total / (1024 ** 3), 2),
        "disk_free": round(disk.free / (1024 ** 3), 2),
    }


def get_current_time():
    from datetime import datetime

    now = datetime.now()

    return {
        "date": now.strftime("%d/%m/%Y"),
        "time": now.strftime("%H:%M:%S")
    }


def get_current_directory():
    return os.getcwd()