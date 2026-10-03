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
4. Desplega **Environment Variables** i afegeix `SITE_PASSWORD` amb la contrasenya que vulguis
   (només lletres i números). L'usuari és `dots`, o el que posis a `SITE_USER`.
5. **Deploy**.

La configuració (`vercel.json`) i la contrasenya (`middleware.js`) són dins de `site/`, perquè Vercel
les llegeix de la carpeta arrel del projecte.

## Si la contrasenya no funciona (pla B)
`middleware.js` demana la contrasenya amb la lògica provada en local, però **no he pogut provar-lo
dins de Vercel**: no vaig poder llegir-ne la documentació des d'aquí, i no sé del cert com tracta un
projecte estàtic (sense Next.js) la resposta buida que dona quan la contrasenya és bona. Si en obrir la
web veus una pàgina en blanc o un error després d'escriure la contrasenya:

1. Esborra `site/middleware.js` i torna a desplegar. La web queda oberta, però amb `noindex`, així que només
   la veu qui tingui l'enllaç. Per ensenyar una maqueta, és prou.
2. O fes servir la protecció que porta Vercel al panell (Settings → Deployment Protection). Les opcions
   que et deixa depenen del teu pla.

Si no poses `SITE_PASSWORD`, la web **no s'obre** (error 503): preferim que falli tancada.

## Com queda protegida
- `middleware.js` demana contrasenya abans de servir res. Funciona amb qualsevol pla.
- Les pàgines porten `noindex` i el `robots.txt` diu a tothom que no la indexi.
- Vercel també té la seva pròpia protecció al panell (Settings → Deployment Protection).
  Si la vols fer servir en lloc de la contrasenya, mira quines opcions et deixa el teu pla.

## Quan tinguis el domini de debò
Torna a generar la web amb el domini real i sense el mode privat:

```bash
SITE_URL=https://el-teu-domini.cat APP_URL=https://app.el-teu-domini.cat sh site/build.sh
```
Això arregla les adreces canòniques, el `sitemap.xml`, les imatges per compartir i
els botons «Entra», i torna a permetre que els cercadors la indexin.

## Avís
Ara mateix la web està generada per a `superdots.vercel.app` i amb `robots.txt`
tancat. Si algun dia la publiques de veritat sense tornar-la a generar, no sortirà
a Google.
