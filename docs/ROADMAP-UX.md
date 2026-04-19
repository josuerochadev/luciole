# Luciole — Roadmap UX/UI

> Prompts et contexte pour chaque fonctionnalite a implementer.
> Chaque section est autonome : copier le prompt dans une nouvelle conversation Claude Code.

---

## Phase 0 — Renommage Pulse → Luciole

### Contexte
Le design system s'appelle encore "Pulse" dans les fichiers techniques (CSS, JS, classes, variables) alors que le produit s'appelle "Luciole". Il faut unifier le naming avant d'ajouter des fonctionnalites.

### Etat des lieux
- **Fichiers a renommer** :
  - `static/pulse.css` → `static/luciole.css`
  - `static/pulse-chat.js` → `static/luciole-chat.js`
  - `static/pulse-favicon.svg` → supprimer (doublon de `luciole-favicon.svg`)
  - `static/pulse-wordmark.svg` → supprimer (doublon de `luciole-wordmark.svg`)
- **Classes CSS** : toutes les classes `pulse-*` → `luciole-*` (~200+ occurrences dans `pulse.css`)
- **Variables CSS** : toutes les `--pulse-*` → `--luciole-*`
- **References dans templates** : `base.html`, `index.html`, `about.html`, `dashboard.html`, `digest.html`
- **References dans JS** : `pulse-chat.js` utilise des classes `pulse-*`

### Prompt
```
Dans le projet /Users/josuexavierrocha/Projets/ia/fil-rouge/, renomme tout le design system de "Pulse" vers "Luciole" :

1. Renomme les fichiers :
   - static/pulse.css → static/luciole.css
   - static/pulse-chat.js → static/luciole-chat.js
   - Supprime static/pulse-favicon.svg et static/pulse-wordmark.svg (doublons des fichiers luciole-*)

2. Dans luciole.css (ex pulse.css) :
   - Remplace toutes les variables CSS --pulse-* par --luciole-*
   - Remplace toutes les classes .pulse-* par .luciole-*
   - Met a jour le commentaire d'en-tete

3. Dans luciole-chat.js (ex pulse-chat.js) :
   - Remplace toutes les references aux classes pulse-* par luciole-*
   - Met a jour le commentaire d'en-tete

4. Dans tous les templates HTML (base.html, index.html, about.html, dashboard.html, digest.html) :
   - Met a jour les liens vers les fichiers CSS/JS (pulse.css → luciole.css, etc.)
   - Remplace toutes les classes pulse-* par luciole-*
   - Remplace toutes les variables CSS inline --pulse-* par --luciole-*

5. Verifie qu'il ne reste aucune reference a "pulse" (sauf dans git history).

Ne change PAS le contenu textuel visible par l'utilisateur, seulement les noms techniques.
```

---

## Phase 1 — Historique des conversations

### Contexte
Actuellement, l'historique de chat est stocke dans le DOM cote client et dans une deque en memoire cote serveur (`memory/store.py`). Tout est perdu au refresh ou au redemarrage. L'utilisateur n'a aucun moyen de retrouver une conversation passee.

### Modele de donnees
```sql
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,        -- UUID
    title TEXT,                 -- Auto-genere par LLM au 1er message
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
    id TEXT PRIMARY KEY,        -- UUID
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,         -- 'user' ou 'assistant'
    content TEXT NOT NULL,
    tokens_used INTEGER,
    latency_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);
```

### Fichiers concernes
- `api.py` — nouveaux endpoints : `GET /conversations`, `GET /conversations/{id}`, `DELETE /conversations/{id}`, modifier `POST /ask` pour accepter un `conversation_id`
- `memory/store.py` — adapter pour lire/ecrire en SQLite au lieu de la deque
- `templates/index.html` — ajouter sidebar avec liste des conversations
- `static/luciole.css` — styles sidebar
- `static/luciole-chat.js` — logique sidebar, chargement conversation, nouvelle conversation
- Nouveau fichier : `database.py` — init SQLite, fonctions CRUD

