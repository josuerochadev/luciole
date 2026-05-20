# Page Articles & Digest In-App

Date: 2026-05-20
Status: Approved

## Contexte

Luciole collecte des articles via RSS, les enrichit par LLM et les stocke en PostgreSQL. Aujourd'hui, les articles ne sont accessibles que via le digest email ou le RAG conversationnel. L'utilisateur connecte n'a aucune vue directe sur les articles collectes, et le digest n'est consultable que par email.

## Objectifs

1. **Page Articles** : interface de consultation des articles avec filtres, tri et pagination.
2. **Digest in-app** : vue web du digest (vivant + historique archivé) directement dans l'application.

---

## 1. Page Articles

### 1.1 Endpoints

#### `GET /articles-page` (HTML)
- Protege par `get_current_user_page` (redirect `/login` si non connecte).
- Rend le template `articles.html`.

#### `GET /articles` (JSON)
- Protege par `get_current_user`.
- Parametres query string :
  - `categorie: str | None` — filtre exact sur la categorie
  - `date_min: str | None` — date ISO 8601 (inclusive)
  - `date_max: str | None` — date ISO 8601 (inclusive)
  - `pertinence_min: int = 5` — seuil minimum de pertinence
  - `tri: str = "pertinence"` — `"pertinence"` ou `"date"`
  - `offset: int = 0`
  - `limit: int = 20` (max 100)
- Reponse : `{ "articles": [...], "total": int, "has_more": bool }`
- Chaque article contient : `lien, titre, resume, categorie, pertinence, source, date_publication, date_ajout`.

### 1.2 Couche donnees

Nouvelle fonction dans `tools/database.py` :

```python
def lire_articles_filtres(
    categorie: str | None = None,
    date_min: str | None = None,
    date_max: str | None = None,
    pertinence_min: int = 5,
    tri: str = "pertinence",
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[dict], int]:
    """
    Retourne (articles, total_count) depuis PostgreSQL.
    Filtre : archive = 0, pertinence >= pertinence_min.
    Tri : ORDER BY pertinence DESC ou date_publication DESC.
    """
```

Nouvelle fonction pour les categories disponibles :

```python
def lire_categories() -> list[str]:
    """SELECT DISTINCT categorie FROM articles WHERE archive = 0 ORDER BY categorie"""
```

### 1.3 UI — `templates/articles.html`

**Barre de filtres** (haut de page) :
- Dropdown categorie (peuple dynamiquement via `/articles?categories_only=true` ou endpoint dedie)
- Deux inputs `type="date"` pour date min/max
- Dropdown pertinence min (5 a 10)
- Dropdown tri (Pertinence / Date)
- Bouton "Appliquer"

