"""Thèmes (palettes) et feuille de style QSS générée à partir d'une palette."""
from __future__ import annotations

from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QApplication

PALETTES = {
    "dark": {
        "bg": "#0D1015", "sidebar": "#11151B", "card": "#171C23", "card_alt": "#1D232C",
        "border": "#252C37", "text": "#E7EBF0", "muted": "#8A94A3", "input": "#12171E",
        "hover": "#1F2631", "on_accent": "#06121A", "danger": "#F0616D", "ok": "#3DD68C",
        "warn": "#F2B84B", "bubble_user_text": "#06121A",
    },
    "light": {
        "bg": "#F3F5F8", "sidebar": "#FFFFFF", "card": "#FFFFFF", "card_alt": "#EEF1F5",
        "border": "#D9DEE6", "text": "#161B22", "muted": "#5F6B7A", "input": "#FFFFFF",
        "hover": "#E8ECF2", "on_accent": "#FFFFFF", "danger": "#D6303F", "ok": "#1E9E63",
        "warn": "#B9770E", "bubble_user_text": "#FFFFFF",
    },
}
ACCENTS = {
    "cyan": {"dark": "#38BDF8", "light": "#0B7FB5"},
    "blue": {"dark": "#5B8DEF", "light": "#2F5FD0"},
}
ACCENT_LABELS = {"cyan": "Cyan", "blue": "Bleu"}
THEME_LABELS = {"dark": "Sombre", "light": "Clair"}

STATUS_COLORS = {
    "to_contact": "#8A94A3", "preparing": "#B08CFF", "ready": "#38BDF8", "sent": "#5B8DEF",
    "waiting": "#F2B84B", "interview": "#F58FD0", "accepted": "#3DD68C", "rejected": "#F0616D",
}


def palette(theme: str, accent: str) -> dict:
    p = dict(PALETTES.get(theme, PALETTES["dark"]))
    p["accent"] = ACCENTS.get(accent, ACCENTS["cyan"])[theme if theme in PALETTES else "dark"]
    return p