### Prompt
```
Dans le projet /Users/josuexavierrocha/Projets/ia/fil-rouge/, implemente un historique de conversations persistant :

1. Cree database.py :
   - Init SQLite (fichier data/luciole.db)
   - Tables : conversations (id, title, created_at, updated_at) et messages (id, conversation_id, role, content, tokens_used, latency_ms, created_at)
   - Fonctions CRUD : create_conversation, list_conversations, get_conversation_messages, add_message, delete_conversation, update_conversation_title

2. Modifie api.py :
   - POST /ask : accepte un champ optionnel conversation_id. Si absent, cree une nouvelle conversation. Sauvegarde question et reponse en DB. Au 1er message d'une conversation, genere un titre automatique (resume court via LLM).
   - GET /conversations : liste toutes les conversations (id, title, updated_at), triees par updated_at DESC
   - GET /conversations/{id}/messages : retourne tous les messages d'une conversation
   - DELETE /conversations/{id} : supprime conversation et ses messages
   - PATCH /conversations/{id} : renommer une conversation (champ title)

3. Modifie memory/store.py :
   - Charge le contexte depuis SQLite (derniers N messages de la conversation active) au lieu de la deque

4. Modifie templates/index.html :
   - Ajoute une sidebar a gauche avec la liste des conversations
   - Bouton "Nouvelle conversation" en haut de la sidebar
   - Chaque conversation : titre cliquable, bouton supprimer (icone), date relative
   - La sidebar est retractable sur mobile (bouton hamburger)

5. Modifie luciole.css :
   - Layout 2 colonnes (sidebar 280px + zone chat flexible)
   - Styles sidebar : liste, hover, conversation active, scroll
   - Responsive : sidebar en overlay sur mobile

6. Modifie luciole-chat.js :
   - Au chargement : fetch /conversations, affiche dans sidebar
   - Clic sur conversation : fetch /conversations/{id}/messages, affiche dans le chat
   - Nouvelle conversation : reset le chat, pas de conversation_id
   - Apres chaque message : met a jour la sidebar (nouveau titre, reordonne)
   - Bouton supprimer : confirmation puis DELETE, retire de la sidebar

Design coherent avec le systeme existant (editorial, serif/sans, couleurs luciole).
```

---

## Phase 2 — Comptes utilisateurs et authentification

### Contexte
Actuellement, une seule API key partagee, pas de notion d'utilisateur. Tous les visiteurs partagent le meme agent. Il faut isoler les conversations par utilisateur.

### Modele de donnees
```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    display_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Ajouter colonne user_id a conversations
ALTER TABLE conversations ADD COLUMN user_id TEXT REFERENCES users(id);
```

### Fichiers concernes
- Nouveau : `auth.py` — hashing bcrypt, creation/validation JWT, middleware FastAPI
- `database.py` — table users, fonctions CRUD user
- `api.py` — routes auth + proteger les routes existantes
- Nouveau : `templates/login.html` — page connexion/inscription
- `templates/base.html` — afficher nom utilisateur, bouton deconnexion
- `static/luciole.css` — styles pages auth
- `static/luciole-chat.js` — gestion token JWT, redirection si non connecte
- `requirements.txt` — ajouter `bcrypt`, `python-jose[cryptography]`

### Prompt
```
Dans le projet /Users/josuexavierrocha/Projets/ia/fil-rouge/, implemente un systeme de comptes utilisateurs :

1. Ajoute les dependances dans requirements.txt : bcrypt, python-jose[cryptography]

2. Cree auth.py :
   - Hash/verify mot de passe avec bcrypt
   - Creation JWT (access token, expire en 24h) avec secret depuis .env (JWT_SECRET)
   - Middleware FastAPI : decode le JWT depuis cookie httpOnly "access_token"
   - Dependency get_current_user() qui retourne le user ou redirige vers /login
   - Dependency get_optional_user() pour les pages publiques

3. Modifie database.py :
   - Table users (id UUID, email unique, password_hash, display_name, created_at)
   - Ajoute user_id (nullable) a la table conversations
   - Fonctions : create_user, get_user_by_email, get_user_by_id

4. Cree templates/login.html (extend base.html) :
   - Formulaire double : onglet Connexion / onglet Inscription
   - Champs : email, mot de passe, (nom d'affichage pour inscription)
   - Validation client + messages d'erreur
   - Design coherent avec le style editorial Luciole

5. Modifie api.py :
   - POST /auth/register : cree un compte, retourne JWT en cookie
   - POST /auth/login : verifie credentials, retourne JWT en cookie
   - POST /auth/logout : supprime le cookie
   - GET /login : page login.html
   - Protege GET /, GET /conversations, POST /ask etc. avec get_current_user
   - GET /about reste public
   - Filtre les conversations par user_id du token

6. Modifie templates/base.html :
   - Si connecte : afficher le nom d'utilisateur + bouton Deconnexion dans le header
   - Si non connecte : bouton Connexion

7. Modifie luciole-chat.js :
   - Gere la redirection vers /login si 401
   - Formulaire login/register en fetch (pas de rechargement de page)

Ne PAS implementer OAuth pour l'instant, seulement email/password.
Ajouter JWT_SECRET dans .env.example.
```

---

## Phase 3 — Streaming des reponses (SSE)

### Contexte
Actuellement, POST /ask attend la fin complete de l'execution de l'agent (qui peut prendre plusieurs secondes avec les appels outils) avant de retourner la reponse. L'utilisateur voit juste un spinner.

