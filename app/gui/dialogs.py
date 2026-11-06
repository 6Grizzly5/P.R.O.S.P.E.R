"""Boîtes de dialogue : entreprise, génération de lettre, aperçu/confirmation d'e-mail."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from PyQt6.QtCore import QDate, Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDateEdit, QDialog, QDialogButtonBox,
                             QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                             QPlainTextEdit, QTextBrowser, QVBoxLayout, QWidget, QMessageBox)

from app.gui.components import make_button
from app.services.career_db import STATUSES, is_valid_email
from app.services.email_service import EmailData


def open_path(path: str | Path) -> bool:
    """Ouvre un fichier/dossier avec l'application par défaut du système."""
    return QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


# ---------------------------------------------------------------------- #
class CompanyDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, company: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Modifier l'entreprise" if company else "Ajouter une entreprise")
        self.setMinimumWidth(480)
        company = company or {}

        self.name = QLineEdit(company.get("name", ""))
        self.sector = QLineEdit(company.get("sector", ""))
        self.hr_email = QLineEdit(company.get("hr_email", ""))
        self.hr_email.setPlaceholderText("rh@entreprise.com")
        self.target = QLineEdit(company.get("target", ""))
        self.target.setPlaceholderText("Ex. Stage de 6 mois en développement logiciel")
        self.status = QComboBox()
        for code, label in STATUSES.items():
            self.status.addItem(label, code)
        self.status.setCurrentIndex(max(0, self.status.findData(company.get("status", "to_contact"))))

        self.has_date = QCheckBox("Date de candidature")
        self.date = QDateEdit(calendarPopup=True)
        self.date.setDisplayFormat("dd/MM/yyyy")
        applied = company.get("applied_date", "")
        qd = QDate.fromString(applied, "yyyy-MM-dd") if applied else QDate()
        self.has_date.setChecked(qd.isValid())
        self.date.setDate(qd if qd.isValid() else QDate.currentDate())
        self.date.setEnabled(self.has_date.isChecked())
        self.has_date.toggled.connect(self.date.setEnabled)

        self.notes = QPlainTextEdit(company.get("notes", ""))
        self.notes.setFixedHeight(80)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.addRow("Entreprise *", self.name)
        form.addRow("Secteur", self.sector)
        form.addRow("E-mail RH", self.hr_email)
        form.addRow("Objectif", self.target)
        form.addRow("Statut", self.status)
        form.addRow(self.has_date, self.date)
        form.addRow("Notes", self.notes)

        self.error = QLabel("")
        self.error.setObjectName("Danger")
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName("Primary")
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Enregistrer")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 16)
        lay.addLayout(form)
        lay.addWidget(self.error)
        lay.addWidget(buttons)

    def _validate(self) -> None:
        if not self.name.text().strip():
            self.error.setText("Le nom de l'entreprise est obligatoire.")
            return
        mail = self.hr_email.text().strip()
        if mail and not is_valid_email(mail):
            self.error.setText("L'adresse e-mail RH n'est pas valide.")
            return
        self.accept()

    def values(self) -> dict:
        return {
            "name": self.name.text(), "sector": self.sector.text(),
            "hr_email": self.hr_email.text(), "target": self.target.text(),
            "status": self.status.currentData(),
            "applied_date": self.date.date().toString("yyyy-MM-dd") if self.has_date.isChecked() else "",
            "notes": self.notes.toPlainText(),
        }


# ---------------------------------------------------------------------- #
class LetterDialog(QDialog):
    """Remplace les questions input() de l'assistant CLI de lettres."""

    def __init__(self, parent: QWidget | None = None, company: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Générer une lettre de demande de stage")
        self.setMinimumWidth(480)
        self.company = QLineEdit(company)
        self.address = QLineEdit()
        self.address.setPlaceholderText("Optionnel — adresse de l'entreprise")
        self.recipient = QLineEdit()
        self.recipient.setPlaceholderText("Optionnel — ex. Madame, Monsieur / Direction des RH")
        self.service = QLineEdit()
        self.service.setPlaceholderText("Optionnel — ex. Service informatique")

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.addRow("Entreprise *", self.company)
        form.addRow("Adresse", self.address)
        form.addRow("Destinataire", self.recipient)
        form.addRow("Service", self.service)

        note = QLabel("Le modèle de lettre est choisi automatiquement par le générateur existant "
                      "(rotation entre les 5 modèles).")
        note.setObjectName("Muted")
        note.setWordWrap(True)
        self.error = QLabel("")
        self.error.setObjectName("Danger")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        ok = buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok.setText("Générer le PDF")
        ok.setObjectName("Primary")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 16)
        lay.addLayout(form)
        lay.addWidget(note)
        lay.addWidget(self.error)
        lay.addWidget(buttons)

    def _validate(self) -> None:
        if not self.company.text().strip():
            self.error.setText("Le nom de l'entreprise est obligatoire.")
            return
        self.accept()

    def values(self) -> dict:
        return {"company": self.company.text(), "address": self.address.text(),
                "recipient": self.recipient.text(), "service": self.service.text()}


