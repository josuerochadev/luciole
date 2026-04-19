import os
from dotenv import load_dotenv

load_dotenv()

# --- Modèle et paramètres LLM ---
MODEL_DEFAULT = "gpt-4o-mini"
MODEL_FAST = "gpt-4o-mini"        # Cascade M6E3 : modèle rapide/économique
MODEL_POWERFUL = "gpt-4o"          # Cascade M6E3 : modèle puissant (raisonnement complexe)
MODEL_VISION = "gpt-4o"            # Vision nécessite gpt-4o (pas mini)
TEMPERATURE = 0.3
MAX_TOKENS = 2048

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
    # ── Français ──
    "https://next.ink/rss/news.xml",
    "https://korben.info/feed",
    "https://www.silicon.fr/feed",
    "https://www.zdnet.fr/feeds/rss/actualites/",
    "https://www.journaldunet.com/rss/",
    "https://www.lemondeinformatique.fr/flux-rss/thematique/toutes-les-actualites/rss.xml",
    "https://www.blogdumoderateur.com/feed/",
    "https://siecledigital.fr/feed/",
    # ── IA & Machine Learning ──
    "https://blogs.microsoft.com/ai/feed/",
    "https://blog.google/technology/ai/rss/",
    "https://openai.com/blog/rss.xml",
    "https://huggingface.co/blog/feed.xml",
    "https://ai.meta.com/blog/rss/",
    "https://deepmind.google/blog/rss.xml",
    "https://www.marktechpost.com/feed/",
    "https://thesequence.substack.com/feed",
    "https://jack-clark.net/feed/",
    "https://newsletter.ruder.io/feed",
    # ── Tech généraliste ──
    "https://techcrunch.com/feed/",
    "https://feeds.arstechnica.com/arstechnica/index",
    "https://www.theverge.com/rss/index.xml",
    "https://www.wired.com/feed/rss",
    "https://thenewstack.io/feed",
    "https://news.ycombinator.com/rss",
    "https://www.infoq.com/feed/",
    "https://dev.to/feed",
    # ── Cloud & DevOps ──
    "https://aws.amazon.com/blogs/aws/feed/",
    "https://cloud.google.com/blog/products/ai-machine-learning/rss",
    "https://azure.microsoft.com/en-us/blog/feed/",
    "https://kubernetes.io/feed.xml",
    "https://www.hashicorp.com/blog/feed.xml",
    "https://www.cncf.io/blog/feed/",
    "https://4sysops.com/feed/",
    # ── Cybersécurité ──
    "https://www.cybersecuritydive.com/feeds/news/",
    "https://thehackernews.com/feeds/posts/default",
    "https://www.bleepingcomputer.com/feed/",
    "https://krebsonsecurity.com/feed/",
    "https://www.schneier.com/feed/atom/",
    "https://www.darkreading.com/rss.xml",
    # ── Open Source & Linux ──
    "https://www.phoronix.com/rss.php",
    "https://www.omgubuntu.co.uk/feed",
    "https://itsfoss.com/feed/",
]

# --- Thèmes de filtrage ---
THEMES = [
    # IA & LLM
    "intelligence artificielle", "artificial intelligence",
    "machine learning", "deep learning", "neural network",
    "LLM", "GPT", "chatgpt", "gemini", "claude", "mistral", "llama",
    "openai", "anthropic", "hugging face", "transformer",
    "RAG", "fine-tuning", "embedding", "prompt",
    "agent", "agentique", "agentic",
    "IA générative", "generative ai", "gen ai",
    "computer vision", "NLP", "diffusion",
    # Cloud & Infrastructure
    "cloud", "infrastructure", "serverless", "microservice",
    "azure", "aws", "gcp", "google cloud",
    "kubernetes", "docker", "terraform", "ansible",
    "DevOps", "CI/CD", "MLOps", "GitOps",
    "SaaS", "PaaS", "IaaS",
    # Cybersécurité
    "cybersécurité", "cybersecurity", "cyber",
    "sécurité", "security", "zero-day", "ransomware",
    "phishing", "malware", "vulnerability", "faille",
    "SOC", "SIEM", "pentest", "zero trust",
    # Data & Open Source
    "données", "data", "big data", "data lake",
    "open source", "linux", "GPU", "NVIDIA",
    "API", "python", "rust",
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
