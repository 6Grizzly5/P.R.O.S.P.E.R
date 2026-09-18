import os


def create_folder(folder_name):
    if not folder_name:
        return "Nom du dossier manquant."

    if os.path.exists(folder_name):
        return f"Le dossier '{folder_name}' existe déjà."

    os.makedirs(folder_name)

    return f"Dossier '{folder_name}' créé."


def delete_folder(folder_name):
    if not folder_name:
        return "Nom du dossier manquant."

    if not os.path.exists(folder_name):
        return f"Le dossier '{folder_name}' n'existe pas."

    if not os.path.isdir(folder_name):
        return f"'{folder_name}' n'est pas un dossier."

    try:
        os.rmdir(folder_name)

        return f"Dossier '{folder_name}' supprimé."

    except OSError:
        return (
            f"Impossible de supprimer '{folder_name}'. "
            "Le dossier est peut-être non vide."
        )


def list_folder(folder_path="."):
    if not os.path.exists(folder_path):
        return f"Le dossier '{folder_path}' n'existe pas."

    if not os.path.isdir(folder_path):
        return f"'{folder_path}' n'est pas un dossier."

    items = os.listdir(folder_path)

    if not items:
        return "Le dossier est vide."

    return items


def find_file(file_name, start_path="."):
    if not file_name:
        return []

    results = []

    for root, directories, files in os.walk(start_path):

        # Évite les environnements virtuels et dossiers Git
        directories[:] = [
            directory
            for directory in directories
            if directory not in ["venv", ".git", "__pycache__"]
        ]

        for file in files:

            if file.lower() == file_name.lower():

                full_path = os.path.abspath(
                    os.path.join(root, file)
                )

                results.append(full_path)

    return results