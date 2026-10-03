# Quin model fa servir un Dot (gratuït primer, pro després)

Els Dots parlen amb qualsevol proveïdor que entengui **Chat Completions** (el protocol de OpenAI, que gairebé tothom copia). Passar de gratuït a pro és canviar tres camps: adreça, clau i model. No cal tocar res més.

## Opcions gratuïtes (el que hi havia publicat a l'octubre del 2026; els límits canvien sovint)
| Proveïdor | Límit gratuït aproximat | Nota |
| --- | --- | --- |
| Groq | ~30 peticions/min, ~1.000/dia | Molt ràpid. Pot canviar els models disponibles. |
| Google Gemini | ~15 peticions/min, fins a ~1.500/dia | A fora de la UE, Google pot fer servir les dades per entrenar. |
| OpenRouter | 20/min, 50/dia (1.000/dia si hi poses 10 $) | Només els models acabats en `:free`. |
| Mistral (França) | Crèdit mensual gratuït | Les dades poden servir per entrenar si no ho desactives. |
| Cerebras | ~1 M tokens/dia | |
| **Ollama al teu ordinador** | **Il·limitat** | **100% privat i sense compte.** Cal un ordinador que l'aguanti i que el servidor hi tingui accés. |

Els plans gratuïts són per provar: amb molts usuaris es quedaran curts, i alguns exigeixen no fer-los servir comercialment. Llegeix les condicions abans d'obrir-ho al públic.

## Com es configura
- **Una persona, pel seu compte:** Configuració → *Model provider* → *Proveïdor ràpid*. Tria'n un, enganxa la clau i desa. Cada compte té la seva pròpia clau, i es desa xifrada.
- **Per a tot el servidor** (els comptes que no n'han posat cap): variables d'entorn
  `MODEL_API_BASE_URL`, `MODEL_API_KEY`, `MODEL_WIRE_API=chat`, `DEFAULT_MODEL`.

Exemple gratuït amb Groq:
```
MODEL_WIRE_API=chat
MODEL_API_BASE_URL=https://api.groq.com/openai/v1
MODEL_API_KEY=gsk_...
DEFAULT_MODEL=llama-3.3-70b-versatile
```
Passar a pro: canvia aquestes quatre línies pel proveïdor de pagament (OpenAI, Mistral de pagament, etc.).

## Límits per no gastar de més
Al panell d'admin pots posar un límit diari de tokens per membre. Un pla gratuït compartit per molts membres es gasta ràpid: usa-ho.
