"""Stockage SQLite des données *nouvelles* de la GUI : candidatures, brouillons d'e-mails,
liens document ↔ entreprise.

La mémoire (memory.json) et l'historique (history.json) du backend ne sont PAS dupliqués :
ils continuent d'être lus/écrits via app.memory.memory.
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from app.core.config import DATA_DIR

DB_FILE = DATA_DIR / "prosper.db"

STATUSES: dict[str, str] = {
    "to_contact": "À contacter",
    "preparing": "En préparation",
    "ready": "Prêt à envoyer",
    "sent": "Envoyé",
    "waiting": "En attente de réponse",
    "interview": "Entretien",
    "accepted": "Accepté",
    "rejected": "Refusé",
}

EMAIL_RE = re.compile(r"^[^@\s,;]+@[^@\s,;]+\.[^@\s,;]{2,}$")


def is_valid_email(address: str) -> bool:
    return bool(EMAIL_RE.match(address.strip()))


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    sector TEXT NOT NULL DEFAULT '',
    hr_email TEXT NOT NULL DEFAULT '',
    target TEXT NOT NULL DEFAULT '',
    applied_date TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'to_contact',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS email_drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL,
    to_addr TEXT NOT NULL DEFAULT '',
    cc TEXT NOT NULL DEFAULT '',
    bcc TEXT NOT NULL DEFAULT '',
    subject TEXT NOT NULL DEFAULT '',
    body_html TEXT NOT NULL DEFAULT '',
    attachments TEXT NOT NULL DEFAULT '[]',
    sent_at TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS doc_links (
    path TEXT PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL
);
"""

COMPANY_FIELDS = ("name", "sector", "hr_email", "target", "applied_date", "status", "notes")
DRAFT_FIELDS = ("company_id", "to_addr", "cc", "bcc", "subject", "body_html")