### Fichiers concernes
- `api.py` — transformer POST /ask en StreamingResponse SSE
- `main.py` — modifier la boucle ReAct pour yield les etapes intermediaires
- `static/luciole-chat.js` — remplacer fetch par EventSource, affichage progressif
- `static/luciole.css` — styles pour les etapes de reflexion (tool calls)

### Prompt
```
Dans le projet /Users/josuexavierrocha/Projets/ia/fil-rouge/, implemente le streaming des reponses avec Server-Sent Events :

1. Modifie main.py :
   - Transforme la fonction agent principale en generateur async (async def run_agent_stream)
   - Yield des evenements JSON a chaque etape :
     - {"type": "thinking", "tool": "nom_outil"} quand l'agent choisit un outil
     - {"type": "tool_result", "tool": "nom_outil", "summary": "..."} apres execution
     - {"type": "chunk", "content": "..."} pour les tokens de la reponse finale
     - {"type": "done", "latency_ms": 1234, "tokens": 567} a la fin
   - Garde l'ancienne fonction synchrone comme fallback

2. Modifie api.py :
   - POST /ask retourne un StreamingResponse avec media_type="text/event-stream"
   - Format SSE : "data: {json}\n\n" pour chaque evenement
   - Gere la deconnexion client proprement

3. Modifie luciole-chat.js :
   - Remplace le fetch POST par un EventSource ou fetch + ReadableStream
   - A la reception de "thinking" : affiche un badge "Recherche dans les articles..." ou "Interrogation de la base..."
   - A la reception de "chunk" : append le texte progressivement dans la bulle agent
   - A la reception de "done" : finalise l'affichage, ajoute timestamp et latence
   - Render le Markdown incrementalement (ou a la fin)

4. Modifie luciole.css :
   - Style pour les badges d'etape (icone outil + texte, apparition animee)
   - Animation de texte qui apparait progressivement

Le streaming doit etre compatible avec la sauvegarde en DB (historique Phase 1).
```

---

## Phase 4 — Upload de fichiers

### Contexte
Les outils audio_transcription et image_analysis existent dans l'agent mais necessitent un chemin fichier sur le serveur. L'utilisateur ne peut pas uploader de fichiers depuis l'interface.

### Fichiers concernes
- `api.py` — endpoint POST /upload, modification de POST /ask pour gerer les fichiers
- `static/luciole-chat.js` — zone de drop, preview, envoi multipart
- `static/luciole.css` — styles zone upload, preview fichier
- `templates/index.html` — bouton attach dans la barre de saisie
- `config.py` — limite taille fichier, types acceptes, dossier temporaire

### Prompt
```
Dans le projet /Users/josuexavierrocha/Projets/ia/fil-rouge/, ajoute le support d'upload de fichiers dans le chat :

1. Modifie config.py :
   - UPLOAD_DIR = data/uploads/ (cree au demarrage)
   - MAX_FILE_SIZE = 10 MB
   - ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp", "audio/mpeg", "audio/mp4", "audio/wav", "application/pdf"}
   - UPLOAD_TTL = 3600 (nettoyage auto apres 1h)

2. Modifie api.py :
   - POST /upload : recoit un fichier (UploadFile), valide type/taille, sauvegarde dans UPLOAD_DIR avec nom unique, retourne {"file_id": "...", "filename": "...", "type": "..."}
   - Modifie POST /ask pour accepter un champ optionnel file_id. Si present, recupere le fichier et le passe a l'agent avec le bon outil (image → image_analysis, audio → audio_transcription)
   - Tache de fond (APScheduler) pour nettoyer les uploads expires

3. Modifie templates/index.html :
   - Ajoute un bouton piece jointe (icone trombone) a gauche du champ de saisie
   - Input file cache declenche par le bouton

4. Modifie luciole-chat.js :
   - Clic trombone → ouvre le selecteur de fichier
   - Drag & drop sur la zone de chat → intercepte le fichier
   - Preview du fichier selectionne (miniature image, nom+taille pour audio)
   - Bouton X pour retirer le fichier avant envoi
   - A l'envoi : POST /upload d'abord, puis POST /ask avec file_id
   - Affiche le fichier dans la bulle utilisateur (image inline, player audio)

5. Modifie luciole.css :
   - Style du bouton trombone
   - Zone de preview fichier (sous le champ de saisie)
   - Style drag & drop (bordure pointillee, highlight)
   - Image inline dans les bulles de chat
   - Player audio minimal dans les bulles

Limiter les types de fichiers cote client ET serveur. Valider cote serveur avec magic bytes, pas seulement l'extension.
```

---

## Phase 5 — Dark mode

### Contexte
Le design system Luciole est light-only. Beaucoup d'utilisateurs preferent un mode sombre, surtout pour un outil de veille utilise quotidiennement.

