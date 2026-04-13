"""
Module d'envoi email — rapport quotidien de veille technologique.

Fonctionnalités :
  - Génération d'un digest HTML des meilleurs articles du jour
  - Regroupement par catégorie
  - Envoi SMTP avec TLS (Gmail, Outlook, SMTP d'entreprise)
  - Mode dry_run : génère le HTML sans envoyer (pour tests)
  - Enregistrement de l'historique d'envoi
"""
import logging
import os
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import (
    EMAIL_EXPEDITEUR, EMAIL_DESTINATAIRES,
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
    MAX_ARTICLES_PAR_RAPPORT, ARTICLES_FILE,
)
from tools.database import charger_json, enregistrer_envoi

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sélection des articles à envoyer
# ---------------------------------------------------------------------------

def selectionner_articles(nb_max: int = MAX_ARTICLES_PAR_RAPPORT) -> list[dict]:
    """
    Retourne les meilleurs articles triés par pertinence décroissante.
    Exclut les articles hors-sujet (catégorie 'Hors-sujet').
    """
    articles = charger_json(ARTICLES_FILE)
    pertinents = [
        a for a in articles
        if a.get("categorie", "Autre").lower() != "hors-sujet"
        and int(a.get("pertinence", 0)) >= 5
    ]
    pertinents.sort(key=lambda a: int(a.get("pertinence", 0)), reverse=True)
    return pertinents[:nb_max]


# ---------------------------------------------------------------------------
# Génération HTML
# ---------------------------------------------------------------------------

# Couleur par catégorie
_COULEURS_CAT = {
    "IA":             "#6366f1",
    "Cloud":          "#0ea5e9",
    "Cybersécurité":  "#ef4444",
    "DevOps":         "#f59e0b",
    "Données":        "#10b981",
    "Infrastructure": "#8b5cf6",
}
_COULEUR_DEFAUT = "#64748b"


def _couleur(categorie: str) -> str:
    for cle, couleur in _COULEURS_CAT.items():
        if cle.lower() in categorie.lower():
            return couleur
    return _COULEUR_DEFAUT


def _badge(categorie: str) -> str:
    c = _couleur(categorie)
    return (
        f'<span style="background:{c};color:#fff;padding:2px 8px;'
        f'border-radius:12px;font-size:11px;font-weight:600;">'
        f'{categorie}</span>'
    )


def _etoiles(pertinence: int) -> str:
    n = min(max(int(pertinence), 0), 10)
    pleines = round(n / 2)
    return "★" * pleines + "☆" * (5 - pleines)


def generer_html(articles: list[dict], date_rapport: str | None = None) -> str:
    """
    Génère le corps HTML du rapport à partir d'une liste d'articles.

    Args:
        articles:     Articles à inclure, triés par pertinence.
        date_rapport: Date affichée dans le titre (ISO ou string libre).

    Returns:
        Chaîne HTML complète.
    """
    if date_rapport is None:
        date_rapport = datetime.now(timezone.utc).strftime("%d/%m/%Y")

    # Regrouper par catégorie
    categories: dict[str, list[dict]] = {}
    for article in articles:
        cat = article.get("categorie", "Autre")
        categories.setdefault(cat, []).append(article)

    # Construire les sections par catégorie
    sections_html = ""
    for cat, arts in categories.items():
        couleur = _couleur(cat)
        articles_html = ""
        for a in arts:
            titre = a.get("titre", "Sans titre")
            lien = a.get("lien", "#")
            resume = a.get("resume", a.get("resume_brut", ""))[:300]
            pertinence = int(a.get("pertinence", 0))
            source = a.get("source", "")
            date_pub = a.get("date_publication", "")[:10]

            articles_html += f"""
            <div style="border-left:3px solid {couleur};padding:10px 14px;margin-bottom:12px;background:#f8fafc;border-radius:0 6px 6px 0;">
              <div style="margin-bottom:4px;">
                <a href="{lien}" style="color:#1e293b;font-weight:600;font-size:15px;text-decoration:none;">{titre}</a>
              </div>
              <p style="color:#475569;font-size:13px;margin:4px 0 6px;">{resume}{'…' if len(resume) >= 300 else ''}</p>
              <div style="font-size:12px;color:#94a3b8;">
                <span style="color:{couleur};">{_etoiles(pertinence)}</span> &nbsp;
                {source} {'· ' + date_pub if date_pub else ''}
              </div>
            </div>"""

        sections_html += f"""
        <div style="margin-bottom:28px;">
          <h2 style="color:{couleur};font-size:16px;margin:0 0 10px;padding-bottom:6px;border-bottom:2px solid {couleur};">
            {_badge(cat)} &nbsp; {cat} — {len(arts)} article{'s' if len(arts) > 1 else ''}
          </h2>
          {articles_html}
        </div>"""

    nb_total = len(articles)
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f1f5f9;margin:0;padding:20px;">
  <div style="max-width:680px;margin:0 auto;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08);">

    <!-- En-tête -->
    <div style="background:linear-gradient(135deg,#1e293b,#334155);padding:28px 32px;color:#fff;">
      <div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#94a3b8;margin-bottom:6px;">
        Veille Technologique
      </div>
      <h1 style="margin:0;font-size:22px;font-weight:700;">Rapport du {date_rapport}</h1>
      <p style="margin:6px 0 0;color:#cbd5e1;font-size:14px;">
        {nb_total} article{'s' if nb_total > 1 else ''} sélectionné{'s' if nb_total > 1 else ''} par l'agent IA
      </p>
    </div>

    <!-- Corps -->
    <div style="padding:28px 32px;">
      {sections_html}
    </div>

    <!-- Pied de page -->
    <div style="background:#f8fafc;padding:16px 32px;border-top:1px solid #e2e8f0;font-size:12px;color:#94a3b8;text-align:center;">
      Rapport généré automatiquement · Rétention 90 jours (RGPD) ·
      <a href="#" style="color:#6366f1;">Se désabonner</a>
    </div>

  </div>
