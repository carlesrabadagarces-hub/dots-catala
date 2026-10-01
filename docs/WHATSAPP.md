# Connectar un agent a WhatsApp

Cada persona connecta el **seu propi número** mitjançant l'API oficial *WhatsApp Cloud API* de Meta. No es fa servir cap API no oficial.

## Requisits
1. Un compte a [Meta for Developers](https://developers.facebook.com) amb una app de tipus *Business* i el producte **WhatsApp** afegit.
2. Un número (el de prova de Meta o el teu) i, d'aquí: el **Phone number ID**, un **access token** i l'**App secret** (Settings → Basic).
3. Una URL pública HTTPS cap al servidor (p. ex. `cloudflared tunnel --url http://127.0.0.1:8000` o `ngrok http 8000`).

## Passos
1. Arrenca superDOTats i entra-hi.
2. A la barra lateral, obre **WhatsApp**. La pantalla et guia:
   - Hi poses el **Phone number ID**, l'**access token** i l'**app secret** que et dona Meta.
   - Tries qui respon: un Dot concret o **automàtic** (el tria segons la pregunta).
   - Hi escrius els números que poden parlar amb el Dot. Ningú més rebrà resposta.
3. En connectar-lo, la mateixa pantalla et dona la **Callback URL** i el **Verify token** per copiar.
   A Meta → WhatsApp → Configuration → Webhook, enganxa'ls i subscriu el camp **messages**.
4. Prem **Envia una prova** per comprovar que el número respon abans de fer res més.

Perquè la Callback URL surti sencera, el servidor ha de saber la seva adreça pública:
posa `PUBLIC_BASE_URL=https://la-teva-url` a les variables d'entorn. Sense això, la pantalla
t'ho avisa i et diu com construir-la.

També es pot fer tot per API, si ho prefereixes:

```
POST /api/v1/whatsapp/connections
{"label": "El meu WhatsApp", "auto_route": true,
 "phone_number_id": "...", "access_token": "...", "app_secret": "...",
 "allowed_numbers": ["+34600111222"]}
```
La resposta inclou `id`, `verify_token` i `webhook_url`.
`POST /api/v1/whatsapp/connections/{id}/test` amb `{"to": "+34..."}` envia el missatge de prova.

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
Només missatges de text (ni àudio ni imatges, encara) i, fora de la finestra de 24 h de Meta, només es pot respondre amb plantilles aprovades.