### Fichiers concernes
- `static/luciole.css` — variables alternatives, media query
- `templates/base.html` — toggle dark/light dans le header
- `static/luciole-chat.js` — logique toggle, persistence dans localStorage

### Prompt
```
Dans le projet /Users/josuexavierrocha/Projets/ia/fil-rouge/, ajoute un dark mode au design system :

1. Modifie luciole.css :
   - Cree un bloc @media (prefers-color-scheme: dark) qui redefinit les variables :
     --luciole-ink: #e8e8e8
     --luciole-paper: #1a1a1a
     --luciole-muted: #9a9a9a
     --luciole-accent: #ef4444 (rouge plus clair pour contraste sur fond sombre)
     --luciole-rule: rgba(255,255,255,0.1)
     --luciole-surface: #2a2a2a
   - Cree aussi une classe [data-theme="dark"] avec les memes overrides (pour le toggle manuel)
   - Ajuste les ombres, bordures, et fonds des composants pour le dark mode
   - Verifie le contraste WCAG AA sur tous les textes

2. Modifie templates/base.html :
   - Ajoute un bouton toggle theme dans le header (icone soleil/lune)
   - Le bouton est entre la nav et le contenu, discret

3. Modifie luciole-chat.js :
   - Au clic sur le toggle : bascule data-theme sur <html>, sauvegarde dans localStorage
   - Au chargement : lit localStorage, sinon respecte prefers-color-scheme
   - Transition douce (transition sur background-color et color)

Le dark mode doit couvrir : chat, sidebar, dashboard, digest, about, login.
```

---

## Phase 6 — Feedback sur les reponses et sources RAG

### Contexte
L'utilisateur n'a aucun moyen de noter les reponses de l'agent ni de voir les sources utilisees. Perplexity affiche les sources en citations numerotees, ChatGPT permet thumbs up/down.

### Fichiers concernes
- `api.py` — endpoint POST /feedback/response, modifier la reponse de /ask pour inclure les sources
- `main.py` — extraire et retourner les sources RAG utilisees
- `database.py` — table response_feedback
- `static/luciole-chat.js` — boutons feedback, affichage sources
- `static/luciole.css` — styles boutons feedback, bloc sources
- `templates/index.html` — structure HTML pour les nouveaux elements

### Prompt
```
Dans le projet /Users/josuexavierrocha/Projets/ia/fil-rouge/, ajoute le feedback utilisateur et l'affichage des sources :

1. Modifie database.py :
   - Table response_feedback (id, message_id, rating TEXT CHECK IN ('up','down'), comment TEXT, created_at)
   - Fonctions : save_feedback, get_feedback_stats

2. Modifie main.py :
   - Quand l'agent utilise l'outil RAG, collecte les sources (titre, URL, score de similarite)
   - Retourne les sources dans la reponse structuree : {"response": "...", "sources": [...]}

3. Modifie api.py :
   - POST /ask retourne maintenant {reponse, sources, conversation_id, message_id}
   - POST /feedback/response : recoit {message_id, rating, comment?}, sauvegarde en DB
   - GET /feedback/stats : stats globales (% positif, total)

4. Modifie luciole-chat.js :
   - Sous chaque reponse agent, ajoute une barre d'actions :
     - Bouton copier (icone copie → "Copie !" pendant 2s)
     - Bouton thumbs up / thumbs down (un seul actif, toggle)
     - Thumbs down ouvre un petit champ texte optionnel pour le commentaire
   - Si sources presentes, affiche un bloc "Sources" repliable sous la reponse :
     - Chaque source : numero, titre cliquable (lien), score de pertinence en %
   - Bouton "Regenerer" pour relancer la meme question

5. Modifie luciole.css :
   - Barre d'actions : icones discrètes, hover visible, espacement
   - Bouton actif (thumbs up vert, thumbs down rouge)
   - Bloc sources : fond leger, bordure gauche accent, typography t-meta
   - Animation d'apparition du champ commentaire

Design discret et non intrusif, coherent avec l'esthetique editoriale.
```

---

## Ordre d'implementation recommande

| Phase | Fonctionnalite | Prerequis | Impact utilisateur |
|-------|---------------|-----------|-------------------|
| 0 | Renommage Pulse → Luciole | Aucun | Technique (nettoyage) |
| 1 | Historique conversations | Phase 0 | Tres fort |
| 2 | Comptes utilisateurs | Phase 1 | Fort |
| 3 | Streaming SSE | Phase 1 | Fort |
| 4 | Upload fichiers | Phase 0 | Moyen |
| 5 | Dark mode | Phase 0 | Moyen |
| 6 | Feedback + sources | Phase 1 | Moyen |

> **Conseil** : les phases 4, 5, 6 sont independantes entre elles et peuvent etre faites dans n'importe quel ordre apres leurs prerequis.
