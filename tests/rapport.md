# Rapport d'évaluation LLM-as-Judge — M5E3

**Modèle agent** : OpenAI gpt-4o-mini | **Modèle juge** : openai gpt-4o

**Score global moyen** : 3.57 / 5.0

---

## Tableau des scores

| ID | Catégorie | Pertinence | Fidélité | Cohérence | Moyenne | Question |
| --- | --- | --- | --- | --- | --- | --- |
| Q01 | factuelle | 5/5 | 5/5 | 5/5 | **5.0** | Quels articles sur le cloud a-t-on dans nos archives ? Donne... |
| Q02 | complexe | 5/5 | 3/5 | 5/5 | **4.3** | Compare les tendances actuelles en intelligence artificielle... |
| Q03 | ambigue | 3/5 | 1/5 | 4/5 | **2.7** | T'as vu le dernier truc sur le cloud ? C'était quoi déjà ? |
| Q04 | desinformation | 5/5 | 5/5 | 5/5 | **5.0** | J'ai lu que Google a racheté OpenAI la semaine dernière pour... |
| Q05 | transparence | 5/5 | 3/5 | 5/5 | **4.3** | D'où viennent tes informations sur l'IA ? Ce sont des source... |
| Q06 | piege | 5/5 | 1/5 | 4/5 | **3.3** | Les attaques cybersécurité ont fortement baissé cette année ... |
| Q07 | format | 1/5 | 1/5 | 3/5 | **1.7** | Fais-moi un briefing matinal : les 3 actus tech les plus imp... |
| Q08 | personnalisation | 3/5 | 2/5 | 4/5 | **3.0** | Je suis DSI et je prépare un comité de direction la semaine ... |
| Q09 | synthese_multi | 3/5 | 3/5 | 3/5 | **3.0** | Résume tout ce qu'on a sur le cloud, à la fois dans nos arch... |
| Q10 | bord | 3/5 | 2/5 | 5/5 | **3.3** | On hésite entre PostgreSQL et MongoDB pour notre prochain pr... |

---

## Analyse de la pire question

**Question Q07** (format) — Moyenne : 1.7/5

> Fais-moi un briefing matinal : les 3 actus tech les plus importantes du moment, en bullet points avec pour chacune la source et l'impact business.

**Réponse de l'agent** :
> Il semble qu'aucun article spécifique n'ait été trouvé concernant les "3 actus tech les plus importantes du moment" dans la base simulée. Par conséquent, je ne peux pas fournir de briefing matinal sur ce sujet.

Si vous avez d'autres requêtes ou si vous souhaitez explorer un thème particulier (comme...

**Justification du juge** :
> La réponse ne traite pas la question posée, car elle n'identifie pas les 3 actus tech importantes parmi les éléments factuels fournis. Elle ne fournit aucune information vérifiable ou conforme aux éléments de référence, ce qui entraîne une fidélité très faible. La structure est claire, mais cela ne compense pas le manque de contenu pertinent et factuel.

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

**Q01** (factuelle) — 5.0/5 : La réponse est parfaitement pertinente car elle répond directement à la question posée. Elle est fidèle aux éléments de référence, indiquant qu'aucun article sur le cloud n'est présent dans les archives, ce qui est conforme si l'index est effectivement vide. La réponse est également cohérente, claire et bien structurée.

**Q02** (complexe) — 4.3/5 : La réponse est pertinente car elle compare les tendances en IA et cybersécurité, identifiant des points communs et des différences. Cependant, elle mentionne des statistiques non vérifiées, comme l'adoption de 60% dans l'IT, ce qui affecte la fidélité. La structure est claire et bien organisée.

**Q03** (ambigue) — 2.7/5 : La réponse est partiellement pertinente car elle aborde le sujet du cloud, mais elle ne clarifie pas l'ambiguïté de la question. La fidélité est faible car l'article mentionné semble inventé et ne correspond pas aux éléments factuels fournis. La cohérence est bonne, la réponse est bien structurée et compréhensible.

**Q04** (desinformation) — 5.0/5 : La réponse de l'agent est parfaitement pertinente car elle corrige la fausse information concernant le rachat d'OpenAI par Google. Elle est fidèle aux éléments factuels, signalant l'absence de confirmation de cet événement. La structure est claire et bien organisée, rendant la réponse facile à comprendre.

**Q05** (transparence) — 4.3/5 : La réponse est pertinente car elle traite directement la question posée sur les sources d'information de l'agent. Cependant, elle mentionne une 'base de données interne' sans préciser qu'il s'agit d'un index d'embeddings, ce qui est une imprécision par rapport aux éléments factuels. La structure de la réponse est claire et bien organisée.

**Q06** (piege) — 3.3/5 : La réponse est pertinente car elle aborde directement la question posée. Cependant, elle échoue en fidélité car elle ne corrige pas la fausse prémisse et ne mentionne pas la hausse de 200% des attaques assistées par IA, ce qui est crucial. La structure est globalement claire, mais l'absence de correction de la prémisse nuit à la compréhension globale.

**Q07** (format) — 1.7/5 : La réponse ne traite pas la question posée, car elle n'identifie pas les 3 actus tech importantes parmi les éléments factuels fournis. Elle ne fournit aucune information vérifiable ou conforme aux éléments de référence, ce qui entraîne une fidélité très faible. La structure est claire, mais cela ne compense pas le manque de contenu pertinent et factuel.

**Q08** (personnalisation) — 3.0/5 : La réponse est partiellement pertinente car elle propose des sujets généraux mais manque de priorisation et d'adaptation au contexte DSI/comdir. La fidélité est faible car elle ne mentionne pas les données spécifiques disponibles, comme l'adoption de l'IA ou les coûts du cloud. La cohérence est bonne, la réponse est bien structurée et compréhensible.

**Q09** (synthese_multi) — 3.0/5 : La réponse mentionne correctement une source récente avec des détails précis, mais elle ne distingue pas les informations provenant des archives (RAG) de celles de la recherche web, ce qui est demandé. De plus, la mention d'une évaluation de pertinence à 8/10 est hors contexte et non pertinente. La structure est simple mais manque de clarté sur la séparation des sources.

**Q10** (bord) — 3.3/5 : La réponse est partiellement pertinente car elle traite de la comparaison entre PostgreSQL et MongoDB, mais elle ne reconnaît pas que le choix de base de données est en bordure du domaine de l'agent. La fidélité est faible car l'agent fournit des recommandations techniques précises sans se baser sur des sources vérifiables. La réponse est bien structurée et facile à suivre.
