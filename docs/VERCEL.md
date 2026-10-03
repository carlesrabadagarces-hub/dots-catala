# Publicar la web en privat a Vercel

Això publica **només la web pública** (`site/`), que és HTML estàtic. L'app (entrar,
crear Dots, panell d'admin, WhatsApp) no hi va: necessita un servidor amb base de
dades, i Vercel no en guarda. Allà hi tindràs l'aparador, no el producte funcionant.

## Passos (uns 5 minuts)
1. A vercel.com → **Add New → Project** i tria el repositori `dots-catala`.
2. Vercel detectarà tres aplicacions (`client`, `server`, `runtime`) i et proposarà el preset **Services**.
   **No les importis**: l'app necessita un servidor amb disc i Vercel no en té.
3. Canvia aquests tres camps:
   - **Project Name**: `superdots` (la URL serà `superdots.vercel.app`).
   - **Root Directory**: `site`.
   - **Application Preset**: `Other`.
4. **Deploy**. No cal cap variable d'entorn.

La configuració és a `site/vercel.json`. Cada cop que s'hi puja alguna cosa, Vercel torna a publicar.

## Públic, però fora de Google
La web és pública: la veu qualsevol que tingui l'enllaç. Però porta `noindex` (a les pàgines, a
`robots.txt` i a la capçalera `X-Robots-Tag`), perquè no volem que Google indexi una adreça
provisional. Quan tinguis el domini de debò, mira l'apartat següent.

Va tenir una contrasenya (un `middleware.js`), però la vaig treure: no es podia provar dins de
Vercel i, si fallava, deixava la web en blanc. Si algun dia vols tornar a tancar-la, la via fiable
és la protecció que porta Vercel al panell (Settings → Deployment Protection).

## Quan tinguis el domini de debò
Torna a generar la web amb el domini real i sense el mode privat:

```bash
SITE_URL=https://el-teu-domini.cat APP_URL=https://app.el-teu-domini.cat sh site/build.sh
```
Això arregla les adreces canòniques, el `sitemap.xml`, les imatges per compartir i
els botons «Entra», i torna a permetre que els cercadors la indexin.
