# Administració, estadístiques i personalització

## Logins de prova
- **Membre de prova:** qualsevol nom + contrasenya `123456`. Cada nom crea un compte separat amb els seus Dots.
- **Administrador:** usuari `admin` + contrasenya `admin`.
- Aquests valors només funcionen en **mode local** (sense `PUBLIC_BASE_URL` i amb `HOST=127.0.0.1`). En un servidor públic no hi ha contrasenyes per defecte: cal definir `TEST_MEMBER_PASSWORD` i `ADMIN_PASSWORD` (mínim 8 caràcters, o `ALLOW_WEAK_TEST_LOGINS=1` sota la teva responsabilitat).
- Hi ha un límit de 6 intents fallits per minut i adreça.
- Abans d'obrir el servei al públic, desactiva els logins de prova (no definis les variables) i deixa només Google i Apple. Un administrador també pot ser un compte de Google o Apple amb el seu correu a `ADMIN_EMAILS`.

## Panell d'administració (`/admin`)
- Resum: membres, membres actius en 7 dies, Dots creats, missatges, peticions al model, tokens, cost estimat, latència (mitjana, mediana i p95) i taxa d'errors.
- Gràfics diaris de peticions i de tokens; taules per model, per canal (web, WhatsApp, generació de Dots), Dots més actius i membres.
- Control per membre: suspendre o reactivar el compte i fixar un límit diari de tokens. Un compte suspès o que ha arribat al límit no pot fer servir el model.
- Les xifres de tokens són **estimades** (uns 4 caràcters per token). El cost surt de `TOKEN_PRICE_IN_PER_M` i `TOKEN_PRICE_OUT_PER_M` (per milió de tokens); ajusta'ls al preu real del teu model.
- API: `GET /api/v1/admin/stats?days=30` i `PATCH /api/v1/admin/users/{id}` (només administradors).

## Personalització dels Dots
Cada Dot té un aspecte propi (`look`): forma (6), color propi, ulls (7), boca (5), barret (13), ulleres (6), complements (10) i color dels complements. S'edita amb el botó "Personalitza" (a la llista i a la capçalera del xat), amb previsualització en directe i un botó "Sorpresa". Els Dots del catàleg s'instal·len ja vestits amb el seu ofici (cuiner amb gorro, metge amb fonendoscopi, etc.).

El dibuix el fa `client/lib/dotSvg.js`, el mateix codi que fa servir la web de presentació. El servidor només accepta valors coneguts (`server/app/services/look.py`) i un test comprova que les llistes coincideixen.
