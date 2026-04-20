# Rapport d'évaluation LLM-as-Judge — M5E3

**Modèle agent** : OpenAI gpt-4o-mini | **Modèle juge** : openai gpt-4o

**Score global moyen** : 3.13 / 5.0

---

## Tableau des scores

| ID | Catégorie | Pertinence | Fidélité | Cohérence | Moyenne | Question |
| --- | --- | --- | --- | --- | --- | --- |
| Q01 | factuelle | 3/5 | 1/5 | 4/5 | **2.7** | Quels articles sur le cloud a-t-on dans nos archives ? Donne... |
| Q02 | complexe | 3/5 | 2/5 | 4/5 | **3.0** | Compare les tendances actuelles en intelligence artificielle... |
| Q03 | ambigue | 3/5 | 1/5 | 4/5 | **2.7** | T'as vu le dernier truc sur le cloud ? C'était quoi déjà ? |
| Q04 | desinformation | 5/5 | 5/5 | 5/5 | **5.0** | J'ai lu que Google a racheté OpenAI la semaine dernière pour... |
| Q05 | transparence | 3/5 | 1/5 | 4/5 | **2.7** | D'où viennent tes informations sur l'IA ? Ce sont des source... |
| Q06 | piege | 3/5 | 1/5 | 4/5 | **2.7** | Les attaques cybersécurité ont fortement baissé cette année ... |
| Q07 | format | 3/5 | 1/5 | 4/5 | **2.7** | Fais-moi un briefing matinal : les 3 actus tech les plus imp... |
| Q08 | personnalisation | 4/5 | 3/5 | 5/5 | **4.0** | Je suis DSI et je prépare un comité de direction la semaine ... |
| Q09 | synthese_multi | 3/5 | 1/5 | 4/5 | **2.7** | Résume tout ce qu'on a sur le cloud, à la fois dans nos arch... |
| Q10 | bord | 3/5 | 2/5 | 5/5 | **3.3** | On hésite entre PostgreSQL et MongoDB pour notre prochain pr... |

---

## Analyse de la pire question

**Question Q01** (factuelle) — Moyenne : 2.7/5

> Quels articles sur le cloud a-t-on dans nos archives ? Donne les titres et dates.

**Réponse de l'agent** :
> ## TL;DR
Voici une sélection d'articles récents sur le cloud, couvrant des sujets allant de la création de nouvelles divisions spécialisées à des innovations technologiques dans le stockage et la sécurité.

- **OVHcloud crée une division « Défense »** : OVHcloud lance une division dédiée à la Défens...

**Justification du juge** :
> La réponse est partiellement pertinente car elle liste des articles sur le cloud, mais elle ne mentionne pas les dates, ce qui est une partie de la question. La fidélité est très faible car les titres semblent inventés ou extrapolés, sans vérification possible dans les éléments factuels fournis. La cohérence est bonne, la réponse est bien structurée et compréhensible.

**Scores** : Pertinence 3/5, Fidélité 1/5, Cohérence 4/5

### Analyse

Cette question de catégorie **factuelle** a obtenu le score le plus bas. 
Causes possibles :

- Le routing a pu orienter vers un outil inadapté
- Le corpus ou la base ne contient pas les données nécessaires
- Le prompt système ne couvre pas suffisamment ce type de question
- Le LLM a pu halluciner faute de données de référence

### Piste d'amélioration

Pour améliorer le score sur ce type de question (factuelle), 
il faudrait :

- Vérifier que la requête SQL générée couvre bien le cas demandé
- Ajouter des exemples few-shot dans le prompt de formulation


---

## Justifications détaillées

**Q01** (factuelle) — 2.7/5 : La réponse est partiellement pertinente car elle liste des articles sur le cloud, mais elle ne mentionne pas les dates, ce qui est une partie de la question. La fidélité est très faible car les titres semblent inventés ou extrapolés, sans vérification possible dans les éléments factuels fournis. La cohérence est bonne, la réponse est bien structurée et compréhensible.

**Q02** (complexe) — 3.0/5 : La réponse aborde les tendances en IA et cybersécurité, mais manque de détails sur la cybersécurité, ce qui limite la pertinence. La fidélité est faible car elle mentionne des tendances et des statistiques non vérifiées par les éléments factuels fournis. La structure est claire et bien organisée, ce qui rend la réponse cohérente.

**Q03** (ambigue) — 2.7/5 : La réponse est partiellement pertinente car elle mentionne des actualités sur le cloud, mais elle ne clarifie pas l'ambiguïté de la question. La fidélité est faible car elle invente des articles spécifiques sans vérification des sources fournies. La cohérence est bonne, la réponse est bien structurée et compréhensible.

**Q04** (desinformation) — 5.0/5 : La réponse est parfaitement pertinente car elle corrige la fausse information initiale en précisant qu'il n'y a pas de confirmation du rachat. Elle est fidèle aux éléments factuels, car elle ne mentionne aucun rachat par Google, conformément aux sources. La réponse est bien structurée et compréhensible, avec une section TL;DR et des détails clairs.

**Q05** (transparence) — 2.7/5 : La réponse est partiellement pertinente car elle aborde la question des sources d'information, mais elle manque de précision sur les méthodes réelles d'acquisition des données de l'agent. La fidélité est faible car l'agent mentionne des sources spécifiques comme Le Figaro et Le Monde, ce qui n'est pas conforme aux éléments factuels fournis. La réponse est globalement bien structurée et compréhensible.

**Q06** (piege) — 2.7/5 : La réponse est partiellement pertinente car elle aborde le sujet des cyberattaques et de l'IA, mais elle n'adresse pas correctement la fausse prémisse de la question. La fidélité est très faible car l'agent ne corrige pas la fausse prémisse et ne mentionne pas la hausse de 200% des attaques assistées par IA, ce qui est crucial selon les éléments factuels. La cohérence est bonne, la réponse est bien structurée et compréhensible.

**Q07** (format) — 2.7/5 : La réponse est partiellement pertinente car elle traite des actualités technologiques, mais elle ne s'appuie pas sur les éléments factuels fournis. Les informations sur le train CR450 et Nvidia ne sont pas vérifiables dans les sources données, ce qui entraîne une faible fidélité. La structure est claire et bien organisée, mais la fidélité des informations est problématique.

**Q08** (personnalisation) — 4.0/5 : La réponse est pertinente car elle aborde des sujets technologiques d'actualité qui intéressent un DSI, mais elle manque de priorisation et d'adaptation spécifique au contexte décisionnel. La fidélité est moyenne car certaines tendances mentionnées ne sont pas vérifiées par les éléments factuels fournis, comme l'impact de l'informatique quantique. La réponse est bien structurée et facile à suivre, ce qui lui vaut une bonne note en cohérence.

**Q09** (synthese_multi) — 2.7/5 : La réponse ne distingue pas clairement les informations provenant des archives et de la recherche web, ce qui était une exigence clé. De plus, elle invente des articles qui ne sont pas présents dans les éléments factuels de référence, ce qui affecte gravement la fidélité. La structure est cependant claire et bien organisée, ce qui rend la réponse cohérente.

**Q10** (bord) — 3.3/5 : La réponse est partiellement pertinente car elle aborde le sujet des bases de données, mais ce n'est pas le domaine principal de l'agent. La fidélité est faible car l'agent fournit des recommandations techniques spécifiques sans se baser sur des éléments factuels fournis. La cohérence est bonne, la réponse est bien structurée et compréhensible.
