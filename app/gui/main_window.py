"""Fenêtre principale : barre latérale persistante + zone centrale dynamique (vues créées à la demande)."""
from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QApplication, QButtonGroup, QFrame, QHBoxLayout, QLabel, QMainWindow,
                             QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from app.core.config import APP_NAME, BASE_DIR, VERSION
from app.gui import GUI_VERSION
from app.gui.components import icon
from app.gui.context import AppContext
from app.gui.theme import apply_theme
from app.gui.views.assistant_view import AssistantView
from app.gui.views.career_view import CareerView
from app.gui.views.dashboard import DashboardView
from app.gui.views.documents_view import DocumentsView
from app.gui.views.email_view import EmailView
from app.gui.views.settings_view import SettingsView

log = logging.getLogger("prosper.gui")

NAV = [
    ("dashboard", "Tableau de bord", "home"),
    ("assistant", "Assistant IA", "chat"),
    ("career", "Candidatures", "briefcase"),
    ("email", "E-mails", "mail"),
    ("documents", "Documents", "file"),
    ("settings", "Paramètres", "sliders"),
]
ICON_FILE = BASE_DIR / "assets" / "icons" / "prosper.png"


class MainWindow(QMainWindow):
    def __init__(self, ctx: AppContext, app: QApplication):
        super().__init__()
        self.ctx, self.app = ctx, app
        self.setWindowTitle(f"{APP_NAME} — Personal AI Assistant")
        self.setMinimumSize(1060, 680)
        self.resize(1240, 780)
        if ICON_FILE.is_file():
            self.setWindowIcon(QIcon(str(ICON_FILE)))

        self._views: dict[str, QWidget] = {}
        self._nav_buttons: dict[str, QPushButton] = {}
        self._palette: dict = {}

        central = QWidget()
        self.setCentralWidget(central)
        row = QHBoxLayout(central)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        row.addWidget(self._build_sidebar())
        self.stack = QStackedWidget()
        row.addWidget(self.stack, 1)

        self._apply_theme()
        self.show_page("dashboard")

    # ------------------------------------------------------------------ #
    def _build_sidebar(self) -> QWidget:
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(236)
        lay = QVBoxLayout(side)
        lay.setContentsMargins(14, 22, 14, 16)
        lay.setSpacing(4)

        title = QLabel("P.R.O.S.P.E.R")
        title.setObjectName("BrandTitle")
        sub = QLabel("Personal AI Assistant")
        sub.setObjectName("BrandSub")
        lay.addWidget(title)
        lay.addWidget(sub)
        lay.addSpacing(22)

        group = QButtonGroup(self)
        group.setExclusive(True)
        for key, label, _ic in NAV:
            btn = QPushButton("  " + label)
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setIconSize(QSize(18, 18))
            btn.clicked.connect(lambda _=False, k=key: self.show_page(k))
            group.addButton(btn)
            lay.addWidget(btn)
            self._nav_buttons[key] = btn
        lay.addStretch(1)
        foot = QLabel(f"v{VERSION}  ·  GUI {GUI_VERSION}")
        foot.setObjectName("SidebarFooter")
        lay.addWidget(foot)
        return side

    # ------------------------------------------------------------------ #
    # Vues (création à la demande → démarrage rapide, mémoire réduite)
    # ------------------------------------------------------------------ #
    def _create(self, key: str) -> QWidget:
        ctx = self.ctx
        if key == "dashboard":
            v = DashboardView(ctx)
            v.navigate.connect(self.show_page)
            v.letterRequested.connect(lambda: self.start_letter(""))
        elif key == "assistant":
            v = AssistantView(ctx)
            if self._palette:
                v.apply_palette(self._palette)
        elif key == "career":
            v = CareerView(ctx)
            v.emailRequested.connect(self.compose_email)
            v.letterRequested.connect(self.start_letter)
            v.dataChanged.connect(self._career_changed)
        elif key == "email":
            v = EmailView(ctx)
        elif key == "documents":
            v = DocumentsView(ctx)
            v.letterRequested.connect(lambda: self.start_letter(""))
        else:
            v = SettingsView(ctx)
            v.appearanceChanged.connect(self._on_appearance)
            v.settingsSaved.connect(self._settings_saved)
        self._views[key] = v
        self.stack.addWidget(v)
        return v

    def view(self, key: str) -> QWidget:
        return self._views.get(key) or self._create(key)

    def show_page(self, key: str) -> None:
        widget = self.view(key)
        self.stack.setCurrentWidget(widget)
        self._nav_buttons[key].setChecked(True)

    # ------------------------------------------------------------------ #
    # Navigation croisée
    # ------------------------------------------------------------------ #
    def start_letter(self, company: str = "") -> None:
        self.show_page("assistant")
        self.view("assistant").start_letter(company)

    def compose_email(self, company_id: int) -> None:
        self.show_page("email")
        self.view("email").compose_for_company(company_id)

    def _career_changed(self) -> None:
        if "email" in self._views:
            self._views["email"].reload_companies()

    def _settings_saved(self) -> None:
        if "dashboard" in self._views:
            self._views["dashboard"].refresh()
        if "email" in self._views:
            self._views["email"].refresh_status()

    # ------------------------------------------------------------------ #
    # Thème
    # ------------------------------------------------------------------ #
    def _on_appearance(self, theme: str, accent: str) -> None:
        self._apply_theme()

    def _apply_theme(self) -> None:
        s = self.ctx.settings
        self._palette = apply_theme(self.app, s.get("theme"), s.get("accent"))
        for key, label, ic in NAV:
            self._nav_buttons[key].setIcon(icon(ic, self._palette["muted"], 18, self._palette["accent"]))
        if "assistant" in self._views:
            self._views["assistant"].apply_palette(self._palette)

    def closeEvent(self, event):  # noqa: N802
        try:
            self.ctx.db.close()
        except Exception:
            pass
        super().closeEvent(event)
