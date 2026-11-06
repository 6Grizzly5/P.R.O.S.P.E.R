"""Tableau de bord : uniquement des données réelles (ou un état vide explicite)."""
from __future__ import annotations

from PyQt6.QtCore import QDateTime, QLocale, QTimer, pyqtSignal
from PyQt6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget)

from app.gui.components import Card, EmptyState, StatCard, make_button, page_header
from app.gui.context import AppContext
from app.services.career_db import STATUSES


class DashboardView(QWidget):
    navigate = pyqtSignal(str)          # clé de page
    letterRequested = pyqtSignal()

    def __init__(self, ctx: AppContext):
        super().__init__()
        self.setObjectName("Page")
        self.ctx = ctx

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 24)
        root.setSpacing(18)

        top = QHBoxLayout()
        self.title_box = page_header("Bienvenue", "Votre assistant personnel — prêt à travailler.")
        self.title = self.title_box.itemAt(0).widget()
        top.addLayout(self.title_box, 1)
        self.clock = QLabel()
        self.clock.setObjectName("Clock")
        top.addWidget(self.clock)
        root.addLayout(top)

        # Statut de l'assistant
        status = Card()
        s_lay = QHBoxLayout(status)
        s_lay.setContentsMargins(18, 12, 18, 12)
        self.status_dot = QLabel("●")
        self.status_text = QLabel()
        s_lay.addWidget(self.status_dot)
        s_lay.addWidget(self.status_text, 1)
        root.addWidget(status)

        # Statistiques réelles
        stats = QHBoxLayout()
        stats.setSpacing(14)
        self.stat_apps = StatCard("Candidatures enregistrées")
        self.stat_docs = StatCard("Documents générés")
        self.stat_drafts = StatCard("Brouillons d'e-mails")
        for s in (self.stat_apps, self.stat_docs, self.stat_drafts):
            stats.addWidget(s)
        root.addLayout(stats)

        # Accès rapides
        quick = QHBoxLayout()
        quick.setSpacing(10)
        for text, key in (("Parler à l'assistant", "assistant"), ("Nouvelle candidature", "career"),
                          ("Écrire un e-mail", "email")):
            b = make_button(text, "Primary" if key == "assistant" else "")
            b.clicked.connect(lambda _=False, k=key: self.navigate.emit(k))
            quick.addWidget(b)
        letter = make_button("Générer une lettre")
        letter.clicked.connect(self.letterRequested.emit)
        quick.addWidget(letter)
        quick.addStretch(1)
        root.addLayout(quick)

        # Activité récente + pipeline
        bottom = QHBoxLayout()
        bottom.setSpacing(14)
        self.recent_card = Card()
        self.recent_lay = QVBoxLayout(self.recent_card)
        self.recent_lay.setContentsMargins(18, 14, 18, 14)
        bottom.addWidget(self.recent_card, 3)
        self.pipe_card = Card()
        self.pipe_lay = QVBoxLayout(self.pipe_card)
        self.pipe_lay.setContentsMargins(18, 14, 18, 14)
        bottom.addWidget(self.pipe_card, 2)
        root.addLayout(bottom, 1)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._tick()
        self.refresh()

    # ------------------------------------------------------------------ #
    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        self._timer.start()
        self.refresh()

    def hideEvent(self, event):  # noqa: N802
        super().hideEvent(event)
        self._timer.stop()      # pas de tick inutile quand la page n'est pas visible

    def _tick(self) -> None:
        text = QLocale(QLocale.Language.French).toString(
            QDateTime.currentDateTime(), "dddd d MMMM yyyy  ·  HH:mm:ss")
        self.clock.setText(text[:1].upper() + text[1:])

    @staticmethod
    def _clear(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def refresh(self) -> None:
        name = (self.ctx.settings.get("display_name") or "").strip()
        self.title.setText(f"Bonjour, {name}" if name else "Bienvenue")

        ready = self.ctx.assistant.ai_ready()
        self.status_dot.setObjectName("Ok" if ready else "Danger")
        self.status_dot.setStyleSheet("")  # force la relecture du QSS
        self.status_dot.style().unpolish(self.status_dot)
        self.status_dot.style().polish(self.status_dot)
        self.status_text.setText("Assistant prêt — Gemini connecté (clé API détectée)" if ready else
                                 "Assistant IA indisponible — configurez la clé API dans les Paramètres")

        n_apps = self.ctx.db.count_companies()
        n_docs = self.ctx.documents.count()
        sent = self.ctx.db.count_sent()
        self.stat_apps.set_value(n_apps, "" if n_apps else "Aucune pour l'instant")
        self.stat_docs.set_value(n_docs, "" if n_docs else "Aucun pour l'instant")
        self.stat_drafts.set_value(self.ctx.db.count_drafts(), f"{sent} envoyé(s)" if sent else "")

        # Activité récente (history.json du backend, partagé avec le CLI)
        self._clear(self.recent_lay)
        t = QLabel("Activité récente")
        t.setObjectName("SectionTitle")
        self.recent_lay.addWidget(t)
        history = list(reversed(self.ctx.assistant.recent_history(8)))
        if not history:
            self.recent_lay.addWidget(EmptyState("Aucune activité enregistrée."))
        for entry in history:
            line = QHBoxLayout()
            cmd = QLabel(str(entry.get("command", "")))
            cmd.setWordWrap(True)
            when = QLabel(str(entry.get("timestamp", "")))
            when.setObjectName("Muted")
            line.addWidget(cmd, 1)
            line.addWidget(when)
            holder = QWidget()
            holder.setLayout(line)
            line.setContentsMargins(0, 2, 0, 2)
            self.recent_lay.addWidget(holder)
        self.recent_lay.addStretch(1)

        # Répartition réelle des candidatures par statut
        self._clear(self.pipe_lay)
        t2 = QLabel("Suivi des candidatures")
        t2.setObjectName("SectionTitle")
        self.pipe_lay.addWidget(t2)
        counts = self.ctx.db.counts_by_status()
        if n_apps == 0:
            self.pipe_lay.addWidget(EmptyState("Ajoutez une entreprise dans « Candidatures »."))
        else:
            grid = QGridLayout()
            r = 0
            for code, label in STATUSES.items():
                if counts.get(code):
                    grid.addWidget(QLabel(label), r, 0)
                    v = QLabel(str(counts[code]))
                    v.setObjectName("Muted")
                    grid.addWidget(v, r, 1)
                    r += 1
            holder = QWidget()
            holder.setLayout(grid)
            self.pipe_lay.addWidget(holder)
        self.pipe_lay.addStretch(1)
