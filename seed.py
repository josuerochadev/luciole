"""
Seed de la base RAG avec 60 articles synthétiques couvrant tous les thèmes.
Utilisation : python seed.py
"""
from tools.rag import indexer_articles, taille_index

ARTICLES_SEED = [
    # ------------------------------------------------------------------ IA (20)
    {"titre": "GPT-5 dévoilé : raisonnement multi-étapes et mémoire longue durée",
     "lien": "https://seed.example.com/gpt5", "categorie": "IA", "pertinence": 10,
     "resume": "OpenAI lance GPT-5 avec une fenêtre de contexte de 1M tokens et des capacités de raisonnement inédites. Le modèle surpasse tous les benchmarks existants en mathématiques et en code.", "source": "seed", "date_publication": "2026-04-01"},

    {"titre": "Mistral Large 3 : le champion européen de l'IA générative",
     "lien": "https://seed.example.com/mistral3", "categorie": "IA", "pertinence": 9,
     "resume": "Mistral AI publie son nouveau modèle Large 3, rival direct de GPT-4o. Entraîné sur des données européennes, il excelle en français et respecte le RGPD nativement.", "source": "seed", "date_publication": "2026-03-28"},

    {"titre": "NVIDIA Blackwell Ultra : 4x les performances d'inférence LLM",
     "lien": "https://seed.example.com/blackwell-ultra", "categorie": "IA", "pertinence": 9,
     "resume": "NVIDIA présente l'architecture Blackwell Ultra, optimisée pour l'inférence de grands modèles de langage. Les datacenter IA atteignent 4x le débit de la génération précédente.", "source": "seed", "date_publication": "2026-03-25"},

    {"titre": "Gemini 2.0 Ultra intègre la vision, le son et le code en temps réel",
     "lien": "https://seed.example.com/gemini2", "categorie": "IA", "pertinence": 8,
     "resume": "Google DeepMind déploie Gemini 2.0 Ultra avec des capacités multimodales avancées : analyse vidéo en direct, génération de code vérifiée et compréhension audio native.", "source": "seed", "date_publication": "2026-03-20"},

    {"titre": "LLaMA 4 open source : Meta démocratise les grands modèles",
     "lien": "https://seed.example.com/llama4", "categorie": "IA", "pertinence": 9,
     "resume": "Meta publie LLaMA 4 sous licence open source. Le modèle de 70B paramètres rivalise avec GPT-4o sur de nombreux benchmarks et peut être déployé localement.", "source": "seed", "date_publication": "2026-03-15"},

    {"titre": "Agents IA autonomes : vers des systèmes qui s'auto-améliorent",
     "lien": "https://seed.example.com/agents-autonomes", "categorie": "IA", "pertinence": 8,
     "resume": "Les nouveaux frameworks d'agents IA permettent des boucles d'auto-amélioration. AutoGPT 3.0 et BabyAGI montrent des capacités de planification sur plusieurs jours sans supervision humaine.", "source": "seed", "date_publication": "2026-03-10"},

    {"titre": "RAG vs Fine-tuning : quelle stratégie pour vos LLMs en production ?",
     "lien": "https://seed.example.com/rag-vs-ft", "categorie": "IA", "pertinence": 8,
     "resume": "Comparatif détaillé entre RAG et fine-tuning pour les cas d'usage enterprise. Le RAG s'impose pour les données dynamiques, le fine-tuning pour les domaines très spécialisés.", "source": "seed", "date_publication": "2026-03-08"},

    {"titre": "Hallucinations LLM : nouvelles techniques de détection et mitigation",
     "lien": "https://seed.example.com/hallucinations", "categorie": "IA", "pertinence": 7,
     "resume": "Trois nouvelles approches réduisent les hallucinations de 60% : grounding sur base vectorielle, vérification par un second modèle, et chaîne de pensée contrainte.", "source": "seed", "date_publication": "2026-03-05"},

    {"titre": "IA générative en entreprise : adoption à 65% dans le CAC 40",
     "lien": "https://seed.example.com/ia-cac40", "categorie": "IA", "pertinence": 7,
     "resume": "Étude Gartner : 65% des entreprises du CAC 40 ont déployé au moins un cas d'usage IA générative en production. Les économies de temps atteignent 25% sur les tâches répétitives.", "source": "seed", "date_publication": "2026-03-01"},

    {"titre": "Prompt engineering : les 10 patterns indispensables en 2026",
     "lien": "https://seed.example.com/prompt-patterns", "categorie": "IA", "pertinence": 6,
     "resume": "Chain-of-thought, few-shot, ReAct, Tree-of-Thought… Revue des patterns de prompt engineering les plus efficaces et leurs cas d'usage en production.", "source": "seed", "date_publication": "2026-02-28"},

    {"titre": "AMD MI350 : la réponse aux GPU NVIDIA pour l'IA",
     "lien": "https://seed.example.com/amd-mi350", "categorie": "IA", "pertinence": 7,
     "resume": "AMD lance les GPU MI350 ciblant directement le marché de l'entraînement LLM. Compatibilité ROCm améliorée et prix 30% inférieur aux H100 de NVIDIA.", "source": "seed", "date_publication": "2026-02-25"},

    {"titre": "IA et droit d'auteur : l'Europe tranche sur les données d'entraînement",
     "lien": "https://seed.example.com/ia-droit", "categorie": "IA", "pertinence": 6,
     "resume": "La Cour de Justice de l'UE établit que l'entraînement sur données publiques nécessite un opt-out explicite des ayants droit. Impact majeur sur les modèles européens.", "source": "seed", "date_publication": "2026-02-20"},

    {"titre": "Coût de l'inférence LLM : baisse de 90% en 18 mois",
     "lien": "https://seed.example.com/cout-inference", "categorie": "IA", "pertinence": 7,
     "resume": "Grâce à la concurrence et aux optimisations matérielles, le coût d'inférence des LLMs a chuté de 90% depuis 2024. GPT-4o-mini coûte désormais moins de 0.01€ pour 1000 tokens.", "source": "seed", "date_publication": "2026-02-15"},

    {"titre": "Multimodalité : les LLMs apprennent à lire les schémas techniques",
     "lien": "https://seed.example.com/llm-schemas", "categorie": "IA", "pertinence": 6,
     "resume": "Les derniers modèles multimodaux comprennent les diagrammes d'architecture, les schémas de base de données et les wireframes. Cas d'usage : documentation automatique.", "source": "seed", "date_publication": "2026-02-10"},

    {"titre": "Benchmarks LLM 2026 : MMLU, HumanEval, les nouveaux standards",
     "lien": "https://seed.example.com/benchmarks-2026", "categorie": "IA", "pertinence": 5,
     "resume": "Les benchmarks historiques sont saturés par les modèles actuels. La communauté adopte de nouveaux standards : MMLU-Pro, LiveCodeBench et des évaluations en conditions réelles.", "source": "seed", "date_publication": "2026-02-05"},

    {"titre": "IA embarquée : les LLMs passent sur smartphone en 2026",
     "lien": "https://seed.example.com/llm-mobile", "categorie": "IA", "pertinence": 7,
     "resume": "Apple, Qualcomm et MediaTek intègrent des NPUs dédiés aux LLMs dans leurs puces 2026. Des modèles de 3B paramètres tournent en temps réel sans connexion internet.", "source": "seed", "date_publication": "2026-02-01"},

    {"titre": "Deep learning : les transformers challengés par les architectures Mamba",
     "lien": "https://seed.example.com/mamba", "categorie": "IA", "pertinence": 6,
     "resume": "Les architectures SSM (State Space Models) comme Mamba offrent une complexité linéaire vs quadratique pour les transformers. Résultats prometteurs sur les longues séquences.", "source": "seed", "date_publication": "2026-01-28"},

    {"titre": "IA et productivité développeur : +40% de code généré par GitHub Copilot",
     "lien": "https://seed.example.com/copilot-stats", "categorie": "IA", "pertinence": 6,
     "resume": "GitHub publie des statistiques : les développeurs utilisant Copilot génèrent 40% de code en plus et complètent les tâches 55% plus vite. L'outil dépasse 2 millions d'utilisateurs actifs.", "source": "seed", "date_publication": "2026-01-25"},

    {"titre": "Éthique IA : le AI Act européen entre en vigueur",
     "lien": "https://seed.example.com/ai-act", "categorie": "IA", "pertinence": 8,
     "resume": "L'AI Act de l'Union Européenne est pleinement applicable. Les systèmes IA à haut risque doivent désormais passer une certification obligatoire. Les amendes peuvent atteindre 6% du CA mondial.", "source": "seed", "date_publication": "2026-01-20"},

    {"titre": "Synthèse vocale IA : impossible de distinguer du vrai en 2026",
     "lien": "https://seed.example.com/tts-2026", "categorie": "IA", "pertinence": 5,
     "resume": "ElevenLabs et OpenAI Voice Engine atteignent un niveau de réalisme indiscernable. La détection des deepfakes audio devient le nouveau défi de la cybersécurité.", "source": "seed", "date_publication": "2026-01-15"},

    # -------------------------------------------------------------- CYBERSÉCURITÉ (12)
    {"titre": "Prompt injection : nouvelle attaque cible les agents IA en production",
     "lien": "https://seed.example.com/prompt-injection-2026", "categorie": "Cybersécurité", "pertinence": 9,
     "resume": "Une nouvelle famille d'attaques par prompt injection contourne les garde-fous des LLMs en production. Les agents ReAct sont particulièrement vulnérables via les données tierces.", "source": "seed", "date_publication": "2026-04-02"},

    {"titre": "Ransomware-as-a-Service : les groupes adoptent l'IA pour personnaliser les attaques",
     "lien": "https://seed.example.com/ransomware-ai", "categorie": "Cybersécurité", "pertinence": 8,
     "resume": "Les groupes de ransomware utilisent des LLMs pour personnaliser les emails de phishing et adapter leur code malveillant à chaque cible. Hausse de 200% du taux de succès.", "source": "seed", "date_publication": "2026-03-22"},

    {"titre": "Zero-day Log4Shell 2 : vulnérabilité critique dans les librairies Java",
     "lien": "https://seed.example.com/log4shell2", "categorie": "Cybersécurité", "pertinence": 10,
     "resume": "Une vulnérabilité similaire à Log4Shell découverte dans une librairie Java largement utilisée. Score CVSS 9.8. Patch disponible, mise à jour urgente recommandée.", "source": "seed", "date_publication": "2026-03-18"},

    {"titre": "RGPD : 50M€ d'amende pour une fuite de données d'entraînement IA",
     "lien": "https://seed.example.com/rgpd-ia", "categorie": "Cybersécurité", "pertinence": 8,
     "resume": "La CNIL inflige une amende record de 50M€ à une entreprise pour avoir utilisé des données personnelles sans consentement pour entraîner un modèle IA. Jurisprudence majeure.", "source": "seed", "date_publication": "2026-03-12"},

    {"titre": "SOC nouvelle génération : détection des menaces par LLM en temps réel",
     "lien": "https://seed.example.com/soc-llm", "categorie": "Cybersécurité", "pertinence": 7,
     "resume": "Les SIEM intègrent des LLMs pour corréler les logs en langage naturel. Réduction de 70% du temps de triage des alertes et détection de patterns inédits.", "source": "seed", "date_publication": "2026-03-08"},

    {"titre": "Cryptographie post-quantique : NIST finalise les standards",
     "lien": "https://seed.example.com/post-quantique", "categorie": "Cybersécurité", "pertinence": 8,
     "resume": "Le NIST publie les standards définitifs de cryptographie post-quantique. Les entreprises ont 3 ans pour migrer leurs systèmes. CRYSTALS-Kyber et CRYSTALS-Dilithium sont retenus.", "source": "seed", "date_publication": "2026-03-01"},

    {"titre": "Attaques supply chain : 3 librairies npm compromises en une semaine",
     "lien": "https://seed.example.com/supply-chain", "categorie": "Cybersécurité", "pertinence": 8,
     "resume": "Trois librairies npm populaires ont été compromises via des comptes mainteneurs piratés. Les packages malveillants ont été téléchargés 2M de fois avant détection.", "source": "seed", "date_publication": "2026-02-22"},

    {"titre": "Authentification sans mot de passe : les passkeys s'imposent en entreprise",
     "lien": "https://seed.example.com/passkeys", "categorie": "Cybersécurité", "pertinence": 6,
     "resume": "L'adoption des passkeys FIDO2 atteint 40% dans les entreprises du Fortune 500. Réduction de 99% des attaques par credential stuffing sur les comptes protégés.", "source": "seed", "date_publication": "2026-02-18"},

    {"titre": "Deepfake vidéo : les outils de détection peinent à suivre",
     "lien": "https://seed.example.com/deepfake-detection", "categorie": "Cybersécurité", "pertinence": 7,
     "resume": "Les générateurs de deepfakes vidéo surpassent les détecteurs dans 60% des cas selon une étude MIT. Les arnaques CEO fraud via deepfake ont coûté 1.2Md$ en 2025.", "source": "seed", "date_publication": "2026-02-10"},

    {"titre": "Sécurité des API : OWASP publie le top 10 2026",
     "lien": "https://seed.example.com/owasp-api", "categorie": "Cybersécurité", "pertinence": 6,
     "resume": "OWASP met à jour son top 10 des vulnérabilités API. Les injections LLM font leur entrée, rejoignant les classiques BOLA, authentification cassée et exposition de données.", "source": "seed", "date_publication": "2026-02-05"},

    {"titre": "Red teaming IA : les entreprises testent leurs LLMs comme des systèmes critiques",
     "lien": "https://seed.example.com/redteam-ia", "categorie": "Cybersécurité", "pertinence": 7,
     "resume": "Les équipes de sécurité adoptent le red teaming spécifique aux LLMs : jailbreaking, extraction de données d'entraînement, manipulation d'agents. Nouveau métier : AI Security Engineer.", "source": "seed", "date_publication": "2026-01-30"},

    {"titre": "NIS2 : les entreprises européennes se mettent en conformité",
     "lien": "https://seed.example.com/nis2", "categorie": "Cybersécurité", "pertinence": 6,
     "resume": "La directive NIS2 est pleinement applicable. 18 secteurs critiques doivent notifier les incidents sous 24h et implémenter des mesures de sécurité renforcées.", "source": "seed", "date_publication": "2026-01-25"},

    # ---------------------------------------------------------------- CLOUD (12)
    {"titre": "AWS re:Invent 2025 : 40 nouveaux services dont Bedrock 3.0",
     "lien": "https://seed.example.com/aws-reinvent", "categorie": "Cloud", "pertinence": 9,
     "resume": "Amazon Web Services annonce 40 nouveaux services dont Bedrock 3.0 avec support multi-agents natif, SageMaker HyperPod pour l'entraînement distribué et Aurora Limitless pour les bases serverless.", "source": "seed", "date_publication": "2026-03-30"},

    {"titre": "Azure OpenAI Service : GPT-5 disponible en preview",
     "lien": "https://seed.example.com/azure-gpt5", "categorie": "Cloud", "pertinence": 8,
     "resume": "Microsoft rend GPT-5 disponible en preview sur Azure OpenAI Service. Intégration native avec Azure AI Search pour le RAG et Semantic Kernel pour les agents.", "source": "seed", "date_publication": "2026-03-26"},

    {"titre": "Google Cloud Next 2026 : Vertex AI et les agents multi-modaux",
     "lien": "https://seed.example.com/gcloud-next", "categorie": "Cloud", "pertinence": 8,
     "resume": "Google Cloud annonce Vertex AI Agent Builder, permettant de créer des agents IA multimodaux sans code. TPU v6 disponible pour l'entraînement à grande échelle.", "source": "seed", "date_publication": "2026-03-20"},

    {"titre": "FinOps cloud : les coûts IA explosent, les entreprises cherchent à optimiser",
     "loin": "https://seed.example.com/finops-ia", "lien": "https://seed.example.com/finops-ia", "categorie": "Cloud", "pertinence": 7,
     "resume": "Les coûts cloud liés à l'IA représentent désormais 40% des factures AWS/Azure/GCP des grandes entreprises. Les pratiques FinOps s'adaptent : spot instances pour l'inférence, réservations pour l'entraînement.", "source": "seed", "date_publication": "2026-03-15"},

    {"titre": "Serverless IA : AWS Lambda supporte désormais les modèles jusqu'à 10GB",
     "lien": "https://seed.example.com/lambda-ia", "categorie": "Cloud", "pertinence": 7,
     "resume": "AWS Lambda augmente sa limite mémoire à 10GB et intègre un layer d'optimisation pour l'inférence LLM. Les fonctions peuvent désormais héberger des modèles de taille moyenne.", "source": "seed", "date_publication": "2026-03-10"},

    {"titre": "Multi-cloud : 78% des entreprises utilisent au moins 2 fournisseurs",
     "lien": "https://seed.example.com/multicloud", "categorie": "Cloud", "pertinence": 6,
     "resume": "Étude IDC : 78% des entreprises ont adopté une stratégie multi-cloud. Terraform et Pulumi s'imposent comme standards d'Infrastructure as Code pour gérer cette complexité.", "source": "seed", "date_publication": "2026-03-05"},

    {"titre": "Cloud souverain français : Bleu et S3NS passent en GA",
     "lien": "https://seed.example.com/cloud-souverain", "categorie": "Cloud", "pertinence": 8,
     "resume": "Les offres de cloud souverain français Bleu (Orange/Capgemini/Microsoft) et S3NS (Thales/Google) passent en disponibilité générale. Premiers clients dans le secteur public et la défense.", "source": "seed", "date_publication": "2026-02-28"},

    {"titre": "Kubernetes 1.32 : gestion native des GPU partagés et scheduler IA",
     "lien": "https://seed.example.com/k8s-132-detail", "categorie": "Cloud", "pertinence": 7,
     "resume": "Kubernetes 1.32 introduit le partage de GPU via MIG (Multi-Instance GPU) natif et un scheduler optimisé pour les workloads IA. Réduction de 40% des coûts GPU en environnement partagé.", "source": "seed", "date_publication": "2026-02-20"},

    {"titre": "Edge computing : AWS Outposts et Azure Stack convergent vers l'IA temps réel",
     "lien": "https://seed.example.com/edge-ia", "categorie": "Cloud", "pertinence": 6,
     "resume": "Les solutions d'edge computing intègrent des accélérateurs IA pour l'inférence locale. Cas d'usage : manufacturing, retail et santé où la latence est critique.", "source": "seed", "date_publication": "2026-02-15"},

    {"titre": "Databricks vs Snowflake : la guerre des plateformes data IA",
     "lien": "https://seed.example.com/databricks-snowflake", "categorie": "Cloud", "pertinence": 6,
     "resume": "Databricks et Snowflake s'affrontent sur le marché du lakehouse IA. Databricks Unity Catalog vs Snowflake Cortex : comparatif des fonctionnalités IA intégrées.", "source": "seed", "date_publication": "2026-02-10"},

    {"titre": "OpenTofu 2.0 : le fork open source de Terraform gagne du terrain",
     "lien": "https://seed.example.com/opentofu2", "categorie": "Cloud", "pertinence": 5,
     "resume": "OpenTofu 2.0, le fork open source de Terraform suite au changement de licence HashiCorp, adopte par 30% des nouvelles installations. Compatibilité complète avec l'écosystème Terraform.", "source": "seed", "date_publication": "2026-02-05"},

    {"titre": "Coût de transfert de données cloud : l'UE force la transparence",
     "lien": "https://seed.example.com/egress-eu", "categorie": "Cloud", "pertinence": 5,
     "resume": "La Commission Européenne oblige les hyperscalers à supprimer les frais de sortie de données vers d'autres fournisseurs EU. Facilite la portabilité et réduit le vendor lock-in.", "source": "seed", "date_publication": "2026-01-30"},

    # --------------------------------------------------------------- DEVOPS (8)
    {"titre": "GitHub Actions 3.0 : pipelines IA-assisted et auto-réparation des builds",
     "lien": "https://seed.example.com/gh-actions3", "categorie": "DevOps", "pertinence": 7,
     "resume": "GitHub Actions 3.0 intègre un assistant IA qui suggère des corrections automatiques en cas d'échec de build et optimise les pipelines CI/CD selon les patterns historiques.", "source": "seed", "date_publication": "2026-03-28"},

    {"titre": "DevSecOps : la sécurité shift-left devient la norme en 2026",
     "lien": "https://seed.example.com/devsecops", "categorie": "DevOps", "pertinence": 6,
     "resume": "Gartner : 80% des entreprises intègrent des outils de sécurité directement dans les pipelines CI/CD. SAST, DAST et SCA automatisés bloquent les vulnérabilités avant production.", "source": "seed", "date_publication": "2026-03-15"},

    {"titre": "Observabilité : OpenTelemetry s'impose comme standard universel",
     "lien": "https://seed.example.com/otel", "categorie": "DevOps", "pertinence": 6,
     "resume": "OpenTelemetry atteint 1 milliard de téléchargements mensuels. Les principaux APM (Datadog, Grafana, New Relic) abandonnent leurs agents propriétaires pour OpenTelemetry.", "source": "seed", "date_publication": "2026-03-05"},

    {"titre": "Platform Engineering : les Internal Developer Platforms montent en puissance",
     "lien": "https://seed.example.com/idp", "categorie": "DevOps", "pertinence": 6,
     "resume": "Les Internal Developer Platforms (IDP) simplifient l'accès aux ressources cloud pour les développeurs. Backstage de Spotify devient le standard de facto avec 2000 entreprises utilisatrices.", "source": "seed", "date_publication": "2026-02-25"},

    {"titre": "Conteneurs vs WebAssembly : WASM gagne du terrain pour les microservices",
     "lien": "https://seed.example.com/wasm", "categorie": "DevOps", "pertinence": 5,
     "resume": "WebAssembly s'impose comme alternative légère aux conteneurs pour les fonctions courtes. Démarrage en microsecondes et isolation sécurisée sans overhead Docker.", "source": "seed", "date_publication": "2026-02-15"},

    {"titre": "GitOps avec ArgoCD et Flux : déploiements Kubernetes en 2026",
     "lien": "https://seed.example.com/gitops", "categorie": "DevOps", "pertinence": 5,
     "resume": "ArgoCD 3.0 et Flux 3.0 rivalisent pour le marché GitOps Kubernetes. Comparatif des fonctionnalités : synchronisation multi-cluster, drift detection et rollback automatique.", "source": "seed", "date_publication": "2026-02-05"},

    {"titre": "eBPF révolutionne le monitoring réseau Linux sans modification kernel",
     "lien": "https://seed.example.com/ebpf", "categorie": "DevOps", "pertinence": 6,
     "resume": "eBPF permet d'injecter du code dans le kernel Linux sans le modifier. Cilium et Pixie l'utilisent pour un monitoring réseau à faible overhead dans les clusters Kubernetes.", "source": "seed", "date_publication": "2026-01-25"},

    {"titre": "Chaos Engineering : Netflix open source sa plateforme de résilience",
     "lien": "https://seed.example.com/chaos", "categorie": "DevOps", "pertinence": 5,
     "resume": "Netflix open source ChaosPlatform, son outil interne de chaos engineering. Permet d'injecter des pannes contrôlées en production pour valider la résilience des microservices.", "source": "seed", "date_publication": "2026-01-15"},

    # --------------------------------------------------------------- DONNÉES (8)
    {"titre": "Apache Spark 4.0 : performances x3 pour les pipelines data IA",
     "lien": "https://seed.example.com/spark4", "categorie": "Données", "pertinence": 7,
     "resume": "Apache Spark 4.0 introduit un moteur d'exécution vectorisé offrant 3x les performances pour les traitements ML. Intégration native avec Delta Lake 4.0 et support GPU.", "source": "seed", "date_publication": "2026-03-20"},

    {"titre": "Data mesh : retour d'expérience après 3 ans de déploiement chez ING",
     "lien": "https://seed.example.com/datamesh-ing", "categorie": "Données", "pertinence": 6,
     "resume": "ING Bank partage son retour d'expérience sur 3 ans de data mesh. Résultats : time-to-insight divisé par 4, mais gouvernance complexe. Recommandations pour les entreprises qui démarrent.", "source": "seed", "date_publication": "2026-03-10"},

    {"titre": "DuckDB 2.0 : OLAP in-process devient sérieux pour la production",
     "lien": "https://seed.example.com/duckdb2", "categorie": "Données", "pertinence": 6,
     "resume": "DuckDB 2.0 supporte désormais les transactions ACID et la réplication. La base OLAP embarquée gagne sa place en production pour les analyses sur des datasets jusqu'à 100GB.", "source": "seed", "date_publication": "2026-03-01"},

    {"titre": "Synthèse de données : générer des datasets d'entraînement IA sans données réelles",
     "lien": "https://seed.example.com/synthetic-data", "categorie": "Données", "pertinence": 7,
     "resume": "Les outils de génération de données synthétiques permettent de créer des datasets d'entraînement respectant le RGPD. Mostly AI et Gretel.ai s'imposent sur ce marché émergent.", "source": "seed", "date_publication": "2026-02-20"},

    {"titre": "Vector databases en 2026 : Pinecone, Weaviate, pgvector — qui gagne ?",
     "lien": "https://seed.example.com/vector-db", "categorie": "Données", "pertinence": 8,
     "resume": "Comparatif des bases vectorielles pour le RAG en production. pgvector sur PostgreSQL s'impose pour les PME, Weaviate pour les grandes échelles, Pinecone pour le serverless.", "source": "seed", "date_publication": "2026-02-10"},

    {"titre": "Data contracts : formaliser les interfaces entre producteurs et consommateurs",
     "lien": "https://seed.example.com/data-contracts", "categorie": "Données", "pertinence": 5,
     "resume": "Les data contracts définissent des SLAs sur la qualité et le format des données. Soda, Great Expectations et dbt Tests s'intègrent dans les pipelines pour valider ces contrats.", "source": "seed", "date_publication": "2026-02-01"},

    {"titre": "Temps réel vs batch : l'essor d'Apache Flink pour le streaming IA",
     "lien": "https://seed.example.com/flink-ia", "categorie": "Données", "pertinence": 6,
     "resume": "Apache Flink 2.0 intègre des opérateurs ML natifs pour le streaming. Cas d'usage : détection de fraude en temps réel, personnalisation et monitoring de modèles IA en production.", "source": "seed", "date_publication": "2026-01-25"},

    {"titre": "Gouvernance des données IA : traçabilité du lineage bout en bout",
     "lien": "https://seed.example.com/lineage", "categorie": "Données", "pertinence": 6,
     "resume": "OpenLineage et Marquez permettent de tracer l'origine de chaque donnée utilisée pour entraîner un modèle IA. Requis par l'AI Act pour les systèmes à haut risque.", "source": "seed", "date_publication": "2026-01-20"},
]

if __name__ == "__main__":
    print("=" * 60)
    print(f"SEED — Indexation de {len(ARTICLES_SEED)} articles synthétiques")
    print("=" * 60)

    print(f"\nIndex avant seed : {taille_index()} documents")
    n = indexer_articles(ARTICLES_SEED)
    print(f"Index après seed  : {taille_index()} documents")
    print(f"\n✓ {n}/{len(ARTICLES_SEED)} articles indexés avec succès.")
