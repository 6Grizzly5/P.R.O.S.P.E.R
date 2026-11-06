# -*- coding: utf-8 -*-
"""Générateur local de lettres de demande de stage pour P.R.O.S.P.E.R.

Cette fonctionnalité fonctionne sans Gemini ni connexion Internet.
Dépendance : reportlab
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from app.core.config import BASE_DIR, DATA_DIR

CANDIDATURES_DIR = BASE_DIR / "Candidatures"
USAGE_FILE = DATA_DIR / "letter_template_usage.json"

MONTHS_FR = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
]

CANDIDATE = {
    "name": "RAZANAKA Prosper Andriniaina Félix",
    "city": "Ivato Aéroport",
    "location": "Ivato Aéroport, Madagascar",
    "email": "prosperfelix11@gmail.com",
    "phones": "034 81 703 77 / 032 26 421 99",
    "school": "ESMIA Innovation",
    "level": "Troisième année de Licence, parcours Génie Logiciel",
    "availability": "à partir du 21 Décembre 2026, pour une durée de six mois",
    "availability_start": "21 Décembre 2026",
}

CLOSING = "Je vous prie d'agréer, Madame, Monsieur, mes salutations distinguées."

# "style" : "band" = bandeau de couleur en haut de page
#           "sidebar" = liseré vertical de couleur sur le bord gauche
TEMPLATES = {
    "directe": {
        "label": "Directe et concise",
        "accent": "#1F4E79",
        "style": "band",
        "subject": "Demande de stage en informatique",
        "paragraphs": [
            "Actuellement étudiant en troisième année de Licence en Génie Logiciel à "
            "{school}, je vous adresse ma candidature pour un stage au sein de {company}. "
            "Arrivé à une étape importante de ma formation, je souhaite désormais confronter "
            "mes connaissances théoriques à la réalité d'un environnement professionnel.",
            "Au cours de mon cursus, j'ai appris à analyser un besoin, à concevoir une "
            "application, à structurer une base de données et à développer des solutions "
            "fonctionnelles. J'ai également pris l'habitude d'utiliser des outils de gestion "
            "de versions comme Git, indispensables pour travailler de manière organisée et "
            "collaborative sur un même projet.",
            "Je souhaite aujourd'hui intégrer une équipe informatique afin de découvrir ses "
            "méthodes de travail, ses outils et ses exigences au quotidien. Sérieux, motivé "
            "et rigoureux, je suis prêt à m'investir pleinement dans les missions qui me "
            "seront confiées, qu'il s'agisse de développement, de maintenance, de tests ou "
            "de documentation.",
            "Je suis conscient qu'un stage est avant tout une période d'apprentissage. "
            "J'accorde donc une grande importance à l'écoute, à la ponctualité et au respect "
            "des consignes. Je m'efforcerai de gagner rapidement en autonomie tout en "
            "sachant demander conseil lorsque cela est nécessaire.",
            "Je suis disponible {availability}. Je me tiens à votre entière disposition pour "
            "un entretien, afin de vous présenter plus en détail mon parcours et ma "
            "motivation, et je vous remercie de l'attention que vous porterez à ma demande.",
            CLOSING,
        ],
    },
    "classique": {
        "label": "Classique et formelle",
        "accent": "#172033",
        "style": "band",
        "subject": "Candidature pour un stage en informatique",
        "paragraphs": [
            "Étudiant en troisième année de Licence, parcours Génie Logiciel, à "
            "{school}, je souhaite effectuer un stage professionnel au sein de {company}. "
            "Cette démarche s'inscrit dans la continuité de ma formation et répond à mon "
            "désir de mettre en pratique, dans un cadre réel, les connaissances acquises "
            "au cours de mon cursus.",
            "Ma formation m'a permis d'acquérir des bases solides en conception et "
            "développement d'applications, en modélisation, en bases de données ainsi qu'en "
            "outils de gestion de versions. Elle m'a également appris à analyser un problème, "
            "à proposer une solution adaptée et à présenter clairement mon travail.",
            "Intégrer votre structure représenterait pour moi une occasion précieuse de "
            "mieux comprendre les exigences du métier, de progresser auprès de professionnels "
            "expérimentés et de participer concrètement aux travaux de votre équipe. Je suis "
            "convaincu que cette expérience enrichira durablement mon parcours.",
            "Rigoureux, ponctuel et attentif, je mesure l'importance de la confiance qui "
            "accompagne chaque mission confiée à un stagiaire. Je m'engage à faire preuve de "
            "sérieux, de discrétion et d'esprit d'équipe, et à tirer le meilleur parti des "
            "conseils qui me seront donnés.",
            "Je suis ouvert à toute mission en lien avec le développement logiciel, "
            "l'analyse des besoins, la gestion des données ou le support applicatif, et "
            "je m'adapterai volontiers aux priorités de votre service.",
            "Disponible {availability}, je serais heureux de pouvoir vous présenter plus "
            "en détail ma motivation lors d'un entretien. Je vous prie d'agréer, Madame, "
            "Monsieur, l'expression de ma considération distinguée.",
        ],
    },
    "technique": {
        "label": "Compétences techniques",
        "accent": "#0F766E",
        "style": "sidebar",
        "subject": "Demande de stage en développement logiciel",
        "paragraphs": [
            "Dans le cadre de ma troisième année de Licence en Génie Logiciel à {school}, "
            "je recherche un stage au sein de {company} afin de renforcer mon expérience "
            "pratique et de me familiariser avec les méthodes de travail d'une équipe de "
            "développement.",
            "Au cours de ma formation et de mes projets personnels, j'ai travaillé avec des "
            "technologies telles que JavaScript, React, Python, Flask, SQL et Git. J'ai "
            "également abordé la modélisation avec Merise et UML, ce qui m'a appris à "
            "concevoir une application avant de la coder, en pensant à sa structure et à "
            "ses données.",
            "Ces expériences m'ont appris à structurer mon travail, à tester mes "
            "réalisations, à corriger mes erreurs et à progresser face aux difficultés "
            "techniques. J'ai développé le réflexe de chercher, de comprendre puis de "
            "documenter les solutions, ce qui me permet d'apprendre vite de nouveaux outils.",
            "Je souhaite mettre ces compétences au service de vos activités tout en "
            "développant de meilleures pratiques de conception, de programmation et de "
            "collaboration en équipe. Je suis particulièrement intéressé par la création "
            "d'applications web, la gestion des bases de données et l'amélioration de "
            "solutions existantes.",
            "Je suis disponible {availability} et reste à votre disposition pour un "
            "entretien, au cours duquel je pourrai vous présenter mes réalisations ainsi que "
            "ma motivation.",
            "Veuillez agréer, Madame, Monsieur, mes salutations respectueuses.",
        ],
    },
    "apprentissage": {
        "label": "Motivation et apprentissage",
        "accent": "#6D28D9",
        "style": "sidebar",
        "subject": "Candidature pour un stage de formation",
        "paragraphs": [
            "Étudiant en troisième année de Licence en Génie Logiciel à {school}, je souhaite "
            "rejoindre {company} dans le cadre d'un stage qui me permettra de confronter ma "
            "formation aux réalités du monde professionnel et de gagner en maturité dans "
            "mon futur métier.",
            "Au-delà des connaissances techniques, je souhaite apprendre à travailler selon "
            "les méthodes et les priorités d'une équipe, à communiquer efficacement avec "
            "mes collègues et à prendre progressivement en charge des tâches concrètes. "
            "Je sais que ces qualités ne s'acquièrent qu'au contact du terrain.",
            "Curieux, appliqué et disposé à apprendre, je suis prêt à m'investir dans les "
            "missions correspondant à mon niveau et à approfondir les compétences "
            "nécessaires aux besoins de votre structure. Je considère chaque conseil et "
            "chaque correction comme une occasion de progresser.",
            "Mon parcours m'a donné le goût de la logique, de la résolution de problèmes et "
            "du travail bien fait. J'aime comprendre le fonctionnement des choses avant "
            "d'agir, et je n'hésite pas à poser des questions lorsqu'un point me paraît "
            "flou, afin d'éviter les erreurs et de gagner du temps.",
            "Intégrer {company} serait pour moi une chance de contribuer, à ma mesure, à "
            "vos projets tout en construisant les bases solides de ma future carrière "
            "dans l'informatique.",
            "Ma disponibilité commence le {availability_start}, pour six mois. Je vous "
            "remercie pour l'examen de ma candidature et vous prie d'agréer, Madame, "
            "Monsieur, l'expression de mes salutations distinguées.",
        ],
    },
    "projet": {
        "label": "Parcours et projets",
        "accent": "#B45309",
        "style": "band",
        "subject": "Demande de stage en informatique - Génie Logiciel",
        "paragraphs": [
            "Actuellement en troisième année de Licence en Génie Logiciel à {school}, je "
            "souhaite réaliser mon stage au sein de {company} pour approfondir mon "
            "expérience du développement d'applications et de la conduite de projets "
            "informatiques.",
            "Mes travaux académiques et personnels m'ont amené à concevoir des applications, "
            "à manipuler des bases de données et à utiliser différents outils de "
            "développement. Chaque projet, de l'analyse du besoin jusqu'à la livraison, m'a "
            "demandé de planifier mon travail, de respecter des délais et de livrer un "
            "résultat fonctionnel.",
            "Ces projets m'ont permis de mieux comprendre l'importance de l'organisation du "
            "code, de la résolution de problèmes et de la collaboration. J'ai appris que "
            "la qualité d'une application ne dépend pas seulement de ses fonctionnalités, "
            "mais aussi de sa clarté, de sa maintenabilité et de l'expérience de ses "
            "utilisateurs.",
            "Je souhaiterais contribuer aux activités de votre équipe, découvrir vos "
            "pratiques et faire progresser mes compétences au contact de situations "
            "réelles. Je suis prêt à prendre part à toutes les étapes d'un projet, de la "
            "conception aux tests, avec sérieux et enthousiasme.",
            "Je suis disponible {availability}. Je serais ravi de vous présenter mes "
            "réalisations lors d'un entretien afin d'illustrer concrètement ma motivation.",
            "Je reste à votre disposition pour tout renseignement complémentaire et vous "
            "prie d'agréer, Madame, Monsieur, l'expression de ma considération distinguée.",
        ],
    },
    "personnalisee": {
        "label": "Détaillée et personnalisée",
        "accent": "#9F1239",
        "style": "sidebar",
        "subject": "Candidature spontanée pour un stage en informatique",
        "paragraphs": [
            "Je vous soumets ma candidature pour un stage au sein de {company}, dans le "
            "domaine informatique, et plus particulièrement pour des missions liées au "
            "développement logiciel ou aux applications métiers.",
            "Étudiant en troisième année de Licence, parcours Génie Logiciel, à {school}, "
            "je souhaite poursuivre ma formation par une expérience qui me confronte aux "
            "besoins concrets d'une organisation. Mon parcours m'a permis d'aborder la "
            "programmation, les bases de données, la conception d'applications et les "
            "outils de collaboration utilisés dans les projets.",
            "Je suis conscient qu'un stage implique autant de rigueur et d'écoute que de "
            "compétences techniques. Je suis donc prêt à apprendre vos méthodes, à respecter "
            "les consignes de votre équipe et à contribuer sérieusement aux tâches qui me "
            "seront confiées, même lorsqu'elles semblent modestes au départ.",
            "Ce que je peux vous apporter, c'est mon envie d'apprendre, ma capacité à "
            "travailler de façon organisée et ma volonté de mener à bien chaque mission. "
            "J'aime relever les défis techniques et je prends le temps de bien comprendre "
            "un problème avant d'y apporter une solution.",
            "En retour, je recherche un cadre qui me permette de progresser auprès de "
            "personnes expérimentées, d'observer de bonnes pratiques et de comprendre les "
            "enjeux réels d'un service informatique.",
            "Je recherche un stage de six mois, à partir du {availability_start}. Je serais "
            "heureux de pouvoir vous rencontrer afin de vous présenter mon parcours et les "
            "objectifs de ce stage.",
            "Je vous remercie de l'attention accordée à ma demande et vous prie d'agréer, "
            "Madame, Monsieur, l'expression de mes salutations distinguées.",
        ],
    },
}

# --------------------------------------------------------------------------- #
#  Détection et extraction
# --------------------------------------------------------------------------- #
def is_letter_request(command: str) -> bool:
    """Détecte localement une demande de génération de lettre."""
    text = command.lower().replace("’", "'")
    markers = (
        "lettre", "demande de stage", "candidature", "lettre de stage",
        "génère une demande", "genere une demande", "prépare ma lettre",
        "prepare ma lettre", "faire une lettre",
    )
    return any(marker in text for marker in markers)


def _extract_company(command: str) -> str:
    """Extrait le nom probable de l'entreprise après 'pour' ou 'chez'."""
    text = command.strip()
    match = re.search(r"\b(?:pour|chez)\s+(.+)$", text, flags=re.IGNORECASE)
    if not match:
        return ""
    company = match.group(1).strip(" .,!?:;\"'")
    company = re.sub(
        r"^(?:l['’]entreprise|la société|la societe|l['’]organisation)\s+",
        "", company, flags=re.IGNORECASE,
    )
    return company.strip()


