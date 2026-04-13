"""
Test du module email — génération HTML + dry_run (aucun email réel envoyé).
Utilisation : python test_email.py
"""
import os
import sys

from tools.email import selectionner_articles, generer_html, generer_texte, envoyer_rapport

print("=" * 65)
print("TEST EMAIL — rapport de veille technologique")
print("=" * 65)

# --- 1. Sélection des articles ---
articles = selectionner_articles(nb_max=10)
print(f"\n[1/4] Sélection articles  : {len(articles)} articles retenus")

if not articles:
    print("      ATTENTION : articles.json vide ou absent.")
    print("      Lancez d'abord : python pipeline.py  ou  python seed.py")
    sys.exit(1)

# Afficher le top 3
for i, a in enumerate(articles[:3], 1):
    cat   = a.get("categorie", "?")
    pert  = a.get("pertinence", "?")
    titre = a.get("titre", "?")[:55]
    print(f"       {i}. [{pert}/10] [{cat}] {titre}...")

# --- 2. Génération HTML ---
html = generer_html(articles)
nb_chars = len(html)
print(f"\n[2/4] Génération HTML     : {nb_chars} caractères")

# Vérifications basiques du HTML
assert "<!DOCTYPE html>" in html,        "HTML manquant : <!DOCTYPE>"
assert "Rapport du" in html,             "HTML manquant : titre du rapport"
assert articles[0].get("titre","") in html, "HTML : titre article absent"
print("       Structure HTML   : OK")
print("       Titre article    : OK")

# Sauvegarde locale pour inspection visuelle
html_path = os.path.join("data", "rapport_test.html")
os.makedirs("data", exist_ok=True)
with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)
print(f"       Fichier de prévisualisation : {html_path}")

# --- 3. Génération texte brut ---
texte = generer_texte(articles)
assert "RAPPORT DE VEILLE" in texte, "Texte brut : en-tête manquant"
assert articles[0].get("titre","") in texte, "Texte brut : titre absent"
print(f"\n[3/4] Génération texte    : {len(texte)} caractères — OK")

# --- 4. dry_run (aucun email envoyé) ---
resultat = envoyer_rapport(
    destinataires=["test@example.com"],
    nb_max=10,
    dry_run=True,
)
assert resultat["ok"] is True,           f"dry_run échoué : {resultat['message']}"
assert resultat["nb_articles"] > 0,      "dry_run : aucun article"
assert "html" in resultat,               "dry_run : HTML absent dans le résultat"
assert "sujet" in resultat,              "dry_run : sujet absent"
print(f"\n[4/4] dry_run             : OK")
print(f"       Sujet             : {resultat['sujet']}")
print(f"       Articles prêts    : {resultat['nb_articles']}")

print(f"\n{'='*65}")
print("Tous les tests PASSENT — module email opérationnel.")
print(f"{'='*65}")
print(f"\nPour envoyer un vrai email, configurez dans .env :")
print("  SMTP_HOST=smtp.gmail.com")
print("  SMTP_PORT=587")
print("  SMTP_USER=votre@gmail.com")
print("  SMTP_PASSWORD=votre_mot_de_passe_application")
print("  EMAIL_EXPEDITEUR=votre@gmail.com")
print("  EMAIL_DESTINATAIRES=destinataire@example.com")
print("\nPuis exécutez : python -c \"from tools.email import envoyer_rapport; print(envoyer_rapport())\"")
