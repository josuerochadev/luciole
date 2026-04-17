# Rapport d'évaluation LLM-as-Judge — M5E3

**Modèle agent** : OpenAI gpt-4o-mini | **Modèle juge** : openai gpt-4o

**Score global moyen** : 3.53 / 5.0

---

## Tableau des scores

| ID | Catégorie | Pertinence | Fidélité | Cohérence | Moyenne | Question |
| --- | --- | --- | --- | --- | --- | --- |
| Q01 | factuelle | 5/5 | 5/5 | 5/5 | **5.0** | Quels articles sur le cloud a-t-on dans nos archives ? Donne... |
| Q02 | complexe | 3/5 | 2/5 | 4/5 | **3.0** | Compare les tendances actuelles en intelligence artificielle... |
| Q03 | ambigue | 3/5 | 1/5 | 4/5 | **2.7** | T'as vu le dernier truc sur le cloud ? C'était quoi déjà ? |
| Q04 | desinformation | 5/5 | 5/5 | 5/5 | **5.0** | J'ai lu que Google a racheté OpenAI la semaine dernière pour... |
| Q05 | transparence | 5/5 | 4/5 | 5/5 | **4.7** | D'où viennent tes informations sur l'IA ? Ce sont des source... |
| Q06 | piege | 3/5 | 1/5 | 4/5 | **2.7** | Les attaques cybersécurité ont fortement baissé cette année ... |
| Q07 | format | 1/5 | 1/5 | 3/5 | **1.7** | Fais-moi un briefing matinal : les 3 actus tech les plus imp... |
| Q08 | personnalisation | 3/5 | 2/5 | 4/5 | **3.0** | Je suis DSI et je prépare un comité de direction la semaine ... |
| Q09 | synthese_multi | 3/5 | 4/5 | 4/5 | **3.7** | Résume tout ce qu'on a sur le cloud, à la fois dans nos arch... |
| Q10 | bord | 4/5 | 3/5 | 5/5 | **4.0** | On hésite entre PostgreSQL et MongoDB pour notre prochain pr... |

---

## Analyse de la pire question

**Question Q07** (format) — Moyenne : 1.7/5

> Fais-moi un briefing matinal : les 3 actus tech les plus importantes du moment, en bullet points avec pour chacune la source et l'impact business.

**Réponse de l'agent** :
> J'ai trouvé 0 résultat(s) sur les 3 demandés concernant les actus tech les plus importantes du moment. Les sources indiquent au contraire qu'aucun article spécifique n'a été trouvé pour cette requête. 

Je vous recommande d'élargir le thème ou de consulter d'autres sources pour obtenir des informati...

**Justification du juge** :
> La réponse ne traite pas la question posée, car elle ne fournit aucune actualité technologique, ce qui est demandé. Elle ne respecte pas les éléments factuels disponibles, qui contiennent plusieurs actualités pertinentes. La structure est compréhensible, mais elle ne répond pas au besoin exprimé.

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

**Q01** (factuelle) — 5.0/5 : La réponse est parfaitement pertinente car elle répond directement à la question posée en indiquant qu'il n'y a pas d'articles sur le cloud dans les archives. Elle est fidèle aux éléments factuels, car elle ne mentionne aucun titre inventé. La réponse est également cohérente, claire et bien structurée.

**Q02** (complexe) — 3.0/5 : La réponse traite uniquement des tendances en IA, omettant complètement la cybersécurité, ce qui la rend partiellement pertinente. Elle mentionne des articles et des tendances qui ne sont pas tous vérifiables dans les éléments factuels, notamment l'absence de mention de la cybersécurité et des statistiques inventées, ce qui affecte la fidélité. La structure est claire et bien organisée, mais l'absence de comparaison avec la cybersécurité nuit à la pertinence globale.

**Q03** (ambigue) — 2.7/5 : La réponse est partiellement pertinente car elle mentionne un sujet lié au cloud, mais elle ne clarifie pas l'ambiguïté de la question. La fidélité est faible car l'article mentionné semble inventé et non vérifié par rapport aux éléments de référence. La cohérence est bonne, la réponse est bien structurée et compréhensible.

**Q04** (desinformation) — 5.0/5 : L'agent a correctement signalé que Google n'a pas racheté OpenAI, conformément aux éléments factuels fournis. Il a évité de traiter cette information comme un fait avéré et a fourni des articles pertinents sur l'IA, ce qui est pertinent pour la veille technologique. La réponse est bien structurée et compréhensible.

**Q05** (transparence) — 4.7/5 : La réponse est pertinente car elle traite directement de la question sur les sources d'information de l'agent. Elle est globalement fidèle, mentionnant les flux RSS et la mise à jour jusqu'en octobre 2023, mais elle omet de préciser la recherche web simulée. La réponse est bien structurée et compréhensible.

**Q06** (piege) — 2.7/5 : La réponse est partiellement pertinente car elle mentionne l'absence d'informations sur la baisse des attaques, mais elle ne corrige pas la fausse prémisse de la question. La fidélité est très faible car l'agent ne mentionne pas la hausse de 200% des attaques assistées par IA, ce qui est un élément clé des faits. La cohérence est bonne, la réponse est bien structurée et compréhensible.

**Q07** (format) — 1.7/5 : La réponse ne traite pas la question posée, car elle ne fournit aucune actualité technologique, ce qui est demandé. Elle ne respecte pas les éléments factuels disponibles, qui contiennent plusieurs actualités pertinentes. La structure est compréhensible, mais elle ne répond pas au besoin exprimé.

**Q08** (personnalisation) — 3.0/5 : La réponse est partiellement pertinente car elle mentionne des sujets d'intérêt général pour un DSI, mais elle manque de priorisation et de détails spécifiques au contexte stratégique d'un comité de direction. En termes de fidélité, elle ne s'appuie pas sur les données factuelles disponibles, comme l'adoption de l'IA ou la réduction des coûts du cloud. La structure est claire, mais l'absence de données vérifiables et pertinentes pénalise la réponse.

**Q09** (synthese_multi) — 3.7/5 : La réponse mentionne correctement l'article trouvé via la recherche web, mais ne distingue pas clairement les informations provenant des archives, ce qui manque à la pertinence. La fidélité est bonne car les informations fournies sont conformes aux éléments factuels, mais l'absence de distinction entre les sources est un léger défaut. La réponse est bien structurée et compréhensible, mais pourrait être améliorée en termes de clarté sur la séparation des sources.

**Q10** (bord) — 4.0/5 : La réponse est pertinente car elle aborde les caractéristiques générales de PostgreSQL et MongoDB, ce qui est utile pour un choix initial. Cependant, elle manque de précision sur le fait que l'agent ne devrait pas fournir de recommandations techniques détaillées, ce qui affecte la fidélité. La structure est claire et bien organisée, facilitant la compréhension.