def _safe_filename(value: str) -> str:
    value = re.sub(r"[^\w.-]+", "_", value.strip(), flags=re.UNICODE)
    value = value.strip("._")
    return value[:70] or "Entreprise"


def _format_date_fr(day: date) -> str:
    return f"{day.day} {MONTHS_FR[day.month - 1]} {day.year}"


# --------------------------------------------------------------------------- #
#  Choix du modèle
# --------------------------------------------------------------------------- #
def _choose_template(company: str) -> tuple[str, str]:
    """Choisit un modèle parmi les moins utilisés pour varier les candidatures."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        usage = json.loads(USAGE_FILE.read_text(encoding="utf-8"))
        if not isinstance(usage, dict):
            usage = {}
    except (OSError, json.JSONDecodeError):
        usage = {}

    counts = {}
    for key in TEMPLATES:
        try:
            counts[key] = int(usage.get(key, 0))
        except (TypeError, ValueError):
            counts[key] = 0

    minimum = min(counts.values())
    candidates = [key for key in TEMPLATES if counts[key] == minimum]
    # Répartition stable mais variée entre les entreprises ayant le même compteur.
    seed = hashlib.sha256(company.casefold().encode("utf-8")).digest()
    selected = candidates[int.from_bytes(seed[:4], "big") % len(candidates)]
    usage[selected] = counts[selected] + 1
    USAGE_FILE.write_text(
        json.dumps(usage, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return selected, TEMPLATES[selected]["label"]


def _ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    answer = input(f"{prompt}{suffix} : ").strip()
    return answer or default


# --------------------------------------------------------------------------- #
#  Génération du PDF
# --------------------------------------------------------------------------- #
def _tint(hex_color: str, factor: float) -> colors.Color:
    """Éclaircit une couleur (factor proche de 1 = presque blanc)."""
    base = colors.HexColor(hex_color)
    return colors.Color(
        base.red + (1 - base.red) * factor,
        base.green + (1 - base.green) * factor,
        base.blue + (1 - base.blue) * factor,
    )


def _fill_template(text: str, company: str) -> str:
    """Remplace les variables sans utiliser str.format (sûr avec { et })."""
    replacements = {
        "{school}": CANDIDATE["school"],
        "{company}": company,
        "{availability}": CANDIDATE["availability"],
        "{availability_start}": CANDIDATE["availability_start"],
    }
    for key, value in replacements.items():
        text = text.replace(key, value)
    return text


def _build_styles(accent: colors.Color) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()["Normal"]
    dark = colors.HexColor("#1B2333")
    grey = colors.HexColor("#5B6475")

    def style(name: str, **kwargs) -> ParagraphStyle:
        return ParagraphStyle(name=name, parent=base, **kwargs)

    return {
        "name": style("CandName", fontName="Helvetica-Bold", fontSize=15,
                      leading=18, textColor=accent, spaceAfter=2),
        "role": style("CandRole", fontName="Helvetica", fontSize=9,
                      leading=12, textColor=grey, spaceAfter=7),
        "contact": style("CandContact", fontName="Helvetica", fontSize=9,
                         leading=13, textColor=dark),
        "recipient": style("Recipient", fontName="Helvetica", fontSize=10,
                           leading=14, textColor=dark, alignment=TA_LEFT),
        "subject": style("Subject", fontName="Helvetica", fontSize=10.5,
                         leading=15, textColor=dark),
        "salutation": style("Salutation", fontName="Helvetica", fontSize=10.5,
                            leading=15, textColor=dark, spaceBefore=4, spaceAfter=9),
        "body": style("Body", fontName="Helvetica", fontSize=10.3, leading=15.5,
                      textColor=dark, alignment=TA_JUSTIFY, spaceAfter=9),
        "date": style("DateBottom", fontName="Helvetica", fontSize=10, leading=14,
                      textColor=dark, alignment=TA_RIGHT, spaceBefore=6),
        "signature": style("Signature", fontName="Helvetica-Bold", fontSize=10.5,
                           leading=14, textColor=dark, alignment=TA_RIGHT),
        "signature_sub": style("SignatureSub", fontName="Helvetica", fontSize=8.8,
                               leading=12, textColor=grey, alignment=TA_RIGHT),
    }


def _make_pdf(company: str, company_address: str, recipient: str,
              service: str, template_key: str) -> Path:
    CANDIDATURES_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today()
    template = TEMPLATES[template_key]
    accent_hex = template["accent"]
    accent = colors.HexColor(accent_hex)
    page_style = template["style"]

    paragraphs = [_fill_template(p, company) for p in template["paragraphs"]]

    stamp = today.strftime("%Y%m%d")
    base_name = f"Lettre_stage_{_safe_filename(company)}_{stamp}"
    output_path = CANDIDATURES_DIR / f"{base_name}.pdf"
    # Ne jamais écraser une lettre déjà créée le même jour.
    counter = 2
    while output_path.exists():
        output_path = CANDIDATURES_DIR / f"{base_name}_{counter}.pdf"
        counter += 1

    left_margin = 2.3 * cm if page_style == "sidebar" else 2.15 * cm
    right_margin = 2.15 * cm
    top_margin = 2.0 * cm if page_style == "band" else 1.7 * cm
    doc = SimpleDocTemplate(
        str(output_path), pagesize=A4,
        rightMargin=right_margin, leftMargin=left_margin,
        topMargin=top_margin, bottomMargin=1.9 * cm,
        title=f"Demande de stage - {company}",
        author=CANDIDATE["name"],
    )
    usable_width = A4[0] - left_margin - right_margin
    styles = _build_styles(accent)

    story = []

    # --- En-tête : mes infos à gauche, destinataire à droite ----------------
    sender_block = [
        Paragraph(escape(CANDIDATE["name"]), styles["name"]),
        Paragraph(escape(CANDIDATE["level"]), styles["role"]),
        Paragraph(
            "<br/>".join([
                escape(CANDIDATE["location"]),
                escape(CANDIDATE["email"]),
                escape(CANDIDATE["phones"]),
            ]),
            styles["contact"],
        ),
    ]

    recipient_lines = [f"<b>{escape(company)}</b>"]
    if company_address:
        recipient_lines.append(escape(company_address))
    recipient_lines.append(f"À l'attention de {escape(recipient)}")
    if service:
        recipient_lines.append(escape(service))
    recipient_block = [Paragraph("<br/>".join(recipient_lines), styles["recipient"])]

    right_col_width = usable_width * 0.43
    header = Table(
        [[sender_block, recipient_block]],
        colWidths=[usable_width - right_col_width, right_col_width],
    )
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), 10),
        ("RIGHTPADDING", (1, 0), (1, 0), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        # Petit trait d'accent à gauche du bloc destinataire
        ("LINEBEFORE", (1, 0), (1, 0), 1.2, accent),
        ("LEFTPADDING", (1, 0), (1, 0), 12),
    ]))
    story.append(header)
    story.append(Spacer(1, 26))

    # --- Objet (avant « Madame, Monsieur, ») --------------------------------
    subject_text = f"<b>Objet :</b> {escape(template['subject'])}"
    subject_box = Table(
        [[Paragraph(subject_text, styles["subject"])]],
        colWidths=[usable_width],
    )
    subject_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _tint(accent_hex, 0.90)),
        ("LINEBEFORE", (0, 0), (0, 0), 3, accent),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(subject_box)
    story.append(Spacer(1, 16))

    # --- Corps de la lettre --------------------------------------------------
    story.append(Paragraph("Madame, Monsieur,", styles["salutation"]))
    for paragraph in paragraphs:
        story.append(Paragraph(escape(paragraph), styles["body"]))

    # --- Date et signature en bas -------------------------------------------
    date_line = f"Fait à {escape(CANDIDATE['city'])}, le {_format_date_fr(today)}"
    story.append(Spacer(1, 6))
    story.append(KeepTogether([
        Paragraph(date_line, styles["date"]),
        Spacer(1, 30),
        Paragraph(escape(CANDIDATE["name"]), styles["signature"]),
        Paragraph(
            escape(f"Étudiant en Génie Logiciel - {CANDIDATE['school']}"),
            styles["signature_sub"],
        ),
    ]))

    # --- Décor de page -------------------------------------------------------
    def decorate(canvas, document):
        width, height = A4
        canvas.saveState()
        canvas.setFillColor(accent)
        if page_style == "band":
            canvas.rect(0, height - 0.55 * cm, width, 0.55 * cm, stroke=0, fill=1)
            canvas.setFillColor(_tint(accent_hex, 0.55))
            canvas.rect(0, height - 0.72 * cm, width, 0.17 * cm, stroke=0, fill=1)
        else:
            canvas.rect(0, 0, 0.55 * cm, height, stroke=0, fill=1)
            canvas.setFillColor(_tint(accent_hex, 0.55))
            canvas.rect(0.55 * cm, 0, 0.17 * cm, height, stroke=0, fill=1)

        # Pied de page discret
        footer_left = left_margin
        canvas.setStrokeColor(colors.HexColor("#D8DDE5"))
        canvas.setLineWidth(0.5)
        canvas.line(footer_left, 1.35 * cm, width - right_margin, 1.35 * cm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#667085"))
        canvas.drawString(
            footer_left, 0.9 * cm,
            f"{CANDIDATE['name']}  |  {CANDIDATE['email']}  |  {CANDIDATE['phones']}",
        )
        if document.page > 1:
            canvas.drawRightString(width - right_margin, 0.9 * cm, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    return output_path


def _open_file(path: Path) -> None:
    """Ouvre le PDF avec l'application par défaut (Windows, macOS, Linux)."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            os.system(f'open "{path}"')
        else:
            os.system(f'xdg-open "{path}"')
    except Exception as exc:
        print(f"P.R.O.S.P.E.R. > Impossible d'ouvrir le fichier automatiquement : {exc}")


