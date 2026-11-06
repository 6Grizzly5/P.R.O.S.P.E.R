"""Email Manager : composition, brouillons, aperçu, envoi avec confirmation humaine explicite."""
from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextCharFormat, QTextListFormat
from PyQt6.QtWidgets import (QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                             QListWidget, QListWidgetItem, QMenu, QMessageBox, QTextEdit,
                             QToolButton, QVBoxLayout, QWidget)

from app.gui.components import Card, make_button, page_header
from app.gui.context import AppContext
from app.gui.dialogs import EmailPreviewDialog, ask_yes_no, open_path
from app.gui.workers import run_async
from app.services.email_service import EmailData, EmailError, split_addresses, validate

log = logging.getLogger("prosper.gui.email")


class EmailView(QWidget):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.setObjectName("Page")
        self.ctx = ctx
        self.draft_id: int | None = None
        self.dirty = False
        self._loading = False
        self._sending = False

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 24)
        root.setSpacing(12)
        root.addLayout(page_header(
            "E-mails", "Préparer → Vérifier → Valider → Envoyer. Rien n'est jamais envoyé sans votre confirmation."))
        self.provider_line = QLabel()
        self.provider_line.setWordWrap(True)
        root.addWidget(self.provider_line)

        body = QHBoxLayout()
        body.setSpacing(14)
        root.addLayout(body, 1)

        # ---------- colonne brouillons ----------
        left = QVBoxLayout()
        head = QHBoxLayout()
        title = QLabel("Brouillons")
        title.setObjectName("SectionTitle")
        head.addWidget(title, 1)
        new = make_button("Nouveau", "Flat")
        new.clicked.connect(lambda: self.new_draft())
        head.addWidget(new)
        left.addLayout(head)
        self.drafts = QListWidget()
        self.drafts.setFixedWidth(250)
        self.drafts.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.drafts.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.drafts.setWordWrap(False)
        self.drafts.itemClicked.connect(self._on_draft_clicked)
        left.addWidget(self.drafts, 1)
        self.del_draft = make_button("Supprimer le brouillon", "DangerButton")
        self.del_draft.clicked.connect(self.delete_draft)
        left.addWidget(self.del_draft)
        body.addLayout(left)

        # ---------- compositeur ----------
        card = Card()
        comp = QVBoxLayout(card)
        comp.setContentsMargins(20, 16, 20, 16)
        comp.setSpacing(10)
        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.company = QComboBox()
        self.company.currentIndexChanged.connect(self._on_company_changed)
        self.to = QLineEdit()
        self.to.setPlaceholderText("destinataire@entreprise.com (plusieurs : séparés par des virgules)")
        self.cc = QLineEdit()
        self.bcc = QLineEdit()
        self.subject = QLineEdit()
        self.subject.setPlaceholderText("Objet du message")
        form.addRow("Entreprise", self.company)
        form.addRow("À", self.to)
        self.cc_label, self.bcc_label = QLabel("Cc"), QLabel("Cci")
        form.addRow(self.cc_label, self.cc)
        form.addRow(self.bcc_label, self.bcc)
        form.addRow("Objet", self.subject)
        comp.addLayout(form)
        self.cc_toggle = make_button("Afficher Cc / Cci", "Flat")
        self.cc_toggle.clicked.connect(lambda: self._show_cc(not self.cc.isVisible()))
        comp.addWidget(self.cc_toggle, 0, Qt.AlignmentFlag.AlignLeft)
        self._show_cc(False)

        tools = QHBoxLayout()
        tools.setSpacing(4)
        self.btn_b = self._tool("B", self._toggle_bold, bold=True)
        self.btn_i = self._tool("I", self._toggle_italic, italic=True)
        self.btn_u = self._tool("U", self._toggle_underline, underline=True)
        self.btn_l = self._tool("• Liste", self._toggle_list)
        for b in (self.btn_b, self.btn_i, self.btn_u, self.btn_l):
            tools.addWidget(b)
        tools.addStretch(1)
        comp.addLayout(tools)

        self.editor = QTextEdit()
        self.editor.setAcceptRichText(True)
        self.editor.setPlaceholderText("Rédigez votre message…")
        self.editor.setMinimumHeight(190)
        comp.addWidget(self.editor, 1)

        att_head = QHBoxLayout()
        att_title = QLabel("Pièces jointes")
        att_title.setObjectName("SectionTitle")
        att_head.addWidget(att_title)
        att_head.addStretch(1)
        for text, fn in (("+ Fichier…", self._add_files), ("+ CV", lambda: self._add_default("cv_path", "CV")),
                         ("+ Lettre de l'école", lambda: self._add_default("school_letter_path", "Lettre de l'école"))):
            b = make_button(text, "Flat")
            b.clicked.connect(fn)
            att_head.addWidget(b)
        self.gen_btn = make_button("+ Lettre générée", "Flat")
        self.gen_btn.clicked.connect(self._add_generated)
        att_head.addWidget(self.gen_btn)
        comp.addLayout(att_head)

        self.attachments = QListWidget()
        self.attachments.setMaximumHeight(96)
        self.attachments.itemDoubleClicked.connect(lambda i: open_path(i.data(Qt.ItemDataRole.UserRole)))
        comp.addWidget(self.attachments)
        att_actions = QHBoxLayout()
        prev = make_button("Aperçu de la pièce jointe")
        prev.clicked.connect(self._preview_attachment)
        rem = make_button("Retirer")
        rem.clicked.connect(self._remove_attachment)
        att_actions.addWidget(prev)
        att_actions.addWidget(rem)
        att_actions.addStretch(1)
        comp.addLayout(att_actions)

        actions = QHBoxLayout()
        self.save_btn = make_button("Enregistrer le brouillon")
        self.save_btn.clicked.connect(lambda: self.save_draft(notify=True))
        self.preview_btn = make_button("Aperçu de l'e-mail")
        self.preview_btn.clicked.connect(self.preview)
        self.send_btn = make_button("Vérifier et envoyer…", "Primary")
        self.send_btn.clicked.connect(self.send_flow)
        actions.addStretch(1)
        actions.addWidget(self.save_btn)
        actions.addWidget(self.preview_btn)
        actions.addWidget(self.send_btn)
        comp.addLayout(actions)
        body.addWidget(card, 1)

        for w in (self.to, self.cc, self.bcc, self.subject):
            w.textEdited.connect(self._mark_dirty)
        self.editor.textChanged.connect(self._mark_dirty)

        self.reload_companies()
        self.reload_drafts()
        self.new_draft()

    # ------------------------------------------------------------------ #
    # Outils d'édition riche
    # ------------------------------------------------------------------ #
    def _tool(self, text: str, slot, bold=False, italic=False, underline=False) -> QToolButton:
        b = QToolButton()
        b.setText(text)
        f = b.font()
        f.setBold(bold)
        f.setItalic(italic)
        f.setUnderline(underline)
        b.setFont(f)
        b.clicked.connect(slot)
        return b

    def _merge(self, fmt: QTextCharFormat) -> None:
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            cursor.select(cursor.SelectionType.WordUnderCursor)
        cursor.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)
        self.editor.setFocus()

    def _toggle_bold(self) -> None:
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Weight.Normal if self.editor.fontWeight() > 50 else QFont.Weight.Bold)
        self._merge(fmt)

    def _toggle_italic(self) -> None:
        fmt = QTextCharFormat()
        fmt.setFontItalic(not self.editor.fontItalic())
        self._merge(fmt)

    def _toggle_underline(self) -> None:
        fmt = QTextCharFormat()
        fmt.setFontUnderline(not self.editor.fontUnderline())
        self._merge(fmt)

    def _toggle_list(self) -> None:
        cursor = self.editor.textCursor()
        if cursor.currentList():
            block_fmt = cursor.blockFormat()
            block_fmt.setIndent(0)
            cursor.currentList().remove(cursor.block())
            cursor.setBlockFormat(block_fmt)
        else:
            cursor.createList(QTextListFormat.Style.ListDisc)
        self.editor.setFocus()

    def _show_cc(self, visible: bool) -> None:
        for w in (self.cc, self.bcc, self.cc_label, self.bcc_label):
            w.setVisible(visible)
        self.cc_toggle.setText("Masquer Cc / Cci" if visible else "Afficher Cc / Cci")

    # ------------------------------------------------------------------ #
    # État
    # ------------------------------------------------------------------ #
    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        self.refresh_status()

    def refresh_status(self) -> None:
        ready, note = self.ctx.email.readiness()
        self.provider_line.setObjectName("Ok" if ready else "BannerWarn")
        self.provider_line.setText(("✓ " if ready else "⚠ Envoi non disponible : ") + note
                                   + ("" if ready else "  (la rédaction et les brouillons restent utilisables)"))
        self.provider_line.style().unpolish(self.provider_line)
        self.provider_line.style().polish(self.provider_line)

    def _mark_dirty(self, *_) -> None:
        if not self._loading:
            self.dirty = True

    def reload_companies(self) -> None:
        current = self.company.currentData()
        self.company.blockSignals(True)
        self.company.clear()
        self.company.addItem("— Aucune —", None)
        for c in self.ctx.db.list_companies():
            self.company.addItem(c["name"], c["id"])
        idx = self.company.findData(current)
        self.company.setCurrentIndex(max(idx, 0))
        self.company.blockSignals(False)

    def reload_drafts(self) -> None:
        self.drafts.clear()
        for d in self.ctx.db.list_drafts():
            mark = "✓ envoyé · " if d["sent_at"] else ""
            item = QListWidgetItem(f"{mark}{d['subject'] or '(sans objet)'}\n{d['to_addr'] or '—'}")
            item.setData(Qt.ItemDataRole.UserRole, d["id"])
            self.drafts.addItem(item)
            if d["id"] == self.draft_id:
                self.drafts.setCurrentItem(item)

    def _on_company_changed(self) -> None:
        cid = self.company.currentData()
        if cid and not self.to.text().strip():
            company = self.ctx.db.get_company(cid)
            if company and company["hr_email"]:
                self.to.setText(company["hr_email"])
        self._mark_dirty()

    # ------------------------------------------------------------------ #
    # Brouillons
    # ------------------------------------------------------------------ #
    def _confirm_discard(self) -> bool:
        if not self.dirty:
            return True
        box = QMessageBox(self)
        box.setWindowTitle("Modifications non enregistrées")
        box.setText("Enregistrer le brouillon en cours ?")
        save = box.addButton("Enregistrer", QMessageBox.ButtonRole.AcceptRole)
        drop = box.addButton("Ne pas enregistrer", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Annuler", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is save:
            self.save_draft()
            return True
        return box.clickedButton() is drop

    def new_draft(self, company_id: int | None = None, force: bool = False) -> None:
        if not force and not self._confirm_discard():
            return
        self._loading = True
        self.draft_id = None
        self.reload_companies()
        idx = self.company.findData(company_id) if company_id else 0
        self.company.setCurrentIndex(max(idx, 0))
        company = self.ctx.db.get_company(company_id) if company_id else None
        self.to.setText(company["hr_email"] if company else "")
        self.cc.clear()
        self.bcc.clear()
        self.subject.setText(f"Demande de stage – {company['name']}" if company else "")
        self.editor.clear()
        self.attachments.clear()
        self.drafts.clearSelection()
        self._loading = False
        self.dirty = False

    def compose_for_company(self, company_id: int) -> None:
        """Appelé depuis « Candidatures » : nouveau brouillon prérempli."""
        self.new_draft(company_id)

    def _on_draft_clicked(self, item: QListWidgetItem) -> None:
        draft_id = item.data(Qt.ItemDataRole.UserRole)
        if draft_id == self.draft_id:
            return
        if not self._confirm_discard():
            self.reload_drafts()
            return
        self.load_draft(draft_id)

    def load_draft(self, draft_id: int) -> None:
        d = self.ctx.db.get_draft(draft_id)
        if d is None:
            return
        self._loading = True
        self.draft_id = draft_id
        self.reload_companies()
        self.company.setCurrentIndex(max(self.company.findData(d["company_id"]), 0))
        self.to.setText(d["to_addr"])
        self.cc.setText(d["cc"])
        self.bcc.setText(d["bcc"])
        self._show_cc(bool(d["cc"] or d["bcc"]))
        self.subject.setText(d["subject"])
        self.editor.setHtml(d["body_html"])
        self.attachments.clear()
        for path in d["attachments"]:
            self._add_attachment(path)
        self._loading = False
        self.dirty = False

    def delete_draft(self) -> None:
        item = self.drafts.currentItem()
        if item is None:
            return
        if ask_yes_no(self, "Supprimer le brouillon", "Supprimer définitivement ce brouillon ?", danger=True):
            did = item.data(Qt.ItemDataRole.UserRole)
            self.ctx.db.delete_draft(did)
            if did == self.draft_id:
                self.new_draft(force=True)
            self.reload_drafts()

    def _attachment_paths(self) -> list[str]:
        return [self.attachments.item(i).data(Qt.ItemDataRole.UserRole)
                for i in range(self.attachments.count())]

    def save_draft(self, notify: bool = False) -> int:
        self.draft_id = self.ctx.db.save_draft({
            "company_id": self.company.currentData(), "to_addr": self.to.text(), "cc": self.cc.text(),
            "bcc": self.bcc.text(), "subject": self.subject.text(), "body_html": self.editor.toHtml(),
            "attachments": self._attachment_paths(),
        }, self.draft_id)
        self.dirty = False
        self.reload_drafts()
        if notify:
            QMessageBox.information(self, "Brouillon", "Brouillon enregistré.")
        return self.draft_id

    # ------------------------------------------------------------------ #
    # Pièces jointes
    # ------------------------------------------------------------------ #
    def _add_attachment(self, path: str) -> None:
        if path in self._attachment_paths():
            return
        p = Path(path)
        if not p.is_file():
            size = "introuvable"
        else:
            n = p.stat().st_size
            size = f"{n} o" if n < 1024 else f"{n / 1024:.0f} Ko" if n < 1024 ** 2 else f"{n / 1024 ** 2:.1f} Mo"
        item = QListWidgetItem(f"{p.name}   ({size})")
        item.setData(Qt.ItemDataRole.UserRole, str(p))
        item.setToolTip(str(p))
        self.attachments.addItem(item)

    def _add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Ajouter des pièces jointes")
        for path in paths:
            self._add_attachment(path)
        if paths:
            self._mark_dirty()

    def _add_default(self, key: str, label: str) -> None:
        path = (self.ctx.settings.get(key) or "").strip()
        if not path or not Path(path).is_file():
            QMessageBox.information(self, label, f"{label} : aucun fichier valide configuré.\n"
                                    "Définissez-le dans Paramètres › Documents.")
            return
        self._add_attachment(path)
        self._mark_dirty()

    def _add_generated(self) -> None:
        docs = self.ctx.documents.list_documents()
        if not docs:
            QMessageBox.information(self, "Lettre générée", "Aucun document PDF disponible.")
            return
        cid = self.company.currentData()
        name = (self.ctx.db.get_company(cid) or {}).get("name", "").casefold() if cid else ""
        docs.sort(key=lambda d: (name not in d.guessed_company.casefold() if name else False))
        menu = QMenu(self)
        for d in docs[:15]:
            menu.addAction(d.name, lambda p=str(d.path): (self._add_attachment(p), self._mark_dirty()))
        menu.exec(self.gen_btn.mapToGlobal(self.gen_btn.rect().bottomLeft()))

    def _remove_attachment(self) -> None:
        row = self.attachments.currentRow()
        if row >= 0:
            self.attachments.takeItem(row)
            self._mark_dirty()

    def _preview_attachment(self) -> None:
        item = self.attachments.currentItem()
        if item and not open_path(item.data(Qt.ItemDataRole.UserRole)):
            QMessageBox.warning(self, "Aperçu", "Impossible d'ouvrir ce fichier.")

    # ------------------------------------------------------------------ #
    # Aperçu et envoi
    # ------------------------------------------------------------------ #
    def collect(self) -> EmailData:
        return EmailData(
            to=split_addresses(self.to.text()), cc=split_addresses(self.cc.text()),
            bcc=split_addresses(self.bcc.text()), subject=self.subject.text().strip(),
            body_html=self.editor.toHtml(), body_text=self.editor.toPlainText(),
            attachments=self._attachment_paths())

    def _dialog(self, confirm_mode: bool) -> bool:
        msg = self.collect()
        errors, warnings = validate(msg)
        ready, note = self.ctx.email.readiness()
        dlg = EmailPreviewDialog(self, msg, confirm_mode=confirm_mode, errors=errors, warnings=warnings,
                                 provider_ready=ready, provider_note=note,
                                 provider_name=self.ctx.email.provider.name)
        return dlg.exec() == dlg.DialogCode.Accepted

    def preview(self) -> None:
        self._dialog(confirm_mode=False)

    def send_flow(self) -> None:
        if self._sending:
            return
        if self.draft_id:
            current = self.ctx.db.get_draft(self.draft_id)
            if current and current["sent_at"] and not ask_yes_no(
                    self, "Déjà envoyé", "Ce message a déjà été envoyé. Le renvoyer ?"):
                return
        if not self._dialog(confirm_mode=True):          # Vérifier + Valider (humain)
            return
        msg = self.collect()
        self.save_draft()
        self._sending = True
        self.send_btn.setEnabled(False)
        self.send_btn.setText("Envoi en cours…")
        run_async(self.ctx.email.send, self._sent_ok, self._sent_failed, msg)

    def _end_sending(self) -> None:
        self._sending = False
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Vérifier et envoyer…")

    def _sent_ok(self, message_id: str) -> None:
        self._end_sending()
        if self.draft_id:
            self.ctx.db.mark_draft_sent(self.draft_id)
        self.reload_drafts()
        QMessageBox.information(self, "E-mail envoyé", f"Le message a bien été envoyé.\nRéférence : {message_id}")
        cid = self.company.currentData()
        if cid and ask_yes_no(self, "Suivi", "Passer cette entreprise au statut « Envoyé » ?"):
            from datetime import date
            self.ctx.db.update_company(cid, status="sent", applied_date=date.today().isoformat())

    def _sent_failed(self, error: str) -> None:
        self._end_sending()
        QMessageBox.critical(self, "Envoi impossible", f"Le message n'a PAS été envoyé.\n\n{error}")
