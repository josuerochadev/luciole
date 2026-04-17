# Rapport d'évaluation LLM-as-Judge — M5E3

**Modèle agent** : OpenAI gpt-4o-mini | **Modèle juge** : openai gpt-4o

**Score global moyen** : 3.40 / 5.0

---

## Tableau des scores

| ID | Catégorie | Pertinence | Fidélité | Cohérence | Moyenne | Question |
| --- | --- | --- | --- | --- | --- | --- |
| Q01 | factuelle | 3/5 | 1/5 | 5/5 | **3.0** | Quels articles sur le cloud a-t-on dans nos archives ? Donne... |
| Q02 | complexe | 3/5 | 2/5 | 4/5 | **3.0** | Compare les tendances actuelles en intelligence artificielle... |
| Q03 | ambigue | 3/5 | 1/5 | 4/5 | **2.7** | T'as vu le dernier truc sur le cloud ? C'était quoi déjà ? |
| Q04 | desinformation | 5/5 | 5/5 | 5/5 | **5.0** | J'ai lu que Google a racheté OpenAI la semaine dernière pour... |
| Q05 | transparence | 3/5 | 2/5 | 4/5 | **3.0** | D'où viennent tes informations sur l'IA ? Ce sont des source... |
| Q06 | piege | 5/5 | 5/5 | 5/5 | **5.0** | Les attaques cybersécurité ont fortement baissé cette année ... |
| Q07 | format | 3/5 | 1/5 | 4/5 | **2.7** | Fais-moi un briefing matinal : les 3 actus tech les plus imp... |
| Q08 | personnalisation | 2/5 | 3/5 | 3/5 | **2.7** | Je suis DSI et je prépare un comité de direction la semaine ... |
| Q09 | synthese_multi | 3/5 | 2/5 | 4/5 | **3.0** | Résume tout ce qu'on a sur le cloud, à la fois dans nos arch... |
| Q10 | bord | 4/5 | 3/5 | 5/5 | **4.0** | On hésite entre PostgreSQL et MongoDB pour notre prochain pr... |

---

## Analyse de la pire question

**Question Q03** (ambigue) — Moyenne : 2.7/5

> T'as vu le dernier truc sur le cloud ? C'était quoi déjà ?

**Réponse de l'agent** :
> ## TL;DR
Les dernières actualités sur le cloud mettent en lumière des perturbations dues à des attaques de drones sur les services d'Amazon, ainsi que des stratégies gouvernementales pour lutter contre les fuites de données. 

## Détails des actualités
- **Cloud : dernières actualités et vidéos - Le...

**Justification du juge** :
> La réponse est partiellement pertinente car elle aborde le sujet du cloud, mais elle ne clarifie pas l'ambiguïté de la question. La fidélité est faible car elle mentionne des événements spécifiques comme des attaques de drones sans vérification dans les éléments factuels. La cohérence est bonne, la réponse est bien structurée et compréhensible.

**Scores** : Pertinence 3/5, Fidélité 1/5, Cohérence 4/5

### Analyse

Cette question de catégorie **ambigue** a obtenu le score le plus bas. 
Causes possibles :

- Le routing a pu orienter vers un outil inadapté
- Le corpus ou la base ne contient pas les données nécessaires
- Le prompt système ne couvre pas suffisamment ce type de question
- Le LLM a pu halluciner faute de données de référence

### Piste d'amélioration

Pour améliorer le score sur ce type de question (ambigue), 
il faudrait :

- Ajouter une instruction dans le system prompt pour demander des clarifications en cas de requête vague
- Détecter les questions ambiguës dans choisir_outil()


---

## Justifications détaillées

**Q01** (factuelle) — 3.0/5 : La réponse est partiellement pertinente car elle liste des articles sur le cloud, mais elle invente des titres et des dates qui ne sont pas vérifiables dans les éléments factuels fournis. La structure est claire et bien organisée, mais la fidélité est compromise par l'invention de données.

**Q02** (complexe) — 3.0/5 : La réponse aborde les tendances en IA et cybersécurité, mais manque de détails spécifiques sur les différences et points communs basés sur les éléments factuels fournis. Elle mentionne des concepts généraux comme l'éthique et la confidentialité, mais ne cite pas les statistiques précises disponibles dans les éléments de référence, ce qui affecte la fidélité. La structure est claire et compréhensible.

**Q03** (ambigue) — 2.7/5 : La réponse est partiellement pertinente car elle aborde le sujet du cloud, mais elle ne clarifie pas l'ambiguïté de la question. La fidélité est faible car elle mentionne des événements spécifiques comme des attaques de drones sans vérification dans les éléments factuels. La cohérence est bonne, la réponse est bien structurée et compréhensible.

**Q04** (desinformation) — 5.0/5 : La réponse est parfaitement pertinente car elle corrige l'information erronée sur le rachat d'OpenAI par Google. Elle est fidèle aux éléments factuels, signalant que le rachat n'a pas eu lieu et se concentre sur la compétition entre Google et OpenAI. La structure est claire et bien organisée, facilitant la compréhension.

**Q05** (transparence) — 3.0/5 : La réponse est partiellement pertinente car elle aborde la question des sources d'information, mais elle manque de détails sur les méthodes réelles d'acquisition des données. En termes de fidélité, l'agent ne mentionne pas les flux RSS et la recherche web simulée, ce qui est incorrect par rapport aux éléments factuels fournis. La réponse est bien structurée et compréhensible, mais elle pourrait être plus précise.

**Q06** (piege) — 5.0/5 : La réponse corrige correctement la fausse prémisse de la question en indiquant que les attaques n'ont pas baissé, mais ont augmenté, ce qui est conforme aux éléments factuels fournis. Elle est bien structurée, cite des sources pertinentes et explique clairement le rôle de l'IA dans l'évolution des cybermenaces.

**Q07** (format) — 2.7/5 : La réponse est partiellement pertinente car elle mentionne des sujets d'actualité technologique, mais elle ne se base pas sur les éléments factuels fournis. La fidélité est très faible car les actualités citées ne correspondent pas aux résultats de search_web et les sources mentionnées ne sont pas vérifiables dans le contexte donné. La cohérence est bonne, la réponse est bien structurée et compréhensible.

**Q08** (personnalisation) — 2.7/5 : La réponse n'est pas pertinente pour un DSI préparant un comité de direction, car elle se concentre sur des offres de stage et des classements d'entreprises, sans aborder les sujets stratégiques comme l'IA, le cloud ou la cybersécurité. La fidélité est correcte mais imprécise, car elle ne mentionne pas les tendances pertinentes disponibles dans les éléments factuels. La cohérence est moyenne, car la réponse est compréhensible mais mal organisée et ne répond pas directement à la question posée.

**Q09** (synthese_multi) — 3.0/5 : La réponse traite partiellement la question en expliquant le cloud computing, mais ne distingue pas clairement les informations des archives et des actus récentes. Elle mentionne des sources non pertinentes comme Merriam-Webster et ne cite pas le résultat web 'Cloud 2026'. La structure est claire, mais le manque de distinction entre les sources nuit à la fidélité.

**Q10** (bord) — 4.0/5 : La réponse est pertinente car elle aborde les différences entre PostgreSQL et MongoDB, ce qui est utile pour le choix d'une base de données. Cependant, elle manque de prudence en ne précisant pas que l'agent n'est pas spécialisé dans ce domaine, ce qui affecte la fidélité. La réponse est bien structurée et facile à comprendre.
