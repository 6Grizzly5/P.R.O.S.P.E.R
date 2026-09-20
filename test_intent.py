from app.ai.intent import understand


commands = [
    "Ouvre VS Code",
    "Quelle heure est-il ?",
    "Crée un dossier appelé test",
    "Je veux connaître les informations de mon ordinateur",
    "Lance mon éditeur de code"
]


for command in commands:

    print("\nUtilisateur :", command)

    result = understand(command)

    print("Intention :", result)