# P.R.O.S.P.E.R — Interface graphique (V0.3)

Interface de bureau PyQt6 ajoutée **autour** du backend existant. Aucun fichier d'origine
n'a été modifié : le CLI fonctionne exactement comme avant.

## Installation (Windows 10)

1. Extraire ce zip **par-dessus** votre dossier `P.R.O.S.P.E.R` actuel (les fichiers d'origine sont
   identiques ; votre `.env`, `venv/`, `.git/`, `data/` et `Candidatures/` ne sont pas touchés).
   Sinon, extraire dans un nouveau dossier et y copier votre `.env`.
2. Double-cliquer sur **`install_gui.bat`** (installe PyQt6 et google-genai dans le `venv`).
3. Double-cliquer sur **`Prosper_GUI.bat`** → l'application s'ouvre, sans fenêtre de terminal.

Raccourci Bureau : **`create_shortcut.bat`** (crée « P.R.O.S.P.E.R » avec l'icône).
Mode terminal : **`Prosper_CLI.bat`** (ou `python run_cli.py` / `python -m app.main`, comme avant).

Commandes manuelles équivalentes :
```bat
venv\Scripts\python.exe -m pip install -r requirements-gui.txt
venv\Scripts\pythonw.exe run_gui.pyw
```
Si PyQt6 refuse de s'installer (Python trop récent), créez le venv avec Python 3.12 ou 3.13.

## Clé API Gemini
Dans **Paramètres › Intelligence artificielle** : collez la clé, « Enregistrer la clé », puis
« Tester la connexion ». Elle est écrite dans `.env` (comme avant), affichée masquée
(`••••1234`) et jamais écrite dans les logs ni dans `settings.json`.

## Fonctionnalités
| Page | Contenu |
|---|---|
| Tableau de bord | Accueil, date/heure, état de l'IA, compteurs réels (candidatures, documents, brouillons), activité récente (`history.json`, partagé avec le CLI), répartition par statut |
| Assistant IA | Conversation avec **le même flux que le CLI** (lettre → intention → action/conversation → reformulation). Thread séparé + indicateur de chargement, confirmation avant `delete`, effacement de la conversation |
| Candidatures | Ajout / modification / suppression, secteur, e-mail RH, objectif, date, 8 statuts, recherche, filtre, vue d'ensemble |
| E-mails | Composition riche (gras, italique, souligné, liste), Cc/Cci, pièces jointes (CV, lettre de l'école, PDF générés, autres), aperçu, brouillons SQLite, envoi avec confirmation |
| Documents | Liste des PDF, ouverture (lecteur par défaut), suppression avec confirmation, regroupement par entreprise, génération via le générateur existant |
| Paramètres | Clé API, dossiers/fichiers par défaut, compte e-mail, thème (sombre/clair) et accent, version |

## Sécurité des e-mails
Flux **Préparer → Vérifier → Valider → Envoyer** : « Vérifier et envoyer… » ouvre une fenêtre
récapitulative (destinataires, objet, message tel que reçu, pièces jointes, erreurs/avertissements).
Le bouton d'envoi reste grisé tant que la case « J'ai vérifié… » n'est pas cochée.
Un message n'est marqué « envoyé » **que si Gmail confirme l'envoi** ; sinon une erreur s'affiche,
jamais de faux succès.

### Activer l'envoi Gmail (non configuré par défaut)
1. Google Cloud Console → créer un projet → activer **Gmail API** → écran de consentement
   (type Externe, ajoutez votre adresse en utilisateur test) → Identifiants →
   **ID client OAuth › Application de bureau** → télécharger `credentials.json`.
2. `venv\Scripts\python.exe -m pip install google-api-python-client google-auth-oauthlib`
3. Paramètres › Compte e-mail › indiquer le fichier `credentials.json`.
4. Au premier envoi, le navigateur s'ouvre pour autoriser (portée `gmail.send` uniquement).
   Le jeton est gardé dans `data/gmail_token.json`. Aucun mot de passe n'est stocké.

> Cette partie suit la documentation officielle mais **n'a pas pu être testée sur un vrai compte
> Gmail** : testez d'abord en vous envoyant un message à vous-même.

## Architecture
```
app/
├── main.py, interface/cli.py, ai/, commands/, core/, memory/   ← backend d'origine (inchangé)
├── services/            ← adaptateurs GUI ↔ backend (aucun import Qt)
│   ├── assistant_service.py   flux du CLI réutilisé (intent, response, CommandRouter, history)
│   ├── letters_service.py     appelle _choose_template / _make_pdf de commands/letters.py
│   ├── documents_service.py, career_db.py (SQLite), email_service.py, settings_service.py
│   └── logging_setup.py       logs data/logs/prosper_gui.log, secrets masqués
└── gui/                 ← PyQt6 : main.py, main_window.py, theme.py (QSS), components.py,
    ├── dialogs.py, workers.py (QRunnable/QThreadPool), context.py
    └── views/ dashboard, assistant_view, career_view, email_view, documents_view, settings_view
run_gui.pyw · run_cli.py · Prosper_GUI.bat · Prosper_CLI.bat · install_gui.bat · create_shortcut.bat
data/prosper.db (créé au 1er lancement), data/settings.json   ← nouvelles données (ignorées par git)
```
Les vues sont créées à la demande (démarrage rapide, faible mémoire) et l'horloge ne tourne que
quand le tableau de bord est visible.

## Choix à connaître
- Les lettres : le générateur écrit toujours dans `Candidatures/`. Si vous choisissez un autre
  dossier dans les Paramètres, le PDF y est **déplacé** après génération.
- L'assistant interactif de lettres du CLI (questions `input()`) est remplacé dans la GUI par un
  formulaire ; le modèle de lettre reste choisi par le générateur existant.
- La conversation affichée n'est pas sauvegardée entre deux sessions (les commandes le sont déjà
  dans `history.json`).
- Le modèle Gemini reste celui défini dans `app/ai/gemini.py` (non modifié).

## Tests
```bat
venv\Scripts\python.exe -m unittest discover -s tests -v
venv\Scripts\python.exe tests\smoke_gui.py
```
