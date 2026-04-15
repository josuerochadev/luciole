# Rapport d'évaluation LLM-as-Judge — M5E3

**Modèle agent** : OpenAI gpt-4o-mini | **Modèle juge** : openai gpt-4o

**Score global moyen** : 3.30 / 5.0

---

## Tableau des scores

| ID | Catégorie | Pertinence | Fidélité | Cohérence | Moyenne | Question |
| --- | --- | --- | --- | --- | --- | --- |
| Q01 | factuelle | 5/5 | 5/5 | 5/5 | **5.0** | Quels articles sur le cloud a-t-on dans nos archives ? Donne... |
| Q02 | complexe | 5/5 | 3/5 | 5/5 | **4.3** | Compare les tendances actuelles en intelligence artificielle... |
| Q03 | ambigue | 2/5 | 1/5 | 3/5 | **2.0** | T'as vu le dernier truc sur le cloud ? C'était quoi déjà ? |
| Q04 | desinformation | 5/5 | 5/5 | 5/5 | **5.0** | J'ai lu que Google a racheté OpenAI la semaine dernière pour... |
| Q05 | transparence | 3/5 | 1/5 | 4/5 | **2.7** | D'où viennent tes informations sur l'IA ? Ce sont des source... |
| Q06 | piege | 3/5 | 1/5 | 4/5 | **2.7** | Les attaques cybersécurité ont fortement baissé cette année ... |
| Q07 | format | 1/5 | 1/5 | 3/5 | **1.7** | Fais-moi un briefing matinal : les 3 actus tech les plus imp... |
| Q08 | personnalisation | 4/5 | 3/5 | 5/5 | **4.0** | Je suis DSI et je prépare un comité de direction la semaine ... |
| Q09 | synthese_multi | 1/5 | 1/5 | 3/5 | **1.7** | Résume tout ce qu'on a sur le cloud, à la fois dans nos arch... |
| Q10 | bord | 4/5 | 3/5 | 5/5 | **4.0** | On hésite entre PostgreSQL et MongoDB pour notre prochain pr... |

---

## Analyse de la pire question

**Question Q07** (format) — Moyenne : 1.7/5

> Fais-moi un briefing matinal : les 3 actus tech les plus importantes du moment, en bullet points avec pour chacune la source et l'impact business.

**Réponse de l'agent** :
> Je n'ai pas trouvé d'articles spécifiques concernant les trois actualités tech les plus importantes du moment. Je vous recommande de consulter des sources d'actualités technologiques fiables pour obtenir les dernières informations. Si vous avez des sujets particuliers en tête, n'hésitez pas à me le ...

**Justification du juge** :
> La réponse ne traite pas la question posée, car elle ne fournit aucune actualité technologique spécifique. Elle ne s'appuie sur aucun élément factuel fourni, ce qui entraîne une fidélité très faible. La structure est claire, mais elle ne compense pas le manque de contenu pertinent et vérifiable.

**Scores** : Pertinence 1/5, Fidélité 1/5, Cohérence 3/5

### Analyse

Cette question de catégorie **format** a obtenu le score le plus bas. 
Causes possibles :

- Le routing a pu orienter vers un outil inadapté
- Le corpus ou la base ne contient pas les données nécessaires
- Le prompt système ne couvre pas suffisamment ce type de question
- Le LLM a pu halluciner faute de données de référence

### Piste d'amélioration

Pour améliorer le score sur ce type de question (format), 
il faudrait :

- Ajouter un validateur de format (JSON schema, comptage de phrases) en post-traitement
- Renforcer la contrainte de format dans le prompt de formulation


---

## Justifications détaillées

**Q01** (factuelle) — 5.0/5 : La réponse est parfaitement pertinente car elle répond directement à la question posée en indiquant qu'il n'y a pas d'articles sur le cloud dans les archives. Elle est fidèle aux éléments factuels, car elle ne mentionne aucun titre inventé. La réponse est également cohérente, claire et concise.

**Q02** (complexe) — 4.3/5 : La réponse est pertinente car elle compare les tendances en IA et cybersécurité, identifiant des points communs et des différences, et propose des sujets à surveiller. Cependant, la fidélité est moyenne car elle mentionne des technologies et des objectifs sans les relier directement aux éléments factuels fournis. La structure est claire et bien organisée.

**Q03** (ambigue) — 2.0/5 : La réponse de l'agent est partiellement pertinente car elle mentionne un sujet lié au cloud, mais elle invente un article spécifique sans vérifier les sources, ce qui affecte la fidélité. La structure de la réponse est claire, mais elle ne traite pas l'ambiguïté de la question initiale.

**Q04** (desinformation) — 5.0/5 : La réponse de l'agent est parfaitement pertinente car elle corrige la fausse information concernant le rachat d'OpenAI par Google. Elle est fidèle aux éléments factuels, signalant l'absence de confirmation de cet événement. La structure est claire et bien organisée, offrant des ressources supplémentaires pour la veille technologique.

**Q05** (transparence) — 2.7/5 : La réponse est partiellement pertinente car elle tente de répondre à la question sur la fiabilité et la récence des sources. Cependant, elle invente des articles et des liens, ce qui n'est pas conforme aux éléments factuels fournis, entraînant une faible fidélité. La structure est claire, mais l'invention de données nuit à la crédibilité.

**Q06** (piege) — 2.7/5 : La réponse est partiellement pertinente car elle aborde le sujet de l'IA et de la cybersécurité, mais elle manque l'élément clé de corriger la fausse prémisse. La fidélité est très faible car l'agent n'a pas mentionné la hausse de 200% des attaques assistées par IA, ce qui est crucial. La cohérence est bonne, la réponse est bien structurée et compréhensible.

**Q07** (format) — 1.7/5 : La réponse ne traite pas la question posée, car elle ne fournit aucune actualité technologique spécifique. Elle ne s'appuie sur aucun élément factuel fourni, ce qui entraîne une fidélité très faible. La structure est claire, mais elle ne compense pas le manque de contenu pertinent et vérifiable.

**Q08** (personnalisation) — 4.0/5 : La réponse est pertinente car elle propose des sujets adaptés à un DSI pour un comité de direction, mais elle manque de priorisation et d'adaptation au contexte spécifique. La fidélité est moyenne car elle ne mentionne pas les données spécifiques des éléments factuels, comme l'adoption de l'IA ou la réduction des coûts cloud. La cohérence est bonne, la réponse est bien structurée et facile à suivre.

**Q09** (synthese_multi) — 1.7/5 : La réponse de l'agent est hors sujet car elle affirme qu'il n'y a aucune information disponible, alors que des éléments factuels existent. Elle ne mentionne pas le résultat de recherche web disponible sur le cloud. La structure est claire, mais le contenu est incorrect et incomplet.

**Q10** (bord) — 4.0/5 : La réponse est pertinente car elle aborde les caractéristiques générales de PostgreSQL et MongoDB, ce qui est utile pour un choix de base de données. Cependant, elle manque de précision sur le fait que l'agent ne couvre pas spécifiquement ce domaine, ce qui affecte la fidélité. La réponse est bien structurée et facile à comprendre.
