from app.core.router import CommandRouter


def show_help():
    print("""
Commandes disponibles :

    system
        Afficher les informations du système.

    time
        Afficher la date et l'heure.

    pwd
        Afficher le dossier courant.

    open <application>
        Ouvrir une application.

    create <folder>
        Créer un dossier.

    delete <folder>
        Supprimer un dossier.

    list <folder>
        Afficher le contenu d'un dossier.

    help
        Afficher cette aide.
    
    close <application>
        Fermer une application.

    find <file>
        Rechercher un fichier.

    exit
        Fermer P.R.O.S.P.E.R.
""")


def display_result(result):
    if result["type"] == "system":

        data = result["data"]

        print(f"\nSystème : {data['system']}")
        print(f"OS      : {data['platform']}")

    elif result["type"] == "time":

        data = result["data"]

        print(f"\nDate  : {data['date']}")
        print(f"Heure : {data['time']}")

    elif result["type"] == "pwd":

        print(f"\nDossier actuel : {result['data']}")

    elif result["type"] == "list":

        data = result["data"]

        print("\nContenu :")

        if isinstance(data, list):

            for item in data:
                print(f"  - {item}")

        else:
            print(data)
    elif result["type"] == "find":

        data = result["data"]

        if not data:
            print("\nP.R.O.S.P.E.R. > Aucun fichier trouvé.")
            return

        print(f"\n{len(data)} fichier(s) trouvé(s) :")

        for path in data:
            print(f"  - {path}")

    else:

        print(f"\nP.R.O.S.P.E.R. > {result['data']}")


def start_cli():

    router = CommandRouter()

    print("=" * 50)
    print("             P.R.O.S.P.E.R.")
    print("     Personal AI Assistant - V0.1")
    print("=" * 50)

    print("\nTape 'help' pour voir les commandes disponibles.")

    while True:

        command = input("\nYou > ").strip()

        if not command:
            continue

        parts = command.split(maxsplit=1)

        action = parts[0].lower()

        argument = ""

        if len(parts) > 1:
            argument = parts[1].strip()

        if action in ["exit", "quit", "bye"]:

            print("P.R.O.S.P.E.R. > À bientôt.")
            break

        if action == "help":

            show_help()
            continue
        
        if action == "delete":

            confirmation = input(
                f"P.R.O.S.P.E.R. > "
                f"Confirmer la suppression de '{argument}' ? [y/n] : "
            ).strip().lower()

            if confirmation not in ["y", "yes", "o", "oui"]:
                print("P.R.O.S.P.E.R. > Suppression annulée.")
                continue

        result = router.execute(action, argument)

        if not result["success"]:

            print(f"\nP.R.O.S.P.E.R. > {result['message']}")
            continue

        display_result(result)