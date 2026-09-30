# Mode automàtic: un número, el Dot adequat

Una connexió de WhatsApp pot funcionar en **mode automàtic**: la persona escriu el seu dubte i el sistema tria el Dot adequat del catàleg (88 Dots) sense que ella hagi de saber quin existeix.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/whatsapp/connections \
  -H 'Content-Type: application/json' --cookie "<sessió>" \
  -d '{"auto_route": true, "phone_number_id": "…", "access_token": "…", "app_secret": "…", "allowed_numbers": ["+34…"]}'
```
(Amb `bot_id` d'un Dot concret la connexió continua funcionant com abans.)

## Com tria el Dot
- Enrutament **gratuït i immediat**: no fa cap crida al model. Compara el missatge amb el nom, el rol, l'especialitat, les tasques i els exemples de cada Dot (ponderant més les paraules poc habituals) i entén sinònims quotidians («cisterna», «renda», «lloguer»…).
- **Enganxós**: dins d'una conversa es queda amb el mateix Dot i només en canvia si el missatge apunta clarament a un altre tema. Quan canvia, ho diu («🚰 Fontaner:»).
- Si el missatge és massa vague («hola»), respon amb una pregunta d'aclariment o la benvinguda **sense gastar tokens**.
- L'API `GET /api/v1/catalog/route?q=…` retorna els 3 Dots més adients per a un text (per a un futur «quin Dot necessito?» a la web).

## Ordres per a la persona
| Ordre | Què fa |
| --- | --- |
| `/ajuda` | Mostra les ordres |
| `/dots` | Alguns Dots que la poden ajudar |
| `/tria <nom>` | Parlar amb un Dot concret |
| `/auto` | Torna a la tria automàtica |
| `/memoria` | Mostra què recorda de la persona |
| `/oblida` | Esborra tot el que sap de la persona |

## Memòria per persona
- Guarda uns quants fets que la persona ha dit (nom, ciutat, fills, feina, idioma) i els passa al Dot perquè no calgui repetir-los. Màxim 20, de 160 caràcters.
- **Captura automàtica només de dades innòcues.** Salut, religió, política, diners o documents d'identitat no es guarden mai sols; només si la persona ho demana explícitament: «recorda que sóc al·lèrgic a la penicil·lina».
- La persona ho veu (`/memoria`) i ho esborra (`/oblida`) quan vulgui. El missatge de benvinguda ho explica.
- Guardat a SQLite (`contact_memory`, `contact_state`), separat per propietari de la connexió. Amb RGPD, cal afegir-ho a la política de privacitat i eliminar-ho a petició.

## Límits actuals
- L'enrutament és per paraules clau: no entén ironia ni temes molt nous. La millora natural és un conjunt d'avaluació amb preguntes reals i, si cal, un segon pas amb un model petit només quan la confiança és baixa.
- Encara no hi ha interfície a la web per crear una connexió automàtica; es fa per l'API.
- Per a un únic número compartit entre molts usuaris (sense llista de números permesos) cal el pas d'infraestructura descrit a la conversa: comptes automàtics per número, cua i Postgres.
