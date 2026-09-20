from app.core.config import APP_NAME, VERSION
from app.core.router import CommandRouter
from app.memory.memory import add_history
from app.ai.intent import understand


def show_help():

    print("""
Commandes disponibles :

    Tu peux utiliser des commandes classiques :

    system
        Afficher les informations détaillées du système.

    time
        Afficher la date et l'heure.

    pwd
        Afficher le dossier courant.

    open <application>
        Ouvrir une application.

    close <application>
        Fermer une application.

    create <folder>
        Créer un dossier.

    delete <folder>
        Supprimer un dossier.

    list <folder>
        Afficher le contenu d'un dossier.

    find <file>
        Rechercher un fichier.

    remember <clé> <valeur>
        Mémoriser une information.

    memory
        Afficher la mémoire de Prosper.

    forget <clé>
        Supprimer une information de la mémoire.

    history
        Afficher les dernières commandes.

    help
        Afficher cette aide.

    exit
        Fermer P.R.O.S.P.E.R.


    Ou parler naturellement :

    "Quelle heure est-il ?"
    "Ouvre mon éditeur de code"
    "Montre-moi les informations de mon PC"
""")


def display_result(result):

    result_type = result["type"]

    if result_type == "system":

        data = result["data"]

        print("\n===== SYSTEM =====")

        print(f"OS              : {data['os']}")
        print(f"Version         : {data['os_version']}")
        print(f"Machine         : {data['machine']}")
        print(f"Processeur      : {data['processor']}")
        print(f"CPU cores       : {data['cpu_count']}")
        print(f"RAM totale      : {data['ram_total']} GB")
        print(f"RAM disponible  : {data['ram_available']} GB")
        print(f"Disque total    : {data['disk_total']} GB")
        print(f"Disque libre    : {data['disk_free']} GB")

    elif result_type == "time":

        data = result["data"]

        print(f"\nDate  : {data['date']}")
        print(f"Heure : {data['time']}")

    elif result_type == "pwd":

        print(f"\nDossier actuel : {result['data']}")

    elif result_type == "list":

        data = result["data"]

        print("\nContenu :")

        if isinstance(data, list):

            for item in data:
                print(f"  - {item}")

        else:
            print(data)

    elif result_type == "find":

        data = result["data"]

        if not data:

            print("\nP.R.O.S.P.E.R. > Aucun fichier trouvé.")

        else:

            print(f"\n{len(data)} fichier(s) trouvé(s) :")

            for path in data:
                print(f"  - {path}")

    elif result_type == "memory":

        data = result["data"]

        print("\n===== MEMORY =====")

        if not data:

            print("La mémoire est vide.")

        else:

            for key, value in data.items():

                print(f"{key} : {value}")

    elif result_type == "history":

        data = result["data"]

        print("\n===== HISTORY =====")

        if not data:

            print("Aucune commande enregistrée.")

        else:

            for entry in data:

                print(
                    f"{entry['timestamp']} "
                    f"-> {entry['command']}"
                )

    else:

        print(
            f"\nP.R.O.S.P.E.R. > "
            f"{result['data']}"
        )


def start_cli():

    router = CommandRouter()

    print("=" * 55)
    print(f"             {APP_NAME}")
    print(f"       Personal AI Assistant - V{VERSION}")
    print("=" * 55)

    print("\nTape 'help' pour voir les commandes disponibles.")
    print("Tu peux aussi parler naturellement à P.R.O.S.P.E.R.")

    while True:

        command = input("\nYou > ").strip()

        if not command:
            continue

        if command.lower() in ["exit", "quit", "bye"]:

            print(
                "P.R.O.S.P.E.R. > "
                "À bientôt."
            )

            break

        if command.lower() == "help":

            show_help()
            continue

        add_history(command)

        print("\nP.R.O.S.P.E.R. > Analyse...")

        intent = understand(command)

        if not intent["success"]:

            print(
                "P.R.O.S.P.E.R. > "
                f"{intent['error']}"
            )

            continue

        action = intent["action"]
        argument = intent["argument"]

        if action == "unknown":

            print(
                "P.R.O.S.P.E.R. > "
                "Je ne sais pas encore comment faire ça."
            )

            continue

        if action == "delete":

            confirmation = input(
                f"P.R.O.S.P.E.R. > "
                f"Confirmer la suppression de "
                f"'{argument}' ? [y/n] : "
            ).strip().lower()

            if confirmation not in [
                "y",
                "yes",
                "o",
                "oui"
            ]:

                print(
                    "P.R.O.S.P.E.R. > "
                    "Suppression annulée."
                )

                continue

        result = router.execute(
            action,
            argument
        )

        if not result["success"]:

            print(
                f"\nP.R.O.S.P.E.R. > "
                f"{result['message']}"
            )

            continue

        display_result(result)