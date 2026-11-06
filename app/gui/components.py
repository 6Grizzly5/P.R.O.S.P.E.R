"""Composants réutilisables : icônes SVG minimalistes, cartes, bulles de chat, etc."""
from __future__ import annotations

from PyQt6.QtCore import QByteArray, QSize, Qt, QTimer
from PyQt6.QtGui import QFontMetrics, QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget)

_ICON_BODY = {
    "home": '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
    "chat": '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    "briefcase": '<rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
    "mail": '<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>',
    "file": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>',
    "sliders": '<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>',
    "send": '<line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>',
}


def _pixmap(name: str, color: str, size: int) -> QPixmap:
    body = _ICON_BODY[name]
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
           f'stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
           f'{body}</svg>')
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    scale = 2  # rendu net sur écrans haute densité
    pix = QPixmap(size * scale, size * scale)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    renderer.render(painter)
    painter.end()
    pix.setDevicePixelRatio(scale)
    return pix


def icon(name: str, color: str, size: int = 20, color_on: str | None = None) -> QIcon:
    """Icône SVG minimaliste ; `color_on` = couleur quand le bouton est coché."""
    ic = QIcon()
    ic.addPixmap(_pixmap(name, color, size), QIcon.Mode.Normal, QIcon.State.Off)
    ic.addPixmap(_pixmap(name, color_on or color, size), QIcon.Mode.Normal, QIcon.State.On)
    return ic


class Card(QFrame):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Card")


def page_header(title: str, subtitle: str = "") -> QVBoxLayout:
    box = QVBoxLayout()
    box.setSpacing(2)
    t = QLabel(title)
    t.setObjectName("PageTitle")
    box.addWidget(t)
    if subtitle:
        s = QLabel(subtitle)
        s.setObjectName("PageSubtitle")
        s.setWordWrap(True)
        box.addWidget(s)
    return box


def make_button(text: str, kind: str = "", ic: QIcon | None = None) -> QPushButton:
    btn = QPushButton(text)
    if kind:
        btn.setObjectName(kind)
    if ic is not None:
        btn.setIcon(ic)
        btn.setIconSize(QSize(16, 16))
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


class StatCard(Card):
    def __init__(self, title: str, value: str = "0", hint: str = ""):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(2)
        self.title = QLabel(title)
        self.title.setObjectName("StatTitle")
        self.value = QLabel(value)
        self.value.setObjectName("StatValue")
        self.hint = QLabel(hint)
        self.hint.setObjectName("Muted")
        lay.addWidget(self.title)
        lay.addWidget(self.value)
        lay.addWidget(self.hint)

    def set_value(self, value, hint: str = "") -> None:
        self.value.setText(str(value))
        self.hint.setText(hint)


class EmptyState(QLabel):
    def __init__(self, text: str):
        super().__init__(text)
        self.setObjectName("EmptyState")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)


class ChatBubble(QWidget):
    """Une ligne de conversation : bulle alignée à droite (utilisateur) ou à gauche (assistant)."""

    MAX_WIDTH = 640

    def __init__(self, text: str, role: str):
        super().__init__()
        self.role = role
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)

        bubble = QFrame()
        bubble.setObjectName("BubbleUser" if role == "user" else "BubbleBot")
        bubble.setMaximumWidth(self.MAX_WIDTH)
        lay = QVBoxLayout(bubble)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(4)

        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse
                                           | Qt.TextInteractionFlag.LinksAccessibleByMouse)
        self.label.setOpenExternalLinks(True)
        if role == "assistant":
            self.label.setTextFormat(Qt.TextFormat.MarkdownText)
        else:
            self.label.setTextFormat(Qt.TextFormat.PlainText)
        self.label.setText(text)
        self._fit(text)
        lay.addWidget(self.label)

        if role == "user":
            row.addStretch(1)
            row.addWidget(bubble)
        else:
            row.addWidget(bubble)
            row.addStretch(1)

    def _fit(self, text: str) -> None:
        """Largeur idéale de la bulle (QLabel avec retour à la ligne se réduit trop sinon)."""
        inner = self.MAX_WIDTH - 28
        plain = text.replace("**", "").replace("`", "").replace("*", "")
        rect = QFontMetrics(self.label.font()).boundingRect(
            0, 0, inner, 10_000, int(Qt.TextFlag.TextWordWrap), plain)
        self.label.setMinimumWidth(min(max(rect.width() + 8, 40), inner))

    def set_text(self, text: str) -> None:
        self.label.setText(text)
        self._fit(text)


class TypingBubble(ChatBubble):
    """Indicateur de chargement animé (léger : un seul QTimer)."""

    def __init__(self, caption: str = "P.R.O.S.P.E.R réfléchit"):
        super().__init__(caption, "assistant")
        self.label.setTextFormat(Qt.TextFormat.PlainText)
        self._caption, self._n = caption, 0
        self.label.setMinimumWidth(230)
        self._timer = QTimer(self)
        self._timer.setInterval(380)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self._tick()

    def _tick(self) -> None:
        self._n = (self._n + 1) % 4
        self.label.setText(self._caption + " " + "●" * self._n + "○" * (3 - self._n))

    def stop(self) -> None:
        self._timer.stop()