</body>
</html>"""
    return html


def generer_texte(articles: list[dict], date_rapport: str | None = None) -> str:
    """Version texte brut du rapport (fallback pour clients sans HTML)."""
    if date_rapport is None:
        date_rapport = datetime.now(timezone.utc).strftime("%d/%m/%Y")

    lignes = [
        f"RAPPORT DE VEILLE TECHNOLOGIQUE — {date_rapport}",
        "=" * 60,
        "",
    ]
    for a in articles:
        lignes += [
            f"[{a.get('categorie','?')}] {a.get('titre','')}",
            f"  Pertinence : {a.get('pertinence','?')}/10",
            f"  {a.get('resume', a.get('resume_brut',''))[:200]}",
            f"  Lien : {a.get('lien','')}",
            "",
        ]
    return "\n".join(lignes)


# ---------------------------------------------------------------------------
# Envoi SMTP
# ---------------------------------------------------------------------------

def envoyer_rapport(
    destinataires: list[str] | None = None,
    nb_max: int = MAX_ARTICLES_PAR_RAPPORT,
    dry_run: bool = False,
) -> dict:
    """
    Sélectionne les meilleurs articles et envoie le rapport par email.

    Args:
        destinataires: Liste d'adresses email. Utilise EMAIL_DESTINATAIRES si None.
        nb_max:        Nombre max d'articles à inclure.
        dry_run:       Si True, génère le HTML sans envoyer (pour tests).

    Returns:
        Dict avec les clés : ok (bool), nb_articles (int), message (str).
    """
    if destinataires is None:
        destinataires = [d.strip() for d in EMAIL_DESTINATAIRES if d.strip()]

    if not destinataires:
        return {"ok": False, "nb_articles": 0, "message": "Aucun destinataire configuré."}

    articles = selectionner_articles(nb_max)
    if not articles:
        return {"ok": False, "nb_articles": 0, "message": "Aucun article pertinent à envoyer."}

    date_rapport = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    sujet = f"[Veille Tech] Rapport du {date_rapport} — {len(articles)} articles"

    html = generer_html(articles, date_rapport)
    texte = generer_texte(articles, date_rapport)

    if dry_run:
        logger.info(f"[Email] dry_run — {len(articles)} articles, destinataires: {destinataires}")
        return {
            "ok": True,
            "nb_articles": len(articles),
            "message": f"dry_run OK — {len(articles)} articles prêts pour {destinataires}",
            "html": html,
            "texte": texte,
            "sujet": sujet,
        }

    # Construire le message MIME
    msg = MIMEMultipart("alternative")
    msg["Subject"] = sujet
    msg["From"] = EMAIL_EXPEDITEUR
    msg["To"] = ", ".join(destinataires)
    msg.attach(MIMEText(texte, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    # Envoi SMTP
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as serveur:
            serveur.ehlo()
            serveur.starttls()
            serveur.ehlo()
            if SMTP_USER and SMTP_PASSWORD:
                serveur.login(SMTP_USER, SMTP_PASSWORD)
            serveur.sendmail(EMAIL_EXPEDITEUR, destinataires, msg.as_bytes())

        enregistrer_envoi(destinataires, len(articles))
        logger.info(f"[Email] Rapport envoyé à {destinataires} — {len(articles)} articles.")
        return {
            "ok": True,
            "nb_articles": len(articles),
            "message": f"Rapport envoyé à {len(destinataires)} destinataire(s).",
        }

    except smtplib.SMTPAuthenticationError:
        msg_err = "Authentification SMTP échouée. Vérifiez SMTP_USER et SMTP_PASSWORD."
        logger.error(f"[Email] {msg_err}")
        return {"ok": False, "nb_articles": 0, "message": msg_err}

    except (smtplib.SMTPException, OSError) as e:
        msg_err = f"Erreur SMTP : {e}"
        logger.error(f"[Email] {msg_err}")
        return {"ok": False, "nb_articles": 0, "message": msg_err}
