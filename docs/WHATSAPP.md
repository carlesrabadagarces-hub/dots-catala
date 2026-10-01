# Connectar un agent a WhatsApp

Cada persona connecta el **seu propi número** mitjançant l'API oficial *WhatsApp Cloud API* de Meta. No es fa servir cap API no oficial.

## Requisits
1. Un compte a [Meta for Developers](https://developers.facebook.com) amb una app de tipus *Business* i el producte **WhatsApp** afegit.
2. Un número (el de prova de Meta o el teu) i, d'aquí: el **Phone number ID**, un **access token** i l'**App secret** (Settings → Basic).
3. Una URL pública HTTPS cap al servidor (p. ex. `cloudflared tunnel --url http://127.0.0.1:8000` o `ngrok http 8000`).

## Passos
1. Arrenca Open Dots i crea un agent (nom, instruccions, model).
2. Registra la connexió (API autenticada; obre `/docs` al servidor):
   ```
   POST /api/v1/whatsapp/connections
   {"bot_id": "bot-xxxxxx", "label": "El meu WhatsApp",
    "phone_number_id": "...", "access_token": "...", "app_secret": "...",
    "allowed_numbers": ["+34600111222"]}
   ```
   La resposta inclou `id` i `verify_token`.
3. A Meta → WhatsApp → Configuration → Webhook:
   - Callback URL: `https://LA-TEVA-URL/api/v1/whatsapp/webhook/<id>`
   - Verify token: el `verify_token` rebut
   - Subscriu el camp **messages**.
4. Envia un missatge des d'un número de `allowed_numbers`: l'agent respon.

## Seguretat
- `access_token` i `app_secret` es guarden xifrats i mai es tornen a mostrar.
- El webhook comprova la signatura `X-Hub-Signature-256` amb l'app secret.
- **Llista blanca obligatòria**: només responen els números de `allowed_numbers` (si és buida, no respon a ningú).
- Les ordres d'eines (`/search`, `/connector`, accions del workspace) no s'executen des de WhatsApp perquè requereixen aprovació a la interfície web.
- Cada remitent té el seu propi fil de conversa (`<connection_id>:<número>`).

## Gestió
`GET/PUT/DELETE /api/v1/whatsapp/connections[/{id}]` (`enabled`, `allowed_numbers`, canviar d'agent, rotar credencials).

## Fiabilitat de les entregues
Meta espera un `2xx` en 5 segons i, si no, reenvia el mateix missatge fins a 7 vegades.
- **Cada entrega s'atén una sola vegada.** El registre del que ja s'ha atès és a la base de dades (taula `whatsapp_events`), no a la memòria del procés: així un reinici no provoca respostes repetides. Es neteja sol al cap de 7 dies.
- **Si l'enviament falla, el missatge s'allibera** perquè el reintent de Meta sí que s'atengui. Si no, el reintent es descartaria com a duplicat i la persona es quedaria sense resposta per sempre.
- **Un pany per persona.** És normal escriure «hola» i, mig segon després, la pregunta de debò. Sense el pany, les dues respostes es generarien alhora llegint el mateix historial i es trepitjarien.
- **Res no s'escriu a la conversa fins que la resposta s'ha enviat de debò**, i els avisos tècnics («ara no puc respondre») no s'hi guarden: no són un torn de conversa i embrutarien el context de tot el que vingui després.

## Limitacions
Només missatges de text, sense interfície gràfica per gestionar connexions (per ara només API), i fora de la finestra de 24 h de Meta només es pot respondre amb plantilles.