# --------------------------------------------------------------------------- #
#  Assistant interactif
# --------------------------------------------------------------------------- #
def run_letter_wizard(command: str = "") -> None:
    """Collecte les informations utiles et génère le PDF localement."""
    print("\nP.R.O.S.P.E.R. > Générateur local de lettres de stage")
    company = _extract_company(command)
    company = _ask("Nom de l'entreprise", company)
    if not company:
        print("P.R.O.S.P.E.R. > Le nom de l'entreprise est obligatoire.")
        return

    company_address = _ask("Adresse de l'entreprise (facultatif)")
    recipient = _ask("Destinataire", "Service des Ressources Humaines")
    service = _ask("Service visé (facultatif)", "Service informatique")
    print("\nP.R.O.S.P.E.R. > Je sélectionne le modèle le moins utilisé pour varier tes lettres...")
    template_key, template_label = _choose_template(company)
    try:
        path = _make_pdf(company, company_address, recipient, service, template_key)
    except Exception as exc:
        print(f"P.R.O.S.P.E.R. > Impossible de générer le PDF : {exc}")
        return

    print(f"\nP.R.O.S.P.E.R. > Lettre créée : {template_label}")
    print(f"P.R.O.S.P.E.R. > Fichier : {path}")
    answer = input("P.R.O.S.P.E.R. > Ouvrir le PDF maintenant ? [O/n] : ").strip().lower()
    if answer in ("", "o", "oui", "y", "yes"):
        _open_file(path)
    print("P.R.O.S.P.E.R. > Tu peux maintenant l'imprimer.")