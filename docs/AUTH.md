# Inici de sessió amb Google i Apple

Cada persona entra amb el seu compte de Google o d'Apple i té els seus propis Dots, converses i connexions de WhatsApp. Ningú no veu les dades dels altres.

## Com funciona
- Flux estàndard OpenID Connect (codi d'autorització). El servidor verifica la signatura del token, l'`aud`, l'emissor i el `nonce`.
- La sessió és una cookie signada (`httponly`), sense guardar res al navegador.
- Si el mateix correu verificat entra amb Google i amb Apple, és el mateix compte.
- En el primer accés es crea un Dot de benvinguda.
- Un botó només és actiu si el proveïdor està configurat. L'accés amb el token local (`.auth-token`) només queda disponible mentre no hi hagi cap proveïdor configurat; es pot forçar amb `ALLOW_LOCAL_LOGIN=1|0`.

## Variables d'entorn del servidor
| Variable | Per a què |
| --- | --- |
| `PUBLIC_BASE_URL` | URL pública de l'API, p. ex. `https://api.superdotats.cat` |
| `FRONTEND_URL` | URL de la web, p. ex. `https://app.superdotats.cat` (per defecte `http://127.0.0.1:3000`) |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Credencials OAuth de Google |
| `APPLE_CLIENT_ID` | *Services ID* d'Apple |
| `APPLE_TEAM_ID`, `APPLE_KEY_ID` | Equip i clau de "Sign in with Apple" |
| `APPLE_PRIVATE_KEY` o `APPLE_PRIVATE_KEY_PATH` | Clau privada `.p8` (text amb `\n` o ruta al fitxer) |
| `SESSION_SECRET` | Opcional. Si no hi és, es genera a `DATA_DIR/.session-secret` |
| `AUTH_COOKIE_SECURE=1` | Recomanat en producció (HTTPS) |
| `CORS_ORIGINS` | Ha d'incloure `FRONTEND_URL` |

## Google
1. A Google Cloud Console → APIs i serveis → Credencials → ID de client OAuth (aplicació web).
2. URI de redirecció autoritzat: `<PUBLIC_BASE_URL>/api/v1/auth/oauth/google/callback`.

## Apple
1. Al compte de desenvolupador d'Apple: crea un *App ID* amb "Sign in with Apple", un *Services ID* i una *Key* (`.p8`).
2. Al *Services ID* afegeix el domini i com a *Return URL*: `<PUBLIC_BASE_URL>/api/v1/auth/oauth/apple/callback`.
3. Apple exigeix HTTPS i un domini verificat; no funciona amb `localhost`.
4. Apple només envia el nom la primera vegada que la persona entra.

## Notes d'un servei compartit
- Les claus del model (`MODEL_API_KEY`) són les del servidor: tots els membres les fan servir. Vigila el cost o limita l'accés.
- Les eines que executen accions (ordinador, connectors) requereixen aprovació a la interfície; revisa-les abans d'obrir el servei al públic.
- Aquesta configuració no s'ha provat amb comptes reals de Google ni d'Apple; sí amb tests automàtics.
