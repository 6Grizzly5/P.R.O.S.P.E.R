import subprocess


APPLICATIONS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "paint": "mspaint.exe",
}


def open_application(application_name):
    if not application_name:
        return "Nom de l'application manquant."

    application_name = application_name.lower()

    if application_name not in APPLICATIONS:
        return (
            f"Application '{application_name}' inconnue.\n"
            f"Applications disponibles : "
            f"{', '.join(APPLICATIONS.keys())}"
        )

    try:
        subprocess.Popen(APPLICATIONS[application_name])

        return f"Ouverture de {application_name}..."

    except Exception as error:
        return f"Erreur lors de l'ouverture : {error}"


def close_application(application_name):
    if not application_name:
        return "Nom de l'application manquant."

    application_name = application_name.lower()

    if application_name not in APPLICATIONS:
        return (
            f"Application '{application_name}' inconnue.\n"
            f"Applications disponibles : "
            f"{', '.join(APPLICATIONS.keys())}"
        )

    process_name = APPLICATIONS[application_name]

    try:
        result = subprocess.run(
            ["taskkill", "/IM", process_name, "/F"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            return f"{application_name} fermé."

        return f"{application_name} n'est pas actuellement ouvert."

    except Exception as error:
        return f"Erreur lors de la fermeture : {error}"