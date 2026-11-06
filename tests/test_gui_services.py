"""Tests des services de la GUI (sans Qt, sans réseau). Lancer : python -m unittest discover -s tests -v"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.assistant_service import AssistantService, Plan  # noqa: E402
from app.services.career_db import CareerDB, is_valid_email  # noqa: E402
from app.services.documents_service import DocumentsService  # noqa: E402
from app.services.email_service import (EmailData, EmailError, EmailNotConfigured,  # noqa: E402
                                        EmailService, build_mime, split_addresses, validate)
from app.services.letters_service import LettersService  # noqa: E402
from app.services.logging_setup import mask_secrets  # noqa: E402
from app.services.settings_service import SettingsService  # noqa: E402


class CareerDBTests(unittest.TestCase):
    def setUp(self):
        self.db = CareerDB(":memory:")

    def test_company_crud_and_search(self):
        cid = self.db.add_company(name="Airtel", sector="Télécom", hr_email="rh@airtel.mg")
        self.db.add_company(name="Orange", status="sent")
        self.assertEqual(self.db.count_companies(), 2)
        self.assertEqual([c["name"] for c in self.db.list_companies(search="tel")], ["Airtel"])
        self.assertEqual([c["name"] for c in self.db.list_companies(status="sent")], ["Orange"])
        self.db.update_company(cid, status="interview", target="Stage 6 mois")
        self.assertEqual(self.db.get_company(cid)["status"], "interview")
        self.assertEqual(self.db.counts_by_status()["interview"], 1)
        self.db.delete_company(cid)
        self.assertIsNone(self.db.get_company(cid))

    def test_validation(self):
        with self.assertRaises(ValueError):
            self.db.add_company(name="  ")
        with self.assertRaises(ValueError):
            self.db.add_company(name="X", status="inconnu")

    def test_drafts_and_sent_flag(self):
        did = self.db.save_draft({"to_addr": "a@b.co", "subject": "S", "body_html": "<p>x</p>",
                                  "attachments": ["/tmp/cv.pdf"]})
        d = self.db.get_draft(did)
        self.assertEqual(d["attachments"], ["/tmp/cv.pdf"])
        self.assertEqual((self.db.count_drafts(), self.db.count_sent()), (1, 0))
        self.db.save_draft({"to_addr": "c@d.co", "subject": "S2"}, did)
        self.assertEqual(self.db.get_draft(did)["to_addr"], "c@d.co")
        self.db.mark_draft_sent(did)
        self.assertEqual((self.db.count_drafts(), self.db.count_sent()), (0, 1))

    def test_doc_links_survive_company_delete(self):
        cid = self.db.add_company(name="Yas")
        self.db.link_document("/x/a.pdf", cid)
        self.assertEqual(self.db.document_links(), {"/x/a.pdf": cid})
        self.db.delete_company(cid)
        self.assertEqual(self.db.document_links(), {})

    def test_email_regex(self):
        self.assertTrue(is_valid_email("rh@airtel.mg"))
        self.assertFalse(is_valid_email("pas-un-mail"))
        self.assertFalse(is_valid_email("a@b"))


class EmailTests(unittest.TestCase):
    def test_split_and_validate(self):
        self.assertEqual(split_addresses("a@b.co; c@d.co,\n e@f.co"), ["a@b.co", "c@d.co", "e@f.co"])
        errors, warnings = validate(EmailData(to=["bad"], subject="", body_text=""))
        self.assertTrue(any("invalide" in e for e in errors))
        self.assertTrue(warnings)
        errors, _ = validate(EmailData(to=[]))
        self.assertIn("Aucun destinataire.", errors)

    def test_missing_attachment_blocks(self):
        errors, _ = validate(EmailData(to=["a@b.co"], attachments=["/nope/missing.pdf"]))
        self.assertTrue(any("introuvable" in e for e in errors))

    def test_build_mime_with_attachment(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "cv.pdf"
            pdf.write_bytes(b"%PDF-1.4 test")
            msg = EmailData(to=["a@b.co"], cc=["c@d.co"], bcc=["e@f.co"], subject="Demande de stage",
                            body_text="Bonjour", body_html="<p>Bonjour</p>", attachments=[str(pdf)])
            mime = build_mime(msg)
            self.assertEqual(mime["To"], "a@b.co")
            self.assertEqual(mime["Bcc"], "e@f.co")
            names = [p.get_filename() for p in mime.iter_attachments()]
            self.assertEqual(names, ["cv.pdf"])
            self.assertIn("text/html", [p.get_content_type() for p in mime.walk()])

    def test_never_fakes_success_when_not_configured(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = EmailService(SettingsService(Path(tmp) / "s.json"))
            ready, note = service.readiness()
            self.assertFalse(ready)
            with self.assertRaises(EmailNotConfigured):
                service.send(EmailData(to=["a@b.co"], subject="x", body_text="y"))

    def test_invalid_message_rejected_before_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = EmailService(SettingsService(Path(tmp) / "s.json"))
            service.provider = mock.Mock()
            with self.assertRaises(EmailError):
                service.send(EmailData(to=["pas-valide"]))
            service.provider.send.assert_not_called()


class SettingsTests(unittest.TestCase):
    def test_roundtrip_and_unknown_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            s = SettingsService(path)
            s.update({"theme": "light", "cv_path": "/x/cv.pdf"})
            self.assertEqual(SettingsService(path).get("theme"), "light")
            with self.assertRaises(KeyError):
                s.set("api_key", "secret")
            self.assertNotIn("api_key", json.loads(path.read_text()))

    def test_secret_masking(self):
        fake = "AIza" + "x" * 35
        self.assertNotIn(fake, mask_secrets(f"erreur avec {fake} dans l'url"))
        self.assertNotIn("abc123", mask_secrets("https://x/y?key=abc123&z=1"))

    def test_api_key_status_is_masked(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = SettingsService(Path(tmp) / "s.json")
            with mock.patch.dict("os.environ", {"GEMINI_API_KEY": "AIzaSECRETVALUE1234"}):
                ok, masked = s.api_key_status()
            self.assertTrue(ok)
            self.assertTrue(masked.endswith("1234"))
            self.assertNotIn("SECRET", masked)


class DocumentsTests(unittest.TestCase):
    def test_list_guess_and_safe_delete(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = SettingsService(Path(tmp) / "s.json")
            docs_dir = Path(tmp) / "docs"
            s.set("documents_dir", str(docs_dir))
            svc = DocumentsService(s)
            svc.docs_dir()  # crée le dossier
            (docs_dir / "Lettre_stage_Accès_Banque_20261026.pdf").write_bytes(b"%PDF")
            (docs_dir / "notes.txt").write_text("x")
            listed = svc.list_documents()
            self.assertEqual([d.guessed_company for d in listed], ["Accès Banque"])
            svc.delete(listed[0].path)
            self.assertEqual(svc.count(), 0)
            outside = Path(tmp) / "autre.pdf"
            outside.write_bytes(b"%PDF")
            with self.assertRaises(ValueError):
                svc.delete(outside)
            self.assertTrue(outside.exists())


class AssistantTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        s = SettingsService(Path(self.tmp.name) / "s.json")
        self.assistant = AssistantService(LettersService(DocumentsService(s)))
        self.hist = mock.patch("app.services.assistant_service.add_history")
        self.hist.start()

    def tearDown(self):
        self.hist.stop()
        self.tmp.cleanup()

    def test_letter_detected_without_ai(self):
        plan = self.assistant.plan("Prépare une lettre de stage pour Airtel")
        self.assertEqual(plan.kind, "letter")
        self.assertIn("Airtel", plan.company)

    def test_action_flow_reuses_backend(self):
        fake_intent = {"success": True, "type": "action", "action": "time", "argument": ""}
        with mock.patch.dict(sys.modules, {
                "app.ai.intent": mock.Mock(understand=lambda m: fake_intent),
                "app.ai.response": mock.Mock(generate_response=lambda m, r: "Il est bien l'heure.")}):
            plan = self.assistant.plan("quelle heure ?")
            self.assertEqual((plan.kind, plan.action), ("action", "time"))
            self.assertEqual(self.assistant.finish(plan), "Il est bien l'heure.")

    def test_delete_requires_confirmation_and_unknown_action_fails_like_cli(self):
        self.assertTrue(Plan("action", action="delete").needs_confirmation)
        self.assertFalse(Plan("action", action="list").needs_confirmation)
        out = self.assistant.finish(Plan("action", message="x", action="inexistante", argument=""))
        self.assertIn("inconnue", out)

    def test_ai_failure_falls_back_to_local_result(self):
        broken = mock.Mock()
        broken.generate_response.side_effect = RuntimeError("réseau coupé")
        with mock.patch.dict(sys.modules, {"app.ai.response": broken}):
            out = self.assistant.finish(Plan("action", message="heure", action="time", argument=""))
        self.assertTrue(out)  # le résultat de l'action reste affiché

    def test_missing_key_gives_friendly_error(self):
        boom = mock.Mock()
        boom.understand.side_effect = RuntimeError("GEMINI_API_KEY manquante")
        with mock.patch.dict(sys.modules, {"app.ai.intent": boom}):
            plan = self.assistant.plan("bonjour")
        self.assertEqual(plan.kind, "error")
        self.assertIn("Paramètres", plan.error)


if __name__ == "__main__":
    unittest.main()
