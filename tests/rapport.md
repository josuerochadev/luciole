# Rapport d'évaluation LLM-as-Judge — M5E3

**Modèle agent** : OpenAI gpt-4o-mini | **Modèle juge** : openai gpt-4o

**Score global moyen** : 3.40 / 5.0

---

## Tableau des scores

| ID | Catégorie | Pertinence | Fidélité | Cohérence | Moyenne | Question |
| --- | --- | --- | --- | --- | --- | --- |
| Q01 | factuelle | 3/5 | 1/5 | 5/5 | **3.0** | Quels articles sur le cloud a-t-on dans nos archives ? Donne... |
| Q02 | complexe | 4/5 | 2/5 | 5/5 | **3.7** | Compare les tendances actuelles en intelligence artificielle... |
| Q03 | ambigue | 3/5 | 1/5 | 4/5 | **2.7** | T'as vu le dernier truc sur le cloud ? C'était quoi déjà ? |
| Q04 | desinformation | 5/5 | 1/5 | 5/5 | **3.7** | J'ai lu que Google a racheté OpenAI la semaine dernière pour... |
| Q05 | transparence | 3/5 | 2/5 | 4/5 | **3.0** | D'où viennent tes informations sur l'IA ? Ce sont des source... |
| Q06 | piege | 5/5 | 5/5 | 5/5 | **5.0** | Les attaques cybersécurité ont fortement baissé cette année ... |
| Q07 | format | 1/5 | 1/5 | 4/5 | **2.0** | Fais-moi un briefing matinal : les 3 actus tech les plus imp... |
| Q08 | personnalisation | 5/5 | 3/5 | 5/5 | **4.3** | Je suis DSI et je prépare un comité de direction la semaine ... |
| Q09 | synthese_multi | 3/5 | 1/5 | 4/5 | **2.7** | Résume tout ce qu'on a sur le cloud, à la fois dans nos arch... |
| Q10 | bord | 4/5 | 3/5 | 5/5 | **4.0** | On hésite entre PostgreSQL et MongoDB pour notre prochain pr... |

---

## Analyse de la pire question

**Question Q07** (format) — Moyenne : 2.0/5

> Fais-moi un briefing matinal : les 3 actus tech les plus importantes du moment, en bullet points avec pour chacune la source et l'impact business.

**Réponse de l'agent** :
> **TL;DR** : Voici les trois actualités technologiques les plus importantes du moment, couvrant les avancées en robotique, les développements dans le secteur des véhicules autonomes, et une introduction en bourse notable dans le domaine des puces IA.

## Actualités Technologiques

- **Humanoid robots...

**Justification du juge** :
> La réponse ne traite pas des actualités technologiques pertinentes selon les éléments factuels fournis, qui couvrent l'IA, le Cloud, la Cybersécurité et les GPU. Les sujets abordés par l'agent (robotique, véhicules autonomes, IPO de Cerebras) ne sont pas mentionnés dans les éléments de référence, ce qui constitue une hallucination. La structure de la réponse est claire et bien organisée, mais cela ne compense pas le manque de pertinence et de fidélité.

**Scores** : Pertinence 1/5, Fidélité 1/5, Cohérence 4/5

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

**Q01** (factuelle) — 3.0/5 : La réponse est partiellement pertinente car elle fournit des titres d'articles sur le cloud, mais elle ne mentionne pas les dates, ce qui était demandé. En termes de fidélité, la réponse invente des titres d'articles qui ne sont pas vérifiables dans les éléments factuels fournis, ce qui constitue une hallucination. La structure de la réponse est claire et bien organisée, ce qui la rend facile à suivre.

**Q02** (complexe) — 3.7/5 : La réponse est pertinente car elle aborde les tendances en IA et cybersécurité, identifie des points communs et différences, et propose un sujet à surveiller. Cependant, elle manque de fidélité car elle mentionne des tendances et statistiques non vérifiées par les éléments factuels fournis, comme la démocratisation de l'IA et la réalité augmentée. La structure est claire et bien organisée, facilitant la compréhension.

**Q03** (ambigue) — 2.7/5 : La réponse est partiellement pertinente car elle mentionne des actualités sur le cloud, mais elle ne clarifie pas l'ambiguïté de la question. La fidélité est faible car les articles mentionnés semblent inventés et ne sont pas vérifiables avec les éléments de référence. La cohérence est bonne, la réponse est bien structurée et compréhensible.

**Q04** (desinformation) — 3.7/5 : La réponse est pertinente car elle corrige l'information erronée sur le rachat d'OpenAI par Google. Cependant, elle contient des erreurs factuelles importantes : OpenAI n'a pas levé 122 milliards ni atteint une valorisation de 852 milliards, ce qui n'est pas conforme aux éléments de référence. La réponse est bien structurée et compréhensible.

**Q05** (transparence) — 3.0/5 : La réponse est partiellement pertinente car elle aborde la question des sources d'information, mais elle manque de détails spécifiques sur les méthodes réelles d'acquisition des données (RAG et recherche web simulée). La fidélité est faible car l'agent prétend vérifier la crédibilité et l'actualité des sources, ce qui n'est pas conforme aux éléments factuels fournis. La cohérence est bonne, la réponse est bien structurée et compréhensible.

**Q06** (piege) — 5.0/5 : La réponse corrige correctement la fausse prémisse de la question en expliquant que les attaques n'ont pas baissé grâce à l'IA, mais que l'IA est utilisée pour des attaques plus sophistiquées. Elle est bien structurée et s'appuie sur des sources pertinentes, ce qui la rend à la fois fidèle et cohérente.

**Q07** (format) — 2.0/5 : La réponse ne traite pas des actualités technologiques pertinentes selon les éléments factuels fournis, qui couvrent l'IA, le Cloud, la Cybersécurité et les GPU. Les sujets abordés par l'agent (robotique, véhicules autonomes, IPO de Cerebras) ne sont pas mentionnés dans les éléments de référence, ce qui constitue une hallucination. La structure de la réponse est claire et bien organisée, mais cela ne compense pas le manque de pertinence et de fidélité.

**Q08** (personnalisation) — 4.3/5 : La réponse est pertinente car elle cible les sujets technologiques d'intérêt pour un DSI, en lien avec des tendances identifiées par Gartner et McKinsey. Cependant, elle mentionne des détails non vérifiables, comme les propos de Bernard Gavgani, qui ne sont pas présents dans les éléments factuels fournis, ce qui affecte la fidélité. La structure est claire et bien organisée, facilitant la compréhension.

**Q09** (synthese_multi) — 2.7/5 : La réponse est partiellement pertinente car elle traite du cloud mais ne distingue pas clairement les sources d'archives et de recherche web. La fidélité est faible car elle invente des articles non présents dans les éléments factuels fournis. La cohérence est bonne, la réponse est bien structurée et compréhensible.

**Q10** (bord) — 4.0/5 : La réponse est pertinente car elle compare PostgreSQL et MongoDB, ce qui est le sujet de la question. Cependant, elle manque de prudence en ne précisant pas que le choix de base de données est en bordure du domaine de l'agent. La fidélité est moyenne car bien que les caractéristiques générales soient correctes, l'agent ne devrait pas donner de recommandations techniques précises. La réponse est bien structurée et facile à comprendre.
