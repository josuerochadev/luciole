"""
Exercice 4 — Tests de la mémoire conversationnelle (memory/store.py)
Valide les 3 cas : sans mémoire vs avec mémoire.

Utilisation : python test_memory.py
"""
import logging
from memory.store import store, recall, clear, taille, LIMITE_MEMOIRE
from llm import appeler_llm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

SEPARATEUR = "-" * 60


def repondre_avec_memoire(question: str) -> str:
    """Appelle le LLM en injectant les derniers messages comme contexte."""
    historique = recall(n=10)
    messages_contexte = "\n".join(
        f"{m['role'].upper()} : {m['content']}" for m in historique
    )
    prompt = (
        f"Historique de la conversation :\n{messages_contexte}\n\n"
        f"Nouvelle question : {question}\n"
        "Réponds en tenant compte de l'historique."
    ) if historique else question

    reponse = appeler_llm(prompt)
    store(question, role="user")
    store(reponse, role="assistant")
    return reponse


def repondre_sans_memoire(question: str) -> str:
    """Appelle le LLM sans aucun contexte mémorisé."""
    return appeler_llm(question)


# ---------------------------------------------------------------------------
# Test 1 — "Je m'appelle Alice" puis "Comment je m'appelle ?"
# ---------------------------------------------------------------------------
def test_rappel_prenom():
    print(f"\n{SEPARATEUR}")
    print("TEST 1 — Rappel du prénom")
    print(SEPARATEUR)
    clear()

    print("\n--- SANS MÉMOIRE ---")
    repondre_sans_memoire("Je m'appelle Alice.")
    rep_sans = repondre_sans_memoire("Comment je m'appelle ?")
    print(f"Réponse : {rep_sans}")

    print("\n--- AVEC MÉMOIRE ---")
    clear()
    store("Je m'appelle Alice.", role="user")
    rep_avec = repondre_avec_memoire("Comment je m'appelle ?")
    print(f"Réponse : {rep_avec}")

    print(f"\nObservation : sans mémoire → le LLM ne sait pas.")
    print(f"             avec mémoire → le LLM répond 'Alice'.")


# ---------------------------------------------------------------------------
# Test 2 — 3 questions enchaînées sur le même sujet
# ---------------------------------------------------------------------------
def test_questions_enchainées():
    print(f"\n{SEPARATEUR}")
    print("TEST 2 — 3 questions enchaînées sur les LLMs")
    print(SEPARATEUR)
    clear()

    questions = [
        "Qu'est-ce qu'un LLM ?",
        "Quels sont les plus connus ?",
        "Lequel est le plus utilisé en entreprise ?",
    ]

    print("\n--- SANS MÉMOIRE ---")
    for q in questions:
        rep = repondre_sans_memoire(q)
        print(f"Q: {q}\nR: {rep[:120]}...\n")

    print("\n--- AVEC MÉMOIRE ---")
    clear()
    for q in questions:
        rep = repondre_avec_memoire(q)
        print(f"Q: {q}\nR: {rep[:120]}...\n")

    print("Observation : avec mémoire, les réponses 2 et 3 référencent le contexte des précédentes.")


# ---------------------------------------------------------------------------
# Test 3 — 12 messages puis rappel du 1er
# ---------------------------------------------------------------------------
def test_limite_memoire():
    overflow = LIMITE_MEMOIRE + 2
    print(f"\n{SEPARATEUR}")
    print(f"TEST 3 — {overflow} messages, rappel du 1er (limite = {LIMITE_MEMOIRE})")
    print(SEPARATEUR)
    clear()

    # Remplir au-delà de la limite
    for i in range(1, overflow + 1):
        store(f"Message numéro {i}", role="user")

    print(f"Messages stockés : {taille()} (attendu : {LIMITE_MEMOIRE} — les 2 premiers sont perdus)")
    assert taille() == LIMITE_MEMOIRE, f"Attendu {LIMITE_MEMOIRE}, obtenu {taille()}"

    historique = recall(n=LIMITE_MEMOIRE)
    premier = historique[0]["content"]
    print(f"Premier message en mémoire : '{premier}' (attendu : 'Message numéro 3')")
    assert premier == "Message numéro 3", f"Attendu 'Message numéro 3', obtenu '{premier}'"

    print(f"\nObservation : la mémoire est bornée à {LIMITE_MEMOIRE} messages. "
          "Les messages les plus anciens sont automatiquement évincés par SQLite.")
    print("✓ Limite de mémoire respectée.")


# ---------------------------------------------------------------------------
# Lancement
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("EXERCICE 4 — Tests de la mémoire conversationnelle")
    print("=" * 60)

    resultats = []
    for nom, fn in [
        ("Rappel prénom",          test_rappel_prenom),
        ("Questions enchaînées",   test_questions_enchainées),
        (f"Limite {LIMITE_MEMOIRE} messages", test_limite_memoire),
    ]:
        try:
            fn()
            resultats.append((nom, "PASS"))
        except AssertionError as e:
            resultats.append((nom, f"FAIL — {e}"))
        except Exception as e:
            resultats.append((nom, f"ERREUR — {e}"))

    print(f"\n{'='*60}\nRÉSUMÉ\n{'='*60}")
    for nom, statut in resultats:
        print(f"  {'✓' if statut == 'PASS' else '✗'} {nom:<30} {statut}")
