"""Paramètres : IA, chemins par défaut, e-mail, apparence, informations."""
from __future__ import annotations

import logging
import platform

from PyQt6.QtCore import PYQT_VERSION_STR, Qt, pyqtSignal
from PyQt6.QtWidgets import (QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                             QMessageBox, QScrollArea, QVBoxLayout, QWidget, QFrame)

from app.core.config import APP_NAME, VERSION
from app.gui import GUI_VERSION
from app.gui.components import Card, make_button, page_header
from app.gui.context import AppContext
from app.gui.theme import ACCENT_LABELS, THEME_LABELS
from app.gui.workers import run_async

log = logging.getLogger("prosper.gui.settings")


def _section(title: str) -> tuple[Card, QFormLayout]:
    card = Card()
    outer = QVBoxLayout(card)
    outer.setContentsMargins(20, 16, 20, 18)
    outer.setSpacing(12)
    t = QLabel(title)
    t.setObjectName("SectionTitle")
    outer.addWidget(t)
    form = QFormLayout()
    form.setSpacing(10)
    form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    outer.addLayout(form)
    return card, form


class SettingsView(QWidget):
    appearanceChanged = pyqtSignal(str, str)   # theme, accent
    settingsSaved = pyqtSignal()

    def __init__(self, ctx: AppContext):
        super().__init__()
        self.setObjectName("Page")
        self.ctx = ctx
        s = ctx.settings

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 24)
        outer.setSpacing(14)
        top = QHBoxLayout()
        top.addLayout(page_header("Paramètres", "Configuration de l'assistant et de l'application."), 1)
        self.save_btn = make_button("Enregistrer", "Primary")
        self.save_btn.clicked.connect(self.save)
        top.addWidget(self.save_btn)
        outer.addLayout(top)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(0, 0, 12, 0)
        lay.setSpacing(14)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        # --- IA ---
        card, form = _section("Intelligence artificielle")
        provider = QLabel("Google Gemini (le modèle est défini dans app/ai/gemini.py)")
        provider.setObjectName("Muted")
        form.addRow("Fournisseur", provider)
        self.key_status = QLabel()
        form.addRow("Clé API", self.key_status)
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("Collez une nouvelle clé pour remplacer l'actuelle")
        form.addRow("Nouvelle clé", self.key_input)
        row = QHBoxLayout()
        self.key_save = make_button("Enregistrer la clé")
        self.key_save.clicked.connect(self.save_key)
        self.key_test = make_button("Tester la connexion")
        self.key_test.clicked.connect(self.test_key)
        row.addWidget(self.key_save)
        row.addWidget(self.key_test)
        row.addStretch(1)
        form.addRow("", row)
        self.key_msg = QLabel("")
        self.key_msg.setWordWrap(True)
        form.addRow("", self.key_msg)
        lay.addWidget(card)

        # --- Chemins ---
        card, form = _section("Documents")
        self.docs_dir = self._path_row(form, "Dossier des documents", s.get("documents_dir"), folder=True,
                                       placeholder="Par défaut : dossier « Candidatures »")
        self.cv = self._path_row(form, "CV par défaut", s.get("cv_path"))
        self.school = self._path_row(form, "Lettre de présentation de l'école", s.get("school_letter_path"))
        lay.addWidget(card)

        # --- E-mail ---
        card, form = _section("Compte e-mail")
        provider = QLabel("Gmail (API OAuth 2.0) — aucun mot de passe n'est stocké")
        provider.setObjectName("Muted")
        form.addRow("Fournisseur", provider)
        self.account = QLineEdit(s.get("email_account"))
        self.account.setPlaceholderText("votre.adresse@gmail.com (information)")
        form.addRow("Adresse", self.account)
        self.creds = self._path_row(form, "Fichier credentials.json", s.get("gmail_credentials_path"),
                                    placeholder="Fichier OAuth « Application de bureau » (Google Cloud)")
        self.mail_status = QLabel()
        self.mail_status.setWordWrap(True)
        form.addRow("État", self.mail_status)
        lay.addWidget(card)

        # --- Apparence ---
        card, form = _section("Apparence")
        self.name = QLineEdit(s.get("display_name"))
        self.name.setPlaceholderText("Pour le message d'accueil (optionnel)")
        form.addRow("Nom affiché", self.name)
        self.theme = QComboBox()
        for k, v in THEME_LABELS.items():
            self.theme.addItem(v, k)
        self.theme.setCurrentIndex(max(0, self.theme.findData(s.get("theme"))))
        form.addRow("Thème", self.theme)
        self.accent = QComboBox()
        for k, v in ACCENT_LABELS.items():
            self.accent.addItem(v, k)
        self.accent.setCurrentIndex(max(0, self.accent.findData(s.get("accent"))))
        form.addRow("Couleur d'accent", self.accent)
        lay.addWidget(card)

        # --- À propos ---
        card, form = _section("À propos")
        for label, value in (("Application", f"{APP_NAME}  —  Personal AI Assistant"),
                             ("Backend", f"v{VERSION}"), ("Interface graphique", f"v{GUI_VERSION}"),
                             ("Python / PyQt", f"{platform.python_version()} / {PYQT_VERSION_STR}")):
            v = QLabel(value)
            v.setObjectName("Muted")
            form.addRow(label, v)
        lay.addWidget(card)
        lay.addStretch(1)
        self.refresh()

    def _path_row(self, form: QFormLayout, label: str, value: str, folder: bool = False,
                  placeholder: str = "") -> QLineEdit:
        edit = QLineEdit(value or "")
        edit.setPlaceholderText(placeholder)
        btn = make_button("Parcourir…")

        def browse():
            if folder:
                path = QFileDialog.getExistingDirectory(self, label, edit.text())
            else:
                path, _ = QFileDialog.getOpenFileName(self, label, edit.text())
            if path:
                edit.setText(path)

        btn.clicked.connect(browse)
        row = QHBoxLayout()
        row.addWidget(edit, 1)
        row.addWidget(btn)
        form.addRow(label, row)
        return edit

    # ------------------------------------------------------------------ #
    def refresh(self) -> None:
        ok, masked = self.ctx.settings.api_key_status()
        self.key_status.setText(f"Configurée  {masked}" if ok else "Non configurée")
        self.key_status.setObjectName("Ok" if ok else "Danger")
        self.key_status.style().unpolish(self.key_status)
        self.key_status.style().polish(self.key_status)
        ready, note = self.ctx.email.readiness()
        self.mail_status.setText(("✓ " if ready else "✕ ") + note)
        self.mail_status.setObjectName("Ok" if ready else "Danger")
        self.mail_status.style().unpolish(self.mail_status)
        self.mail_status.style().polish(self.mail_status)

    def _msg(self, text: str, ok: bool) -> None:
        self.key_msg.setText(text)
        self.key_msg.setObjectName("Ok" if ok else "Danger")
        self.key_msg.style().unpolish(self.key_msg)
        self.key_msg.style().polish(self.key_msg)

    def save_key(self) -> None:
        try:
            self.ctx.settings.set_api_key(self.key_input.text())
        except (ValueError, OSError) as exc:
            self._msg(str(exc), False)
            return
        self.key_input.clear()
        self._msg("Clé enregistrée dans .env.", True)
        self.refresh()
        self.settingsSaved.emit()

    def test_key(self) -> None:
        self.key_test.setEnabled(False)
        self._msg("Test en cours…", True)

        def probe() -> str:
            from app.ai.gemini import ask_gemini
            return ask_gemini("Réponds uniquement par le mot : OK")

        def done(reply):
            self.key_test.setEnabled(True)
            self._msg("Connexion réussie : l'IA répond.", True)

        def failed(err):
            self.key_test.setEnabled(True)
            self._msg(f"Échec de la connexion : {err}", False)

        run_async(probe, done, failed)

    def save(self) -> None:
        s = self.ctx.settings
        s.update({
            "documents_dir": self.docs_dir.text().strip(), "cv_path": self.cv.text().strip(),
            "school_letter_path": self.school.text().strip(), "email_account": self.account.text().strip(),
            "gmail_credentials_path": self.creds.text().strip(), "display_name": self.name.text().strip(),
            "theme": self.theme.currentData(), "accent": self.accent.currentData(),
        })
        self.appearanceChanged.emit(self.theme.currentData(), self.accent.currentData())
        self.refresh()
        self.settingsSaved.emit()
        QMessageBox.information(self, "Paramètres", "Paramètres enregistrés.")
