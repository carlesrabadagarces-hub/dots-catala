# Publicar la web en privat a Vercel

Això publica **només la web pública** (`site/`), que és HTML estàtic. L'app (entrar,
crear Dots, panell d'admin, WhatsApp) no hi va: necessita un servidor amb base de
dades, i Vercel no en guarda. Allà hi tindràs l'aparador, no el producte funcionant.

## Passos (uns 10 minuts)
1. Entra a vercel.com amb el compte de GitHub i fes **Add New → Project**.
2. Tria el repositori `dots-catala` i la branca `claude/open-dots-whatsapp-integration-hn623w`.
3. Posa-li de nom **superdots** (així la URL serà `superdots.vercel.app`).
4. No cal tocar res més: `vercel.json` ja diu que serveixi la carpeta `site/`.
5. A **Settings → Environment Variables** afegeix:
   - `SITE_PASSWORD`: la contrasenya que vulguis (només lletres i números).
   - `SITE_USER` (opcional): l'usuari; si no el poses, és `dots`.
6. Desplega. En obrir la web, el navegador demanarà usuari i contrasenya.

## Si la contrasenya no funciona (pla B)
`middleware.js` demana la contrasenya amb la lògica provada en local, però **no he pogut provar-lo
dins de Vercel**: no vaig poder llegir-ne la documentació des d'aquí, i no sé del cert com tracta un
projecte estàtic (sense Next.js) la resposta buida que dona quan la contrasenya és bona. Si en obrir la
web veus una pàgina en blanc o un error després d'escriure la contrasenya:

1. Esborra `middleware.js` i torna a desplegar. La web queda oberta, però amb `noindex`, així que només
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