def build_qss(p: dict) -> str:
    return f"""
* {{ font-family: "Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif; font-size: 13px; }}
QWidget {{ color: {p['text']}; }}
QMainWindow, QDialog, QStackedWidget, #Page {{ background: {p['bg']}; }}
QToolTip {{ background: {p['card_alt']}; color: {p['text']}; border: 1px solid {p['border']};
    padding: 4px 8px; }}

/* ---- Sidebar ---- */
#Sidebar {{ background: {p['sidebar']}; border-right: 1px solid {p['border']}; }}
#BrandTitle {{ font-size: 17px; font-weight: 700; letter-spacing: 3px; }}
#BrandSub {{ color: {p['muted']}; font-size: 11px; }}
#NavButton {{ background: transparent; border: none; border-radius: 8px; padding: 10px 14px;
    text-align: left; color: {p['muted']}; font-size: 13px; }}
#NavButton:hover {{ background: {p['hover']}; color: {p['text']}; }}
#NavButton:checked {{ background: {p['card_alt']}; color: {p['text']}; font-weight: 600;
    border-left: 3px solid {p['accent']}; }}
#SidebarFooter {{ color: {p['muted']}; font-size: 11px; }}

/* ---- Textes ---- */
#PageTitle {{ font-size: 24px; font-weight: 700; }}
#PageSubtitle {{ color: {p['muted']}; font-size: 13px; }}
#SectionTitle {{ font-size: 14px; font-weight: 600; }}
#Muted {{ color: {p['muted']}; }}
#StatValue {{ font-size: 30px; font-weight: 700; color: {p['accent']}; }}
#StatTitle {{ color: {p['muted']}; font-size: 12px; }}
#Clock {{ font-size: 13px; color: {p['muted']}; }}
#EmptyState {{ color: {p['muted']}; padding: 18px; }}
#Danger {{ color: {p['danger']}; }}
#Ok {{ color: {p['ok']}; }}

/* ---- Cartes ---- */
#Card {{ background: {p['card']}; border: 1px solid {p['border']}; border-radius: 12px; }}
#Banner {{ background: {p['card_alt']}; border: 1px solid {p['border']}; border-radius: 8px;
    padding: 8px 12px; }}
#BannerWarn {{ background: {p['card_alt']}; border: 1px solid {p['warn']}; border-radius: 8px;
    padding: 8px 12px; color: {p['warn']}; }}
#BannerError {{ background: {p['card_alt']}; border: 1px solid {p['danger']}; border-radius: 8px;
    padding: 8px 12px; color: {p['danger']}; }}

/* ---- Boutons ---- */
QPushButton {{ background: {p['card_alt']}; border: 1px solid {p['border']}; border-radius: 8px;
    padding: 8px 16px; color: {p['text']}; }}
QPushButton:hover {{ background: {p['hover']}; border-color: {p['accent']}; }}
QPushButton:pressed {{ background: {p['border']}; }}
QPushButton:disabled {{ color: {p['muted']}; background: {p['card']}; border-color: {p['border']}; }}
QPushButton#Primary {{ background: {p['accent']}; border: 1px solid {p['accent']};
    color: {p['on_accent']}; font-weight: 600; }}
QPushButton#Primary:hover {{ background: {p['accent']}; border-color: {p['text']}; }}
QPushButton#Primary:disabled {{ background: {p['card_alt']}; color: {p['muted']};
    border-color: {p['border']}; }}
QPushButton#DangerButton {{ color: {p['danger']}; }}
QPushButton#DangerButton:hover {{ border-color: {p['danger']}; }}
QPushButton#Flat {{ background: transparent; border: none; color: {p['accent']}; padding: 4px 8px; }}
QPushButton#Flat:hover {{ background: {p['hover']}; }}
QPushButton#Chip {{ background: {p['card_alt']}; border: 1px solid {p['border']};
    border-radius: 14px; padding: 5px 12px; color: {p['muted']}; }}
QPushButton#Chip:hover {{ color: {p['text']}; border-color: {p['accent']}; }}
QToolButton {{ background: {p['card_alt']}; border: 1px solid {p['border']}; border-radius: 6px;
    padding: 5px 9px; color: {p['text']}; }}
QToolButton:hover {{ border-color: {p['accent']}; }}
QToolButton:checked {{ background: {p['accent']}; color: {p['on_accent']}; }}

/* ---- Champs ---- */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QDateEdit, QSpinBox, QTextBrowser {{
    background: {p['input']}; border: 1px solid {p['border']}; border-radius: 8px;
    padding: 7px 10px; selection-background-color: {p['accent']};
    selection-color: {p['on_accent']}; }}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QDateEdit:focus {{
    border: 1px solid {p['accent']}; }}
QLineEdit:disabled, QComboBox:disabled, QDateEdit:disabled {{ color: {p['muted']}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{ background: {p['card']}; border: 1px solid {p['border']};
    selection-background-color: {p['hover']}; selection-color: {p['text']}; outline: none; }}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px;
    border: 1px solid {p['border']}; background: {p['input']}; }}
QCheckBox::indicator:checked {{ background: {p['accent']}; border-color: {p['accent']}; }}

/* ---- Listes & tables ---- */
QListWidget {{ background: {p['card']}; border: 1px solid {p['border']}; border-radius: 10px;
    padding: 4px; outline: none; }}
QListWidget::item {{ padding: 8px 10px; border-radius: 6px; }}
QListWidget::item:hover {{ background: {p['hover']}; }}
QListWidget::item:selected {{ background: {p['card_alt']}; color: {p['text']};
    border-left: 3px solid {p['accent']}; }}
QTableWidget {{ background: {p['card']}; border: 1px solid {p['border']}; border-radius: 10px;
    gridline-color: transparent; outline: none; alternate-background-color: {p['card']};
    selection-background-color: {p['card_alt']}; selection-color: {p['text']}; }}
QTableWidget::item {{ padding: 6px 10px; border-bottom: 1px solid {p['border']}; }}
QTableWidget::item:selected {{ background: {p['card_alt']}; }}
QHeaderView::section {{ background: {p['card']}; color: {p['muted']}; border: none;
    border-bottom: 1px solid {p['border']}; padding: 8px 10px; font-weight: 600; font-size: 12px; }}
QTableCornerButton::section {{ background: {p['card']}; border: none; }}

/* ---- Scrollbars ---- */
QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {p['border']}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {p['muted']}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {p['border']}; border-radius: 4px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* ---- Messages de chat ---- */
#BubbleUser {{ background: {p['accent']}; border-radius: 14px; border-bottom-right-radius: 4px; }}
#BubbleUser QLabel {{ color: {p['bubble_user_text']}; }}
#BubbleBot {{ background: {p['card']}; border: 1px solid {p['border']}; border-radius: 14px;
    border-bottom-left-radius: 4px; }}
#BubbleRole {{ color: {p['muted']}; font-size: 11px; }}

/* ---- Étapes d'envoi ---- */
#StepOn {{ color: {p['accent']}; font-weight: 700; }}
#StepOff {{ color: {p['muted']}; }}

QMenu {{ background: {p['card']}; border: 1px solid {p['border']}; padding: 4px; }}
QMenu::item {{ padding: 7px 18px; border-radius: 5px; }}
QMenu::item:selected {{ background: {p['hover']}; }}
QGroupBox {{ border: none; }}
"""


def apply_theme(app: QApplication, theme: str, accent: str) -> dict:
    p = palette(theme, accent)
    app.setStyleSheet(build_qss(p))
    font = QFont("Segoe UI", 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)
    return p


def status_qcolor(code: str) -> QColor:
    return QColor(STATUS_COLORS.get(code, "#8A94A3"))
