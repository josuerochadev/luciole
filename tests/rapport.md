# Rapport d'évaluation LLM-as-Judge — M5E3

**Modèle agent** : OpenAI gpt-4o-mini | **Modèle juge** : openai gpt-4o

**Score global moyen** : 3.92 / 5.0

---

## Tableau des scores

| ID | Catégorie | Pertinence | Fidélité | Cohérence | Moyenne | Question |
| --- | --- | --- | --- | --- | --- | --- |
| Q01 | format | 1/5 | 1/5 | 3/5 | **1.7** | Fais-moi un résumé structuré des tendances technologiques ac... |
| Q02 | complexe | 5/5 | 5/5 | 5/5 | **5.0** | Explique à quelqu'un qui n'y connaît rien en informatique ce... |
| Q03 | complexe | 5/5 | 2/5 | 5/5 | **4.0** | Compare les tendances actuelles en intelligence artificielle... |
| Q04 | ambigue | 5/5 | 5/5 | 5/5 | **5.0** | Parle-moi du truc là, tu sais, le machin avec les données. |
| Q05 | complexe | 4/5 | 3/5 | 4/5 | **3.7** | L'IA va-t-elle remplacer tous les développeurs d'ici 2 ans ? |
| Q06 | format | 5/5 | 3/5 | 5/5 | **4.3** | Donne-moi un tableau comparatif des domaines IA, Cloud et Cy... |
| Q07 | piege | 5/5 | 5/5 | 5/5 | **5.0** | Tu confirmes que nous avons 15 clients Standard dans la base... |
| Q08 | format | 5/5 | 2/5 | 5/5 | **4.0** | Liste les clients Premium au format JSON avec les champs nom... |
| Q09 | multi_tools | 1/5 | 1/5 | 3/5 | **1.7** | Quelles sont les dernières nouvelles sur Kubernetes et le cl... |
| Q10 | bord | 5/5 | 5/5 | 5/5 | **5.0** | Qu'est-ce que le framework Svelte et devrait-on l'adopter po... |
| Q11 | format | 5/5 | 2/5 | 5/5 | **4.0** | Je dois présenter les tendances IA à mon directeur qui a 5 m... |
| Q12 | format | 5/5 | 1/5 | 5/5 | **3.7** | Résume en exactement 3 phrases les tendances IA actuelles. |

---

## Analyse de la pire question

**Question Q01** (format) — Moyenne : 1.7/5

> Fais-moi un résumé structuré des tendances technologiques actuelles en 5 bullet points maximum.

**Réponse de l'agent** :
> Actuellement, aucun article spécifique n'a été trouvé concernant les tendances technologiques actuelles. Je vous recommande de vérifier d'autres sources ou de reformuler votre recherche pour obtenir des résultats pertinents. Si vous avez d'autres questions ou un sujet spécifique en tête, n'hésitez p...

**Justification du juge** :
> La réponse ne traite pas la question posée, qui demandait un résumé structuré des tendances technologiques actuelles. Elle ne fait pas référence aux éléments factuels fournis, tels que les LLMs en 2026 ou la cybersécurité IA +200%. La structure est claire mais ne répond pas à la demande.

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

**Q01** (format) — 1.7/5 : La réponse ne traite pas la question posée, qui demandait un résumé structuré des tendances technologiques actuelles. Elle ne fait pas référence aux éléments factuels fournis, tels que les LLMs en 2026 ou la cybersécurité IA +200%. La structure est claire mais ne répond pas à la demande.

**Q02** (complexe) — 5.0/5 : La réponse est parfaitement ciblée, expliquant clairement ce que sont les LLMs et leur importance, sans utiliser de jargon technique. Elle est fidèle aux éléments factuels, ne contenant aucune donnée inventée ou statistique non vérifiée. La structure est limpide et facile à suivre, rendant le sujet accessible à un néophyte.

**Q03** (complexe) — 4.0/5 : La réponse est pertinente car elle compare les tendances en IA et cybersécurité, soulignant l'adoption croissante et l'automatisation. Cependant, elle mentionne des modèles comme 'GPT-5' et 'Gemini Ultra 2', qui ne sont pas vérifiables dans les éléments factuels fournis, ce qui affecte la fidélité. La structure est claire et bien organisée.

**Q04** (ambigue) — 5.0/5 : L'agent a correctement identifié que la question était vague et a demandé des précisions, ce qui est pertinent. La réponse est fidèle aux éléments factuels, car elle ne fait pas d'hypothèses non fondées. La structure est claire et bien organisée, facilitant la compréhension.

**Q05** (complexe) — 3.7/5 : La réponse est pertinente car elle aborde l'impact de l'IA sur le développement, mais elle ne traite pas directement de la question du remplacement total des développeurs. La fidélité est moyenne car elle mentionne des articles qui ne sont pas vérifiables et ne sont pas directement liés à la question. La cohérence est bonne, la réponse est bien structurée et compréhensible, mais l'évaluation de la pertinence des articles est confuse.

**Q06** (format) — 4.3/5 : La réponse est pertinente car elle fournit un tableau comparatif structuré des domaines demandés. Cependant, la fidélité est moyenne car certaines tendances mentionnées, comme la migration vers des solutions multi-cloud, ne sont pas directement tirées des éléments factuels fournis. La cohérence est excellente, la réponse est bien organisée et facile à suivre.

**Q07** (piege) — 5.0/5 : La réponse de l'agent est parfaitement pertinente car elle corrige la fausse prémisse de la question. Elle est fidèle aux éléments factuels, indiquant correctement qu'il n'y a qu'un seul client Standard, Bob Dupont. La réponse est également cohérente, claire et bien structurée.

**Q08** (format) — 4.0/5 : La réponse est pertinente car elle fournit un JSON avec les clients Premium demandés. Cependant, la fidélité est faible car les emails sont masqués, ce qui ne correspond pas aux éléments factuels fournis. La structure est claire et bien organisée.

**Q09** (multi_tools) — 1.7/5 : La réponse ne traite pas correctement la question posée, car elle ne mentionne aucune information pertinente sur Kubernetes ou le cloud, malgré la disponibilité d'un résultat web. Elle échoue à distinguer les sources d'information et ne respecte pas les éléments factuels fournis. La structure est compréhensible mais manque de contenu pertinent.

**Q10** (bord) — 5.0/5 : La réponse est pertinente car elle reconnaît que le sujet Svelte est en dehors du domaine de l'agent. Elle est fidèle aux éléments factuels, car elle ne fournit pas d'informations inventées ou incorrectes. La réponse est cohérente, bien structurée et facile à comprendre.

**Q11** (format) — 4.0/5 : La réponse est pertinente car elle fournit trois phrases percutantes adaptées à un public dirigeant. Cependant, la fidélité est faible car elle mentionne des modèles comme 'GPT-5' et 'Gemini Ultra 2' qui ne sont pas confirmés par les éléments factuels, et le chiffre de 60% d'adoption de l'IA générative n'est pas vérifiable. La cohérence est bonne, les phrases sont bien structurées et compréhensibles.

**Q12** (format) — 3.7/5 : La réponse est pertinente car elle traite des tendances actuelles en IA en trois phrases, comme demandé. Cependant, elle mentionne des modèles spécifiques comme GPT-5 et Gemini Ultra 2, ainsi qu'une statistique d'adoption de l'IA générative qui ne sont pas vérifiables dans les éléments factuels fournis, ce qui affecte la fidélité. La structure est claire et bien organisée, rendant la réponse facile à suivre.
