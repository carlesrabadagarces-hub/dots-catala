# Art dels Dots (Higgsfield)

Els Dots "de peluix" són imatges en capes generades amb Higgsfield (GPT Image 2.5, fons transparent):
- 3 cossos (gota, arc, cub) × 8 colors de pelatge (rosa, taronja, groc, verd, verd atzur, blau, violeta, pissarra).
- 16 complements: 12 barrets, unes ulleres de sol, i pajarita, corbata i bigoti. S'han descartat visera, bufanda, fonendoscopi, auriculars, capa, ulleres rodones i quadrades, monocle i insígnia: o quedaven malament sobre els cossos o els vidres transparents deixaven veure els ulls de la imatge.

## Flux de treball
1. Les imatges originals (PNG 1024) van a `brand/art/raw/` (no es pugen a git; la llista amb els enllaços és a `brand/art/manifest.json` i es poden tornar a baixar amb `python brand/download_assets.py`).
2. `python brand/build_art.py` les processa: treu l'ombra, retalla, redimensiona i les guarda en WebP a `client/public/dots/` i `site/dots/`, i calcula on són els ulls i el cap de cada cos (`manifest.json` i `client/lib/dotSpriteData.js`).
3. `client/lib/dotSprite.js` munta el Dot per capes amb aquestes posicions (el mateix codi l'usa la web de presentació). El Dot pla en SVG (`dotSvg.js`) queda com a alternativa per als bots antics.

## Vida
`client/lib/dotLife.js` fa que respirin, parpellegin (en la versió SVG), s'alegrin quan els toques, "pensin" o "parlin" segons l'estat, i s'adormin si no hi ha activitat. A la web de presentació els Dots de la capçalera es mouen i fan botets en caminar, hi ha un company que viu a la cantonada i un final on el Dot salta, fa l'ullet i llança confeti.

## Limitacions
- Els ulls són part de la imatge: no segueixen el cursor ni parpellegen en els Dots de peluix (només el moviment del cos). L'ullet del final és un pedaç dibuixat sobre l'ull.
- Cada complement té una posició calculada per als 3 cossos; convé revisar-los a ull si en canvies les imatges.

## Logotip
El logotip és el nostre Dot blau (cos "gota"): `brand/logo-blue-*.png`. `python brand/make_logo.py` regenera el logotip, la icona de l'app i la de la web.