**Liste d'articles** :
- Chaque article est une carte avec :
  - Titre (lien cliquable vers l'article original, `target="_blank"`, `rel="noopener"`)
  - Badge categorie (couleurs reprises de `_COULEURS_CAT` dans `tools/email.py`)
  - Score pertinence en etoiles (meme logique `_etoiles()`)
  - Source + date de publication
  - Resume tronque (~200 chars)
- Compteur au-dessus : "42 articles"

**Bouton "Charger plus"** :
- En bas de la liste
- Incremente `offset += limit`, appelle `/articles`, append les resultats
- Masque quand `has_more === false`

**Style** : design system Luciole existant (CSS vars `--luciole-*`), meme patterns que dashboard.html.

---

## 2. Digest In-App

### 2.1 Migration historique JSON vers PostgreSQL

Nouvelle table :

```sql
CREATE TABLE IF NOT EXISTS digest_history (
    id            SERIAL PRIMARY KEY,
    sent_at       TEXT NOT NULL,
    recipients    TEXT[] NOT NULL DEFAULT '{}',
    nb_articles   INTEGER NOT NULL DEFAULT 0,
    html_content  TEXT NOT NULL DEFAULT ''
);
```

- `enregistrer_envoi()` dans `tools/database.py` : ecrire en PG au lieu du fichier JSON.
- Sauvegarder le `html_content` au moment de l'envoi pour pouvoir le re-servir.
- `charger_json(HISTORIQUE_FILE)` : remplacer par lecture PG partout.
- Supprimer la dependance au fichier `data/historique_envois.json`.

### 2.2 Endpoints

#### `GET /digest-page` (HTML) — existant, enrichi
- Toujours protege par auth.
- Rend le template `digest.html` modifie avec deux onglets.

#### `GET /digest/live` (JSON) — nouveau
- Protege par `get_current_user`.
- Retourne les meilleurs articles actuels groupes par categorie.
- Reponse :
```json
{
  "categories": {
    "IA": [{ "titre": "...", "lien": "...", "pertinence": 9, ... }],
    "Cloud": [...]
  },
  "total": 18,
  "generated_at": "2026-05-20T08:00:00Z"
}
```
- Logique : reutilise `selectionner_articles()` puis regroupe par categorie.

#### `GET /digest/history` — existant, modifie
- Lit depuis PG au lieu du JSON.
- Reponse : `{ "historique": [{ "id": 1, "sent_at": "...", "recipients": [...], "nb_articles": 12 }] }`

#### `GET /digest/archive/{id}` (HTML) — nouveau
- Protege par `get_current_user`.
- Retourne le `html_content` stocke en PG pour ce digest.
- 404 si l'id n'existe pas.

### 2.3 UI — `templates/digest.html` (refonte)

**Deux onglets WAI-ARIA tabs** (meme pattern que `login.html`) :

**Onglet 1 — "Digest du jour"** (actif par defaut)
- KPIs en haut : nb articles, nb categories, date de generation
- Articles groupes par categorie dans des sections pliables (accordeon) :
  - Header section : badge couleur + nom categorie + nombre d'articles
  - Contenu : liste de cartes article (titre, etoiles, source, date, resume)
  - Sections ouvertes par defaut, pliables au clic
- Charge via `GET /digest/live` au montage

**Onglet 2 — "Historique & envoi"**
- Contenu actuel preserve : champ API key, boutons preview/envoyer, status
- Tableau historique enrichi : colonne "Voir" avec lien qui charge le HTML archive dans une iframe (meme pattern que le preview actuel)

### 2.4 Pas de regression

- L'envoi SMTP reste identique (logique dans `tools/email.py` inchangee).
- Le endpoint `GET /digest` (HTML protege par API key) reste fonctionnel.
- Le endpoint `POST /digest/send` reste identique.

---

## 3. Navigation

Ajouter les liens dans la navbar (`base.html`) :
- "Articles" → `/articles-page`
- Le lien "Digest" existant pointe deja vers `/digest-page`

---

## 4. Fichiers impactes

| Fichier | Action |
|---------|--------|
| `api.py` | Ajouter endpoints `/articles-page`, `/articles`, `/digest/live`, `/digest/archive/{id}`. Modifier `/digest/history`, `/digest/stats`. |
| `tools/database.py` | Ajouter `lire_articles_filtres()`, `lire_categories()`. Creer table `digest_history`. Migrer `enregistrer_envoi()` vers PG. |
| `templates/articles.html` | Nouveau template. |
| `templates/digest.html` | Refonte avec onglets + digest vivant. |
| `templates/base.html` | Ajouter lien "Articles" dans la navbar. |
| `tools/email.py` | Modifier `envoyer_rapport()` pour sauvegarder le HTML en PG. Adapter `selectionner_articles()` pour exposition groupee. |
| `config.py` | Supprimer `HISTORIQUE_FILE` une fois la migration PG terminee (ou garder comme fallback temporaire). |

## 5. Hors scope

- Filtrage par source
- Tri par categorie
- Tags/favoris/a lire plus tard
- Preferences utilisateur
- Personnalisation du digest par user
- Resume executif LLM des tendances
