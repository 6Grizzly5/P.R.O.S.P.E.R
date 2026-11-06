"""Documents Manager : PDF générés (liste, ouverture, suppression, regroupement par entreprise)."""
from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QAbstractItemView, QComboBox, QHBoxLayout, QHeaderView, QInputDialog,
                             QMessageBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from app.gui.components import EmptyState, make_button, page_header
from app.gui.context import AppContext
from app.gui.dialogs import ask_yes_no, open_path
from app.services.documents_service import DocumentInfo

log = logging.getLogger("prosper.gui.documents")
ALL, UNSORTED = "__all__", "__none__"


def _size(n: int) -> str:
    return f"{n / 1024:.0f} Ko" if n < 1024 * 1024 else f"{n / 1024 / 1024:.1f} Mo"


class DocumentsView(QWidget):
    letterRequested = pyqtSignal()
    dataChanged = pyqtSignal()

    def __init__(self, ctx: AppContext):
        super().__init__()
        self.setObjectName("Page")
        self.ctx = ctx
        self._docs: list[DocumentInfo] = []
        self._shown: list[tuple[DocumentInfo, str]] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 24)
        root.setSpacing(14)

        top = QHBoxLayout()
        top.addLayout(page_header("Documents", "Lettres PDF générées par P.R.O.S.P.E.R."), 1)
        gen = make_button("Générer une lettre", "Primary")
        gen.clicked.connect(self.letterRequested.emit)
        top.addWidget(gen)
        root.addLayout(top)

        filt = QHBoxLayout()
        self.company_filter = QComboBox()
        self.company_filter.currentIndexChanged.connect(self._render)
        filt.addWidget(self.company_filter)
        filt.addStretch(1)
        root.addLayout(filt)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Document", "Entreprise", "Créé le", "Taille"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setShowGrid(False)
        hdr = self.table.horizontalHeader()
        hdr.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.doubleClicked.connect(lambda _: self.open_selected())
        self.table.itemSelectionChanged.connect(self._buttons)
        root.addWidget(self.table, 1)
        self.empty = EmptyState("Aucun document PDF pour l'instant.\nGénérez une lettre pour commencer.")
        root.addWidget(self.empty)

        actions = QHBoxLayout()
        self.open_btn = make_button("Ouvrir")
        self.open_btn.clicked.connect(self.open_selected)
        self.assign_btn = make_button("Associer à une entreprise…")
        self.assign_btn.clicked.connect(self.assign)
        self.del_btn = make_button("Supprimer", "DangerButton")
        self.del_btn.clicked.connect(self.delete_selected)
        folder = make_button("Ouvrir le dossier")
        folder.clicked.connect(lambda: open_path(self.ctx.documents.docs_dir()))
        refresh = make_button("Actualiser")
        refresh.clicked.connect(self.refresh)
        for b in (self.open_btn, self.assign_btn, self.del_btn, folder, refresh):
            actions.addWidget(b)
        actions.addStretch(1)
        root.addLayout(actions)
        self.refresh()

    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        self.refresh()

    # ------------------------------------------------------------------ #
    def _company_name(self, doc: DocumentInfo, links: dict, names: dict) -> str:
        cid = links.get(str(doc.path))
        if cid in names:
            return names[cid]
        return doc.guessed_company

    def refresh(self) -> None:
        self._docs = self.ctx.documents.list_documents()
        current = self.company_filter.currentData()
        links = self.ctx.db.document_links()
        names = {c["id"]: c["name"] for c in self.ctx.db.list_companies()}
        groups = sorted({self._company_name(d, links, names) for d in self._docs} - {""},
                        key=str.casefold)
        self.company_filter.blockSignals(True)
        self.company_filter.clear()
        self.company_filter.addItem("Toutes les entreprises", ALL)
        for g in groups:
            self.company_filter.addItem(g, g)
        self.company_filter.addItem("Non classés", UNSORTED)
        idx = self.company_filter.findData(current) if current else 0
        self.company_filter.setCurrentIndex(max(idx, 0))
        self.company_filter.blockSignals(False)
        self._links, self._names = links, names
        self._render()

    def _render(self) -> None:
        wanted = self.company_filter.currentData()
        self._shown = []
        for d in self._docs:
            comp = self._company_name(d, self._links, self._names)
            if wanted == ALL or wanted is None or (wanted == UNSORTED and not comp) or wanted == comp:
                self._shown.append((d, comp))
        self.table.setRowCount(len(self._shown))
        for r, (d, comp) in enumerate(self._shown):
            for c, text in enumerate((d.name, comp or "—", d.created.strftime("%d/%m/%Y %H:%M"), _size(d.size))):
                self.table.setItem(r, c, QTableWidgetItem(text))
        self.table.setVisible(bool(self._shown))
        self.empty.setVisible(not self._shown)
        self.empty.setText("Aucun document pour ce filtre." if self._docs else
                           "Aucun document PDF pour l'instant.\nGénérez une lettre pour commencer.")
        self._buttons()

    def _selected(self) -> DocumentInfo | None:
        row = self.table.currentRow()
        return self._shown[row][0] if 0 <= row < len(self._shown) else None

    def _buttons(self) -> None:
        has = self._selected() is not None
        for b in (self.open_btn, self.assign_btn, self.del_btn):
            b.setEnabled(has)

    # ------------------------------------------------------------------ #
    def open_selected(self) -> None:
        doc = self._selected()
        if doc and not open_path(doc.path):
            QMessageBox.warning(self, "Ouverture", "Impossible d'ouvrir ce document avec le lecteur par défaut.")

    def assign(self) -> None:
        doc = self._selected()
        if doc is None:
            return
        companies = self.ctx.db.list_companies()
        if not companies:
            QMessageBox.information(self, "Associer", "Ajoutez d'abord une entreprise dans « Candidatures ».")
            return
        labels = ["(aucune — dissocier)"] + [c["name"] for c in companies]
        choice, ok = QInputDialog.getItem(self, "Associer à une entreprise", doc.name, labels, 0, False)
        if ok:
            idx = labels.index(choice)
            self.ctx.db.link_document(str(doc.path), None if idx == 0 else companies[idx - 1]["id"])
            self.refresh()

    def delete_selected(self) -> None:
        doc = self._selected()
        if doc is None:
            return
        if ask_yes_no(self, "Supprimer le document",
                      f"Supprimer définitivement « {doc.name} » ?", danger=True):
            try:
                self.ctx.documents.delete(doc.path)
                self.ctx.db.unlink_document(str(doc.path))
            except (OSError, ValueError) as exc:
                QMessageBox.warning(self, "Suppression", f"Suppression impossible : {exc}")
            self.refresh()
            self.dataChanged.emit()
