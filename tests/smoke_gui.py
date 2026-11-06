"""Test de fumée de l'interface (hors-écran). Usage : QT_QPA_PLATFORM=offscreen python tests/smoke_gui.py [dossier_captures]"""
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt6.QtCore import QCoreApplication  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from app.gui.context import AppContext  # noqa: E402
from app.gui.main_window import MainWindow  # noqa: E402
from app.services.assistant_service import Plan  # noqa: E402

shots = Path(sys.argv[1]) if len(sys.argv) > 1 else None
if shots:
    shots.mkdir(parents=True, exist_ok=True)


def pump(ms=150):
    end = time.time() + ms / 1000
    while time.time() < end:
        QCoreApplication.processEvents()
        time.sleep(0.01)


def snap(win, name):
    pump(120)
    if shots:
        win.grab().save(str(shots / f"{name}.png"))


app = QApplication([])
ctx = AppContext.create(db_path=":memory:")
db = ctx.db
a = db.add_company(name="Airtel Madagascar", sector="Télécom", hr_email="rh@airtel.mg",
                   target="Stage 6 mois – développement", status="preparing")
db.add_company(name="Orange Madagascar", sector="Télécom", hr_email="rh@orange.mg", status="sent",
               applied_date="2026-10-26")
db.add_company(name="Accès Banque", sector="Finance", status="waiting", applied_date="2026-10-26")
db.save_draft({"company_id": a, "to_addr": "rh@airtel.mg", "subject": "Demande de stage – Airtel Madagascar",
               "body_html": "<p>Bonjour,</p><p>Je souhaite effectuer un <b>stage</b>.</p>"})

win = MainWindow(ctx, app)
win.show()
pump()
failures = []


def check(cond, label):
    print(("OK   " if cond else "FAIL ") + label)
    if not cond:
        failures.append(label)


# Toutes les pages s'ouvrent
for key in ("dashboard", "assistant", "career", "email", "documents", "settings"):
    win.show_page(key)
    pump(80)
    check(win.stack.currentWidget() is win.view(key), f"page « {key} » affichée")
    snap(win, f"{key}")

# Assistant : l'UI reste réactive pendant un traitement lent (thread)
asst = win.view("assistant")
win.show_page("assistant")


def slow_plan(msg):
    time.sleep(0.6)
    return Plan("conversation", message=msg)


ctx.assistant.plan = slow_plan
ctx.assistant.finish = lambda plan: "Bonjour ! Voici une **réponse** de test."
asst.input.setPlainText("Salut")
asst.send()
t0, ticks = time.time(), 0
while time.time() - t0 < 0.5:
    QCoreApplication.processEvents()   # la boucle d'événements tourne → pas de gel
    ticks += 1
    time.sleep(0.005)
check(asst._busy and ticks > 20, "UI non figée pendant le traitement")
snap(win, "assistant_loading")
pump(1200)
check(not asst._busy, "réponse reçue, indicateur retiré")
snap(win, "assistant_reply")
asst.clear_conversation()
check(asst.thread_lay.count() == 2, "conversation effacée")

# Candidatures : recherche + filtre
career = win.view("career")
win.show_page("career")
career.search.setText("orange")
pump(50)
check(career.table.rowCount() == 1, "recherche entreprise")
career.search.setText("")
career.status_filter.setCurrentIndex(career.status_filter.findData("waiting"))
pump(50)
check(career.table.rowCount() == 1, "filtre par statut")
career.status_filter.setCurrentIndex(0)

# Candidatures → e-mail prérempli
win.compose_email(a)
email = win.view("email")
check(email.to.text() == "rh@airtel.mg" and "Airtel" in email.subject.text(), "e-mail prérempli depuis l'entreprise")

# Brouillon : enregistrer / recharger
email.editor.setHtml("<p>Bonjour <b>test</b></p>")
did = email.save_draft()
email.new_draft(force=True)
email.load_draft(did)
check("test" in email.editor.toPlainText(), "brouillon enregistré puis rechargé")

# Envoi : sans fournisseur prêt, JAMAIS de faux succès et rien n'est marqué envoyé
ready, note = ctx.email.readiness()
check(not ready, f"Gmail non prêt détecté ({note[:50]}…)")
msg = email.collect()
check(ctx.db.count_sent() == 0, "aucun e-mail marqué envoyé")

# Pièces jointes
cv = Path("/tmp/cv_test.pdf")
cv.write_bytes(b"%PDF-1.4 test")
email._add_attachment(str(cv))
check(email.attachments.count() == 1, "pièce jointe ajoutée")
email.attachments.setCurrentRow(0)
email._remove_attachment()
check(email.attachments.count() == 0, "pièce jointe retirée")
email._add_attachment(str(cv))
snap(win, "email_filled")

# Thème clair + accent bleu
ctx.settings.set("theme", "light")
ctx.settings.set("accent", "blue")
win._apply_theme()
win.show_page("dashboard")
snap(win, "dashboard_light")
ctx.settings.set("theme", "dark")
ctx.settings.set("accent", "cyan")
win._apply_theme()

print("\nRÉSULTAT :", "ÉCHEC " + str(failures) if failures else "tout est OK")
sys.exit(1 if failures else 0)
