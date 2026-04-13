import os
from dotenv import load_dotenv

load_dotenv()

# --- Modèle et paramètres LLM ---
MODEL_DEFAULT = "gpt-4o-mini"
TEMPERATURE = 0.3
MAX_TOKENS = 1024

# --- Clé API (depuis variable d'environnement) ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- System prompt de l'agent ---
SYSTEM_PROMPT = (
    "Tu es un agent de veille technologique. "
    "Ton rôle est de lire des articles RSS, d'en extraire l'essentiel, "
    "de les classer par catégorie et d'évaluer leur pertinence sur une échelle de 1 à 10. "
    "Sois concis, factuel et professionnel. Réponds toujours en français."
)

# --- Sources RSS surveillées ---
RSS_SOURCES = [
    # Français
    "https://next.ink/rss/news.xml",
    "https://korben.info/feed",
    "https://www.silicon.fr/feed",
    "https://www.zdnet.fr/feeds/rss/actualites/",
    # International
    "https://4sysops.com/feed/",
    "https://techcrunch.com/feed/",
    "https://feeds.arstechnica.com/arstechnica/index",
    "https://www.theverge.com/rss/index.xml",
    # Cloud & DevOps
    "https://aws.amazon.com/blogs/aws/feed/",
    "https://kubernetes.io/feed.xml",
    # Cybersécurité
    "https://www.cybersecuritydive.com/feeds/news/",
    # IA
    "https://blogs.microsoft.com/ai/feed/",
]

# --- Thèmes de filtrage ---
THEMES = [
    "intelligence artificielle",
    "cybersécurité",
    "cyber",
    "cloud",
    "infrastructure",
    "DevOps",
    "LLM",
    "GPU",
    "données",
    "kubernetes",
    "docker",
    "sécurité",
    "machine learning",
    "deep learning",
    "open source",
    "azure",
    "aws",
    "linux",
]

# --- Seuil de pertinence (articles en-dessous ignorés) ---
PERTINENCE_MIN = 5

# --- Nombre max d'articles par rapport quotidien ---
MAX_ARTICLES_PAR_RAPPORT = 20

# --- Stockage local ---
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_BASE_DIR, "data")
ARTICLES_FILE = f"{DATA_DIR}/articles.json"
HISTORIQUE_FILE = f"{DATA_DIR}/historique_envois.json"
ARCHIVES_FILE = f"{DATA_DIR}/archives.json"
LOGS_FILE = f"{DATA_DIR}/logs.jsonl"

# --- Rétention des données (en jours) ---
RETENTION_ARTICLES_JOURS = 90
RETENTION_LOGS_JOURS = 30

# --- Configuration email ---
EMAIL_EXPEDITEUR = os.getenv("EMAIL_EXPEDITEUR", "veille@example.com")
EMAIL_DESTINATAIRES = os.getenv("EMAIL_DESTINATAIRES", "").split(",")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