# ---------------------------------------------------------------------- #
class EmailPreviewDialog(QDialog):
    """Aperçu complet ; en mode confirmation, étape « Valider » du flux
    Préparer → Vérifier → Valider → Envoyer. Rien n'est envoyé ici : la fenêtre
    retourne seulement l'accord explicite de l'utilisateur."""

    def __init__(self, parent: QWidget | None, msg: EmailData, *, confirm_mode: bool,
                 errors: list[str], warnings: list[str], provider_ready: bool,
                 provider_note: str, provider_name: str):
        super().__init__(parent)
        self.setWindowTitle("Vérification avant envoi" if confirm_mode else "Aperçu de l'e-mail")
        self.resize(720, 700)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 16)
        lay.setSpacing(10)

        steps = QHBoxLayout()
        for i, (label, on) in enumerate([("Préparer", True), ("Vérifier", True),
                                         ("Valider", confirm_mode), ("Envoyer", False)]):
            lbl = QLabel(("✓ " if on and i < (2 if not confirm_mode else 2) else "") + label)
            lbl.setObjectName("StepOn" if on else "StepOff")
            steps.addWidget(lbl)
            if i < 3:
                arrow = QLabel("→")
                arrow.setObjectName("Muted")
                steps.addWidget(arrow)
        steps.addStretch(1)
        lay.addLayout(steps)

        def row(label: str, value: str) -> QLabel:
            lbl = QLabel(f"<span style='color:gray'>{label}</span>&nbsp;&nbsp;{_esc(value) or '—'}")
            lbl.setTextFormat(Qt.TextFormat.RichText)
            lbl.setWordWrap(True)
            lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            return lbl

        lay.addWidget(row("À&nbsp;:", ", ".join(msg.to)))
        if msg.cc:
            lay.addWidget(row("Cc&nbsp;:", ", ".join(msg.cc)))
        if msg.bcc:
            lay.addWidget(row("Cci&nbsp;:", ", ".join(msg.bcc)))
        lay.addWidget(row("Objet&nbsp;:", msg.subject))

        body = QTextBrowser()
        body.setStyleSheet("QTextBrowser{background:#ffffff;color:#111111;border-radius:8px;"
                           "padding:10px;}")
        body.setHtml(msg.body_html or "<p><i>(message vide)</i></p>")
        lay.addWidget(body, 1)

        lay.addWidget(QLabel(f"Pièces jointes ({len(msg.attachments)})"))
        attachments = QListWidget()
        attachments.setMaximumHeight(90)
        for a in msg.attachments:
            attachments.addItem(Path(a).name)
        attachments.itemDoubleClicked.connect(
            lambda item: open_path(msg.attachments[attachments.row(item)]))
        lay.addWidget(attachments)

        for text in errors:
            b = QLabel("✕ " + text)
            b.setObjectName("BannerError")
            b.setWordWrap(True)
            lay.addWidget(b)
        for text in warnings:
            b = QLabel("⚠ " + text)
            b.setObjectName("BannerWarn")
            b.setWordWrap(True)
            lay.addWidget(b)

        self.confirm = QCheckBox("J'ai vérifié le destinataire, l'objet, le message et les pièces jointes.")
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        close = make_button("Annuler" if confirm_mode else "Fermer")
        close.clicked.connect(self.reject)
        buttons.addWidget(close)

        if confirm_mode:
            if not provider_ready:
                b = QLabel(f"Envoi indisponible ({provider_name}) : {provider_note}")
                b.setObjectName("BannerError")
                b.setWordWrap(True)
                lay.addWidget(b)
            else:
                lay.addWidget(self.confirm)
            self.send_btn = make_button("Confirmer et envoyer", "Primary")
            self.send_btn.setEnabled(False)
            self.send_btn.clicked.connect(self.accept)
            can = provider_ready and not errors
            self.confirm.toggled.connect(lambda on: self.send_btn.setEnabled(on and can))
            buttons.addWidget(self.send_btn)
        lay.addLayout(buttons)


def _esc(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def ask_yes_no(parent: QWidget, title: str, text: str, *, danger: bool = False) -> bool:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning if danger else QMessageBox.Icon.Question)
    box.setWindowTitle(title)
    box.setText(text)
    yes = box.addButton("Oui", QMessageBox.ButtonRole.YesRole)
    box.addButton("Non", QMessageBox.ButtonRole.NoRole)
    box.setDefaultButton(box.buttons()[1])
    box.exec()
    return box.clickedButton() is yes
