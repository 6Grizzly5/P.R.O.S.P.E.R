"""Career Manager : suivi des candidatures (SQLite)."""
from __future__ import annotations

import logging
from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QAbstractItemView, QComboBox, QHBoxLayout, QHeaderView, QLabel,
                             QLineEdit, QMessageBox, QTableWidget, QTableWidgetItem, QVBoxLayout,
                             QWidget)

from app.gui.components import EmptyState, make_button, page_header
from app.gui.context import AppContext
from app.gui.dialogs import CompanyDialog, ask_yes_no
from app.gui.theme import status_qcolor
from app.services.career_db import STATUSES

log = logging.getLogger("prosper.gui.career")

COLUMNS = ["Entreprise", "Secteur", "E-mail RH", "Objectif", "Candidature", "Statut"]


def _fmt_date(iso: str) -> str:
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return "—"


class CareerView(QWidget):
    emailRequested = pyqtSignal(int)      # id entreprise
    letterRequested = pyqtSignal(str)     # nom entreprise
    dataChanged = pyqtSignal()

    def __init__(self, ctx: AppContext):
        super().__init__()
        self.setObjectName("Page")
        self.ctx = ctx
        self._rows: list[dict] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 24)
        root.setSpacing(14)

        top = QHBoxLayout()
        top.addLayout(page_header("Candidatures", "Suivez chaque entreprise, de la prise de contact à la réponse."), 1)
        self.add_btn = make_button("Ajouter une entreprise", "Primary")
        self.add_btn.clicked.connect(self.add_company)
        top.addWidget(self.add_btn)
        root.addLayout(top)

        self.overview = QLabel()
        self.overview.setObjectName("Muted")
        self.overview.setWordWrap(True)
        root.addWidget(self.overview)

        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Rechercher (entreprise, secteur, e-mail, objectif)…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.refresh)
        self.status_filter = QComboBox()
        self.status_filter.addItem("Tous les statuts", "")
        for code, label in STATUSES.items():
            self.status_filter.addItem(label, code)
        self.status_filter.currentIndexChanged.connect(self.refresh)
        filters.addWidget(self.search, 1)
        filters.addWidget(self.status_filter)
        root.addLayout(filters)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setShowGrid(False)
        hdr = self.table.horizontalHeader()
        hdr.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        modes = (QHeaderView.ResizeMode.Interactive, QHeaderView.ResizeMode.Interactive,
                 QHeaderView.ResizeMode.Interactive, QHeaderView.ResizeMode.Stretch,
                 QHeaderView.ResizeMode.ResizeToContents, QHeaderView.ResizeMode.ResizeToContents)
        for i, mode in enumerate(modes):
            hdr.setSectionResizeMode(i, mode)
        for i, w in enumerate((190, 130, 210)):
            self.table.setColumnWidth(i, w)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.doubleClicked.connect(lambda _: self.edit_company())
        self.table.itemSelectionChanged.connect(self._update_buttons)
        root.addWidget(self.table, 1)

        self.empty = EmptyState("Aucune entreprise pour l'instant.\nCliquez sur « Ajouter une entreprise » pour commencer.")
        root.addWidget(self.empty)

        actions = QHBoxLayout()
        self.edit_btn = make_button("Modifier")
        self.edit_btn.clicked.connect(self.edit_company)
        self.del_btn = make_button("Supprimer", "DangerButton")
        self.del_btn.clicked.connect(self.delete_company)
        self.letter_btn = make_button("Générer une lettre")
        self.letter_btn.clicked.connect(self._letter)
        self.mail_btn = make_button("Écrire un e-mail")
        self.mail_btn.clicked.connect(self._email)
        for b in (self.edit_btn, self.del_btn, self.letter_btn, self.mail_btn):
            actions.addWidget(b)
        actions.addStretch(1)
        root.addLayout(actions)
        self.refresh()

    # ------------------------------------------------------------------ #
    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        self.refresh()

    def current_id(self) -> int | None:
        row = self.table.currentRow()
        if 0 <= row < len(self._rows):
            return self._rows[row]["id"]
        return None

    def _update_buttons(self) -> None:
        has = self.current_id() is not None
        for b in (self.edit_btn, self.del_btn, self.letter_btn, self.mail_btn):
            b.setEnabled(has)

    def refresh(self) -> None:
        keep = self.current_id()
        self._rows = self.ctx.db.list_companies(self.search.text(), self.status_filter.currentData() or "")
        self.table.setRowCount(len(self._rows))
        for r, c in enumerate(self._rows):
            cells = [c["name"], c["sector"], c["hr_email"], c["target"],
                     _fmt_date(c["applied_date"]) if c["applied_date"] else "—",
                     STATUSES.get(c["status"], c["status"])]
            for col, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if col == 5:
                    item.setForeground(status_qcolor(c["status"]))
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)
                self.table.setItem(r, col, item)
            if c["id"] == keep:
                self.table.selectRow(r)
        total = self.ctx.db.count_companies()
        self.table.setVisible(bool(self._rows))
        self.empty.setVisible(not self._rows)
        if total and not self._rows:
            self.empty.setText("Aucun résultat pour ces filtres.")
        elif not total:
            self.empty.setText("Aucune entreprise pour l'instant.\nCliquez sur « Ajouter une entreprise » pour commencer.")
        counts = self.ctx.db.counts_by_status()
        parts = [f"{STATUSES[c]} : {n}" for c, n in counts.items() if n]
        self.overview.setText(f"{total} entreprise(s)" + ("  ·  " + "   |   ".join(parts) if parts else ""))
        self._update_buttons()

    # ------------------------------------------------------------------ #
    def add_company(self) -> None:
        dlg = CompanyDialog(self)
        if dlg.exec() == CompanyDialog.DialogCode.Accepted:
            try:
                self.ctx.db.add_company(**dlg.values())
            except ValueError as exc:
                QMessageBox.warning(self, "Entreprise", str(exc))
                return
            self.refresh()
            self.dataChanged.emit()

    def edit_company(self) -> None:
        cid = self.current_id()
        if cid is None:
            return
        dlg = CompanyDialog(self, self.ctx.db.get_company(cid))
        if dlg.exec() == CompanyDialog.DialogCode.Accepted:
            try:
                self.ctx.db.update_company(cid, **dlg.values())
            except ValueError as exc:
                QMessageBox.warning(self, "Entreprise", str(exc))
                return
            self.refresh()
            self.dataChanged.emit()

    def delete_company(self) -> None:
        cid = self.current_id()
        if cid is None:
            return
        company = self.ctx.db.get_company(cid)
        if ask_yes_no(self, "Supprimer l'entreprise",
                      f"Supprimer « {company['name']} » du suivi ?\n"
                      "Les documents PDF ne seront pas supprimés.", danger=True):
            self.ctx.db.delete_company(cid)
            self.refresh()
            self.dataChanged.emit()

    def _letter(self) -> None:
        cid = self.current_id()
        if cid is not None:
            self.letterRequested.emit(self.ctx.db.get_company(cid)["name"])

    def _email(self) -> None:
        cid = self.current_id()
        if cid is not None:
            self.emailRequested.emit(cid)