class CareerDB:
    def __init__(self, path: Path | str = DB_FILE):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # ------------------------------------------------------------------ #
    # Entreprises
    # ------------------------------------------------------------------ #
    def add_company(self, **values) -> int:
        name = (values.get("name") or "").strip()
        if not name:
            raise ValueError("Le nom de l'entreprise est obligatoire.")
        data = {f: (values.get(f) or "").strip() for f in COMPANY_FIELDS}
        if not data["status"]:
            data["status"] = "to_contact"
        if data["status"] not in STATUSES:
            raise ValueError(f"Statut inconnu : {data['status']}")
        now = _now()
        cur = self.conn.execute(
            "INSERT INTO companies (name, sector, hr_email, target, applied_date, status,"
            " notes, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (*[data[f] for f in COMPANY_FIELDS], now, now),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def update_company(self, company_id: int, **values) -> None:
        fields = {k: (v or "").strip() for k, v in values.items() if k in COMPANY_FIELDS}
        if "name" in fields and not fields["name"]:
            raise ValueError("Le nom de l'entreprise est obligatoire.")
        if "status" in fields and fields["status"] not in STATUSES:
            raise ValueError(f"Statut inconnu : {fields['status']}")
        if not fields:
            return
        sets = ", ".join(f"{k} = ?" for k in fields)
        self.conn.execute(
            f"UPDATE companies SET {sets}, updated_at = ? WHERE id = ?",
            (*fields.values(), _now(), company_id),
        )
        self.conn.commit()

    def delete_company(self, company_id: int) -> None:
        self.conn.execute("DELETE FROM companies WHERE id = ?", (company_id,))
        self.conn.commit()

    def get_company(self, company_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM companies WHERE id = ?", (company_id,)).fetchone()
        return dict(row) if row else None

    def list_companies(self, search: str = "", status: str = "") -> list[dict]:
        sql, params = "SELECT * FROM companies WHERE 1=1", []
        if status:
            sql += " AND status = ?"
            params.append(status)
        if search.strip():
            like = f"%{search.strip()}%"
            sql += " AND (name LIKE ? OR sector LIKE ? OR hr_email LIKE ? OR target LIKE ?)"
            params += [like] * 4
        sql += " ORDER BY name COLLATE NOCASE"
        return [dict(r) for r in self.conn.execute(sql, params)]

    def count_companies(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0])

    def counts_by_status(self) -> dict[str, int]:
        counts = {code: 0 for code in STATUSES}
        for row in self.conn.execute("SELECT status, COUNT(*) AS n FROM companies GROUP BY status"):
            counts[row["status"]] = row["n"]
        return counts

    # ------------------------------------------------------------------ #
    # Brouillons d'e-mails
    # ------------------------------------------------------------------ #
    def save_draft(self, draft: dict, draft_id: int | None = None) -> int:
        data = {f: draft.get(f) for f in DRAFT_FIELDS}
        data["company_id"] = data["company_id"] or None
        for f in DRAFT_FIELDS[1:]:
            data[f] = (data[f] or "").strip() if f != "body_html" else (data[f] or "")
        attachments = json.dumps(list(draft.get("attachments") or []), ensure_ascii=False)
        now = _now()
        if draft_id is None:
            cur = self.conn.execute(
                "INSERT INTO email_drafts (company_id, to_addr, cc, bcc, subject, body_html,"
                " attachments, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (*[data[f] for f in DRAFT_FIELDS], attachments, now, now),
            )
            self.conn.commit()
            return int(cur.lastrowid)
        self.conn.execute(
            "UPDATE email_drafts SET company_id=?, to_addr=?, cc=?, bcc=?, subject=?,"
            " body_html=?, attachments=?, updated_at=? WHERE id=?",
            (*[data[f] for f in DRAFT_FIELDS], attachments, now, draft_id),
        )
        self.conn.commit()
        return draft_id

    @staticmethod
    def _draft_row(row: sqlite3.Row) -> dict:
        d = dict(row)
        try:
            d["attachments"] = json.loads(d["attachments"])
        except json.JSONDecodeError:
            d["attachments"] = []
        return d

    def get_draft(self, draft_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM email_drafts WHERE id = ?", (draft_id,)).fetchone()
        return self._draft_row(row) if row else None

    def list_drafts(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM email_drafts ORDER BY updated_at DESC, id DESC")
        return [self._draft_row(r) for r in rows]

    def count_drafts(self) -> int:
        return int(self.conn.execute(
            "SELECT COUNT(*) FROM email_drafts WHERE sent_at = ''").fetchone()[0])

    def count_sent(self) -> int:
        return int(self.conn.execute(
            "SELECT COUNT(*) FROM email_drafts WHERE sent_at != ''").fetchone()[0])

    def mark_draft_sent(self, draft_id: int) -> None:
        """À n'appeler qu'après un envoi réellement confirmé par le fournisseur."""
        self.conn.execute(
            "UPDATE email_drafts SET sent_at = ?, updated_at = ? WHERE id = ?",
            (_now(), _now(), draft_id),
        )
        self.conn.commit()

    def delete_draft(self, draft_id: int) -> None:
        self.conn.execute("DELETE FROM email_drafts WHERE id = ?", (draft_id,))
        self.conn.commit()

    # ------------------------------------------------------------------ #
    # Documents ↔ entreprises
    # ------------------------------------------------------------------ #
    def link_document(self, path: str, company_id: int | None) -> None:
        if company_id is None:
            self.conn.execute("DELETE FROM doc_links WHERE path = ?", (str(path),))
        else:
            self.conn.execute(
                "INSERT INTO doc_links (path, company_id) VALUES (?, ?)"
                " ON CONFLICT(path) DO UPDATE SET company_id = excluded.company_id",
                (str(path), company_id),
            )
        self.conn.commit()

    def document_links(self) -> dict[str, int]:
        rows = self.conn.execute(
            "SELECT path, company_id FROM doc_links WHERE company_id IS NOT NULL")
        return {r["path"]: r["company_id"] for r in rows}

    def unlink_document(self, path: str) -> None:
        self.link_document(path, None)
