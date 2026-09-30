# SEO i GEO (cerca amb IA) de la web pública

Tot es genera amb `sh site/build.sh` a partir del catàleg de Dots. Abans de publicar, defineix el domini real:

```bash
SITE_URL=https://el-teu-domini.cat APP_URL=https://app.el-teu-domini.cat sh site/build.sh
```
`SITE_URL` és el domini de la web (canonical, sitemap, Open Graph, dades estructurades). El valor per defecte, `superdotats.cat`, és només un marcador: no és un domini registrat.

## Què s'ha fet
**Pàgines que es poden indexar (98 + inici)**
- `agents/<dot>/`: una pàgina per Dot (88) amb títol i descripció propis, què fa, expertesa, exemples de preguntes, límits, quan deriva a un professional i preguntes freqüents. El contingut surt del catàleg, no és text duplicat.
- `sectors/<sector>/`: 10 pàgines de sector amb la llista dels seus Dots.
- Inici amb un resum citable «Què és superDOTats», FAQ i directori de tots els Dots en HTML estàtic (abans es dibuixaven amb JavaScript i els rastrejadors sense JS no ho veien).

**Tècnic**
- `<title>`, `meta description`, `canonical`, `hreflang`, `robots` amb previsualitzacions àmplies, Open Graph, Twitter Card (`og.jpg` 1200×630), icones, `site.webmanifest`.
- Dades estructurades JSON-LD: `Organization`, `WebSite`, `SoftwareApplication`, `FAQPage`, `ItemList`, `VideoObject`, `BreadcrumbList`, `CollectionPage`. Cada FAQ del JSON-LD coincideix amb el text visible.
- `robots.txt` (permet els rastrejadors d'IA: GPTBot, OAI-SearchBot, ClaudeBot, PerplexityBot, Google-Extended…), `sitemap.xml` amb 99 URL i data de modificació.
- Semàntica: un sol `h1` per pàgina, `main`, enllaç «Salta al contingut», FAQ accessible amb `aria`.

**GEO (que els assistents d'IA et citin bé)**
- `llms.txt` (resum i enllaços) i `llms-full.txt` (tots els Dots amb tasques, límits i derivació).
- Un paràgraf definitori i fets curts i coherents (88 Dots, 10 sectors, MIT, català, API oficial de Meta) que es poden citar tal qual.
- Nom sempre escrit igual: **superDOTats**.
- Avisos honestos a cada pàgina (informació general, no substitueix un professional, 112 en urgències).

## Pendent (ho has de fer tu o depèn del domini)
1. Registrar el domini i desplegar `site/` a l'arrel (Caddy/Nginx). Servir `robots.txt`, `sitemap.xml` i `llms.txt` a l'arrel.
2. Donar d'alta el domini a **Google Search Console** i **Bing Webmaster Tools**, enviar `sitemap.xml` i validar les dades estructurades amb la «Prova de resultats enriquits».
3. Comprovar el rendiment (PageSpeed / Lighthouse). Els vídeos pesen; considera servir-los amb `preload="none"` a mòbil o des d'una CDN.
4. Contingut que dona autoritat: casos reals, un blog amb guies («Com fer la renda si ets autònom», «Què fer davant una fuita»), enllaços de premsa i d'altres webs. Sense enllaços externs, el SEO tècnic no basta.
5. Idiomes: ara només català. Per captar castellà i anglès, afegir versions traduïdes amb `hreflang` recíproc, no només un selector.
6. Revisar amb un professional els textos dels Dots de salut i legal abans de promocionar-los.
7. Prova periòdica de GEO: pregunta a ChatGPT, Claude, Gemini i Perplexity coses com «agents d'IA en català per al WhatsApp» i mira si et citen; ajusta el text del resum i de `llms.txt`.

## Limitacions
- L'aparença de la pàgina d'inici amb JavaScript (animacions, vídeos) no afecta el text indexable, però un rendiment lent sí que pot perjudicar el posicionament.
- Cap garantia de posicions: el SEO depèn de la competència, l'antiguitat del domini i els enllaços.
