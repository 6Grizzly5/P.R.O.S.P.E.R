"""Interface de conversation reliée à l'assistant existant (via AssistantService)."""
from __future__ import annotations

import logging

from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QPlainTextEdit, QScrollArea, QVBoxLayout,
                             QWidget)

from app.gui.components import ChatBubble, TypingBubble, icon, make_button, page_header
from app.gui.context import AppContext
from app.gui.dialogs import LetterDialog, ask_yes_no, open_path
from app.gui.workers import run_async
from app.services.assistant_service import Plan

log = logging.getLogger("prosper.gui.assistant")

WELCOME = ("Bonjour 👋 Je suis **P.R.O.S.P.E.R**. Je peux répondre à vos questions, ouvrir des "
           "applications, donner l'heure ou des infos système, gérer des dossiers, "
           "mémoriser des informations et préparer vos lettres de stage.\n\n"
           "Essayez : *« Quelle heure est-il ? »* ou *« Prépare une lettre de stage pour Airtel »*.")


class _Input(QPlainTextEdit):
    """Entrée = envoyer ; Maj+Entrée = nouvelle ligne."""
    submitted = pyqtSignal()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (
                event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.submitted.emit()
            return
        super().keyPressEvent(event)


class AssistantView(QWidget):
    documentsChanged = pyqtSignal()

    def __init__(self, ctx: AppContext):
        super().__init__()
        self.setObjectName("Page")
        self.ctx = ctx
        self._busy = False
        self._typing: TypingBubble | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 24)
        root.setSpacing(14)

        top = QHBoxLayout()
        top.addLayout(page_header("Assistant IA", "Conversation avec le même assistant que le terminal."), 1)
        self.clear_btn = make_button("Effacer la conversation")
        self.clear_btn.clicked.connect(self.clear_conversation)
        top.addWidget(self.clear_btn)
        root.addLayout(top)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.thread = QWidget()
        self.thread_lay = QVBoxLayout(self.thread)
        self.thread_lay.setContentsMargins(4, 4, 12, 4)
        self.thread_lay.setSpacing(12)
        self.thread_lay.addStretch(1)
        self.scroll.setWidget(self.thread)
        root.addWidget(self.scroll, 1)

        bar = QHBoxLayout()
        bar.setSpacing(10)
        self.input = _Input()
        self.input.setPlaceholderText("Écrivez un message… (Entrée pour envoyer, Maj+Entrée pour une nouvelle ligne)")
        self.input.setFixedHeight(56)
        self.input.submitted.connect(self.send)
        self.send_btn = make_button("Envoyer", "Primary")
        self.send_btn.clicked.connect(self.send)
        self._send_icon_color = "#06121A"
        bar.addWidget(self.input, 1)
        bar.addWidget(self.send_btn)
        root.addLayout(bar)

        self._add("assistant", WELCOME)

    def apply_palette(self, p: dict) -> None:
        self.send_btn.setIcon(icon("send", p["on_accent"], 16))

    # ------------------------------------------------------------------ #
    def _add(self, role: str, text: str) -> ChatBubble:
        bubble = ChatBubble(text, role)
        self.thread_lay.insertWidget(self.thread_lay.count() - 1, bubble)
        QTimer.singleShot(40, self._scroll_bottom)
        return bubble

    def _scroll_bottom(self) -> None:
        bar = self.scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def clear_conversation(self) -> None:
        if self._busy:
            return
        while self.thread_lay.count() > 1:
            item = self.thread_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._add("assistant", "Conversation effacée. Comment puis-je vous aider ?")

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.send_btn.setEnabled(not busy)
        self.input.setReadOnly(busy)
        self.clear_btn.setEnabled(not busy)
        if busy:
            self._typing = TypingBubble()
            self.thread_lay.insertWidget(self.thread_lay.count() - 1, self._typing)
            QTimer.singleShot(40, self._scroll_bottom)
        elif self._typing is not None:
            self._typing.stop()
            self._typing.deleteLater()
            self._typing = None

    # ------------------------------------------------------------------ #
    def send(self) -> None:
        text = self.input.toPlainText().strip()
        if not text or self._busy:
            return
        self.input.clear()
        self._add("user", text)
        self._set_busy(True)
        run_async(self.ctx.assistant.plan, self._on_plan, self._on_error, text)

    def _on_error(self, message: str) -> None:
        self._set_busy(False)
        self._add("assistant", f"⚠️ {message}")

    def _on_plan(self, plan: Plan) -> None:
        if plan.kind == "error":
            self._set_busy(False)
            self._add("assistant", f"⚠️ {plan.error}")
            return
        if plan.kind == "letter":
            self._set_busy(False)
            self._letter_flow(plan.company)
            return
        if plan.needs_confirmation and not ask_yes_no(
                self, "Confirmer la suppression",
                f"Confirmer la suppression de « {plan.argument} » ?", danger=True):
            self._set_busy(False)
            self._add("assistant", "Suppression annulée.")
            return
        run_async(self.ctx.assistant.finish, self._on_reply, self._on_error, plan)

    def _on_reply(self, text: str) -> None:
        self._set_busy(False)
        self._add("assistant", text or "(réponse vide)")

    # ------------------------------------------------------------------ #
    # Lettres : le formulaire remplace l'assistant interactif du CLI
    # ------------------------------------------------------------------ #
    def start_letter(self, company: str = "") -> None:
        self._letter_flow(company)

    def _letter_flow(self, company: str) -> None:
        dlg = LetterDialog(self, company)
        if dlg.exec() != LetterDialog.DialogCode.Accepted:
            self._add("assistant", "Génération de la lettre annulée.")
            return
        values = dlg.values()
        self._set_busy(True)
        run_async(lambda: self.ctx.letters.generate(**values), self._on_letter, self._on_error)

    def _on_letter(self, result) -> None:
        path, label = result
        self._set_busy(False)
        self._add("assistant", f"✅ Lettre créée (modèle **{label}**) :\n\n`{path}`")
        self.documentsChanged.emit()
        if ask_yes_no(self, "Lettre créée", "Ouvrir le PDF maintenant ?"):
            open_path(path)
