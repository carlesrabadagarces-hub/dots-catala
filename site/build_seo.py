"""SEO + GEO build: static, crawlable pages generated from the catalogue.

Writes (relative to site/):
  index.html                    home with full <head> (meta, Open Graph, JSON-LD) + static FAQ and directory
  agents/<id>/index.html        one page per Dot (88)
  sectors/<id>/index.html       one page per sector (10)
  robots.txt, sitemap.xml, llms.txt, llms-full.txt, site.webmanifest, agents.css

Set SITE_URL (default https://superdotats.cat) to the real domain before deploying.
"""
import html
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here.parent / "server"))
from app.services.catalog_data import CATALOG, META, SECTORS  # noqa: E402
from app.services.look import look_for_agent  # noqa: E402

SITE = os.environ.get("SITE_URL", "https://superdotats.cat").rstrip("/")
APP_URL = os.environ.get("APP_URL", "http://127.0.0.1:3000")
GITHUB = "https://github.com/carlesrabadagarces-hub/dots-catala"
TODAY = os.environ.get("BUILD_DATE", date.today().isoformat())
SPECS = CATALOG + META
e = lambda s: html.escape(str(s), quote=True)
lower1 = lambda s: s[:1].lower() + s[1:] if s else s


def clip(text, n):
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0].rstrip(",.;:") + "…"


def ld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + "</script>"


# ---------------------------------------------------------------- sprites (rendered with node, same code as the site)
def render_sprites():
    lib = here.parent / "client" / "lib"

    def strip(t):
        t = re.sub(r"^import .*?;\n", "", t, flags=re.M)
        t = re.sub(r"^export ", "", t, flags=re.M)
        return re.sub(r"^/\*.*?\*/\n", "", t, count=1, flags=re.S)

    code = strip((lib / "dotSpriteData.js").read_text()) + "\n" + strip((lib / "dotSprite.js").read_text())
    looks = {s["id"]: look_for_agent(s["id"], s["sector"]) for s in SPECS}
    js = code + "\nconst L=JSON.parse(require('fs').readFileSync(0,'utf8'));const out={css:SPRITE_CSS};for(const k in L){out[k]=dotSprite(L[k],220,'',BASE_PATH)}process.stdout.write(JSON.stringify(out));"
    js = "const BASE_PATH='../../dots/';\n" + js
    tmp = here / ".sprites.tmp.js"
    tmp.write_text(js)
    try:
        res = subprocess.run(["node", str(tmp)], input=json.dumps(looks), capture_output=True, text=True, check=True)
    finally:
        tmp.unlink(missing_ok=True)
    return json.loads(res.stdout)


SPR = render_sprites()

# ---------------------------------------------------------------- shared bits
ORG = {"@type": "Organization", "@id": f"{SITE}/#org", "name": "superDOTats", "url": f"{SITE}/",
       "logo": f"{SITE}/dots/logo.png", "sameAs": [GITHUB]}
LOGO_SVG = '<img src="{p}dots/logo.png" width="32" height="32" alt="" loading="eager">'


def head(title, desc, path, depth, extra="", og_type="website"):
    p = "../" * depth
    url = f"{SITE}{path}"
    return f"""<!doctype html>
<html lang="ca">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<link rel="alternate" hreflang="ca" href="{url}">
<link rel="alternate" hreflang="x-default" href="{url}">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">
<meta name="theme-color" content="#ffffff">
<meta property="og:site_name" content="superDOTats">
<meta property="og:locale" content="ca_ES">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}/og.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Dots de colors saltant per les teulades de Barcelona amb la Sagrada Família al fons">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">
<meta name="twitter:image" content="{SITE}/og.jpg">
<link rel="icon" type="image/png" sizes="32x32" href="{p}icons/favicon-32.png">
<link rel="apple-touch-icon" href="{p}icons/apple-touch-icon.png">
<link rel="manifest" href="{p}site.webmanifest">
{extra}"""


# ---------------------------------------------------------------- FAQ + directory blocks for the home page
FAQ = json.loads((here / "faq.json").read_text(encoding="utf-8"))


def faq_html():
    out = []
    for i, f in enumerate(FAQ):
        out.append(
            f'<div class="fq rv" data-look=\'{e(json.dumps(f["look"]))}\'>'
            f'<h3><button type="button" id="fq-{i}" aria-expanded="false" aria-controls="fa-{i}"><span class="qd" aria-hidden="true"></span>'
            f'<span class="qt">{e(f["q"])}</span><span class="pl" aria-hidden="true">+</span></button></h3>'
            f'<div class="qa" id="fa-{i}" role="region" aria-labelledby="fq-{i}"><div><p>{e(f["a"])}</p></div></div></div>')
    return "\n".join(out)


def by_sector():
    groups = {k: [] for k in SECTORS}
    for s in SPECS:
        groups.setdefault(s["sector"], []).append(s)
    return groups


def dir_html():
    out = []
    for sid, items in by_sector().items():
        if not items:
            continue
        sec = SECTORS[sid]
        out.append(f'<div><h3><span class="sw" style="background:{sec["color"]}"></span><a href="sectors/{sid}/">{e(sec["name"])}</a></h3><ul>'
                   + "".join(f'<li><a href="agents/{s["id"]}/">{e(s["name"])}</a></li>' for s in items) + "</ul></div>")
    return "\n".join(out)


def fill(text, marker, content):
    return re.sub(rf"(<!--{marker}_START-->).*?(<!--{marker}_END-->)", lambda m: m.group(1) + "\n" + content + "\n" + m.group(2), text, flags=re.S)


body = (here / "body.html").read_text(encoding="utf-8")
body = fill(body, "FAQ", faq_html())
body = fill(body, "DIR", dir_html())
(here / "body.html").write_text(body, encoding="utf-8")

# ---------------------------------------------------------------- home
HOME_TITLE = "superDOTats: agents d'IA per al teu WhatsApp, en català"
HOME_DESC = ("superDOTats és una plataforma de codi obert per crear agents d'IA (Dots) i connectar-los al teu WhatsApp. "
             "88 Dots especialitzats en català: metge, fontaner, assessor fiscal, mestra i molts més.")
home_ld = {"@context": "https://schema.org", "@graph": [
    ORG,
    {"@type": "WebSite", "@id": f"{SITE}/#site", "url": f"{SITE}/", "name": "superDOTats", "inLanguage": "ca", "publisher": {"@id": f"{SITE}/#org"}},
    {"@type": "SoftwareApplication", "@id": f"{SITE}/#app", "name": "superDOTats", "applicationCategory": "CommunicationApplication",
     "operatingSystem": "Web, WhatsApp", "description": HOME_DESC, "inLanguage": "ca", "url": f"{SITE}/",
     "license": "https://opensource.org/licenses/MIT", "isAccessibleForFree": True, "codeRepository": GITHUB,
     "offers": {"@type": "Offer", "price": "0", "priceCurrency": "EUR"}, "publisher": {"@id": f"{SITE}/#org"},
     "featureList": ["88 Dots especialitzats en català", "Connexió amb l'API oficial de WhatsApp de Meta", "Memòria per persona",
                     "Panell d'administració", "Codi obert (MIT)"]},
    {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in FAQ]},
    {"@type": "ItemList", "name": "Sectors de superDOTats", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": SECTORS[k]["name"], "url": f"{SITE}/sectors/{k}/"} for i, k in enumerate(SECTORS)]},
    {"@type": "VideoObject", "name": "Un Dot en 16 segons", "description": "Com funciona un Dot: tries un agent, li escrius pel WhatsApp i et respon en català.",
     "thumbnailUrl": f"{SITE}/media/explainer-poster.jpg", "uploadDate": TODAY, "duration": "PT16S",
     "contentUrl": f"{SITE}/media/explainer.mp4", "inLanguage": "ca"},
]}
fonts = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@400;500&display=swap">\n')
home_body = re.sub(r"<title>.*?</title>\n?", "", body, count=1, flags=re.S)
home_body = re.sub(r'<link rel="icon"[^>]*>\n?', "", home_body, count=1)
home_body = re.sub(r'<link rel="preconnect"[^>]*>\n?', "", home_body)
home_body = re.sub(r'<link rel="stylesheet" href="https://fonts.googleapis.com[^>]*>\n?', "", home_body)
home = (head(HOME_TITLE, HOME_DESC, "/", 0, extra=fonts + ld(home_ld) + "\n<style>html,body{margin:0}</style>\n")
        + "</head>\n<body>\n" + home_body + "\n</body>\n</html>\n")
(here / "index.html").write_text(home, encoding="utf-8")

# ---------------------------------------------------------------- agent + sector pages
CSS = (SPR["css"] + """
:root{--bg:#fff;--fg:#0a0a0a;--muted:#5f5f5c;--line:#e8e8e6;--panel:#f6f6f4;--font:"Geist","Helvetica Neue",Arial,sans-serif}
@media (prefers-color-scheme:dark){:root{--bg:#000;--fg:#fafafa;--muted:#a0a0a0;--line:#232323;--panel:#0e0e0e}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}body{margin:0;background:var(--bg);color:var(--fg);font-family:var(--font);line-height:1.6}
a{color:inherit}.w{max-width:960px;margin:0 auto;padding:0 20px}
nav.top{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:16px 0;border-bottom:1px solid var(--line)}
nav.top a.logo{display:flex;align-items:center;gap:10px;font-weight:600;text-decoration:none;letter-spacing:-.03em;font-size:1.15rem}
nav.top .r{display:flex;gap:18px;align-items:center;font-size:14px;color:var(--muted)}nav.top .r a{text-decoration:none}
.btn{display:inline-block;background:var(--fg);color:var(--bg);padding:10px 20px;border-radius:999px;text-decoration:none;font-weight:600;font-size:15px}
.btn.g{background:transparent;color:var(--fg);border:1px solid var(--line)}
.crumbs{font-size:13px;color:var(--muted);margin:18px 0 0}.crumbs a{text-decoration:none}.crumbs a:hover{text-decoration:underline}
.hero{display:grid;grid-template-columns:auto 1fr;gap:28px;align-items:center;padding:28px 0 12px}
h1{font-size:clamp(2rem,5vw,3.2rem);line-height:1.05;letter-spacing:-.04em;margin:0 0 12px}
.lead{color:var(--muted);font-size:1.12rem;margin:0 0 18px;max-width:38em}
h2{font-size:1.5rem;letter-spacing:-.03em;margin:40px 0 12px}
ul.chk{list-style:none;padding:0;margin:0;display:grid;gap:8px}ul.chk li{padding-left:26px;position:relative}ul.chk li::before{content:"✓";position:absolute;left:0;color:#19c3a6;font-weight:700}
.bub{display:flex;flex-direction:column;gap:8px;align-items:flex-end}.bub span{background:#d9fdd3;color:#111;padding:9px 14px;border-radius:16px 16px 4px 16px;max-width:90%}
details{border:1px solid var(--line);border-radius:16px;padding:12px 16px;margin-bottom:10px;background:var(--panel)}summary{cursor:pointer;font-weight:600}details p{margin:10px 0 0;color:var(--muted)}
.rel{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:10px;list-style:none;padding:0;margin:0}
.rel a{display:block;border:1px solid var(--line);border-radius:14px;padding:12px 14px;text-decoration:none;background:var(--panel)}.rel a:hover{border-color:var(--fg)}.rel small{display:block;color:var(--muted)}
.note{font-size:13px;color:var(--muted);margin-top:36px;border-top:1px solid var(--line);padding-top:14px}
footer{margin:60px 0 40px;font-size:13px;color:var(--muted);display:flex;flex-wrap:wrap;gap:8px 20px}footer a{text-decoration:none}footer a:hover{text-decoration:underline}
@media (max-width:640px){.hero{grid-template-columns:1fr;text-align:left}nav.top .r a:not(.btn){display:none}}
""")
(here / "agents.css").write_text(CSS, encoding="utf-8")


def nav(depth):
    p = "../" * depth
    return (f'<a class="skip" href="#c" style="position:absolute;left:-999px">Salta al contingut</a><div class="w"><nav class="top" aria-label="Principal">'
            f'<a class="logo" href="{p}">{LOGO_SVG.format(p=p)}<span>superDOTats</span></a>'
            f'<div class="r"><a href="{p}#directori">Tots els Dots</a><a href="{p}#faq">Preguntes</a><a class="btn" href="{APP_URL}">Entra</a></div></nav>')


def foot(depth):
    p = "../" * depth
    return (f'<footer><span>© superDOTats · codi obert (MIT) · projecte independent, sense relació amb OpenAI ni Meta.</span>'
            f'<a href="{p}">Inici</a><a href="{p}#directori">Directori de Dots</a><a href="{GITHUB}">GitHub</a></footer></div>')


def agent_page(s):
    sec = SECTORS[s["sector"]]
    url_path = f"/agents/{s['id']}/"
    role = s["role"]
    title = clip(f"{s['name']} al WhatsApp: {lower1(role)} | superDOTats", 68)
    tasks = s["tasks"]
    desc = clip(f"{s['name']}: {lower1(role)}. {tasks[0]}, {lower1(tasks[1])} i més, en català i pel teu WhatsApp. Un Dot de superDOTats, gratuït i de codi obert.", 158)
    safety = list(sec.get("safety", [])) + list(s.get("safety", []))
    escalate = " ".join(x for x in (sec.get("escalate", ""), s.get("escalate", "")) if x) or "Si el cas supera el que pot resoldre, et recomana un professional qualificat."
    faqs = [
        (f"Què pot fer {s['name']}?", " ".join(t.rstrip(".") + "." for t in tasks[:3])),
        (f"Puc fiar-me de {s['name']}?", f"És un assistent d'IA i dona informació general. {safety[0] if safety else ''} Verifica sempre les dades importants."),
        (f"Quan em derivarà {s['name']} a un professional?", escalate),
        (f"Com poso {s['name']} al meu WhatsApp?", "Crea el Dot des del catàleg de superDOTats i connecta'l al teu número amb l'API oficial de WhatsApp de Meta. El pots personalitzar i decidir quins contactes hi poden parlar."),
    ]
    rel = [r for r in by_sector()[s["sector"]] if r["id"] != s["id"]][:6]
    ld_graph = {"@context": "https://schema.org", "@graph": [
        ORG,
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "superDOTats", "item": f"{SITE}/"},
            {"@type": "ListItem", "position": 2, "name": sec["name"], "item": f"{SITE}/sectors/{s['sector']}/"},
            {"@type": "ListItem", "position": 3, "name": s["name"], "item": f"{SITE}{url_path}"}]},
        {"@type": "WebPage", "@id": f"{SITE}{url_path}", "url": f"{SITE}{url_path}", "name": title, "description": desc, "inLanguage": "ca",
         "isPartOf": {"@id": f"{SITE}/#site"}, "dateModified": TODAY, "about": {"@id": f"{SITE}{url_path}#dot"}},
        {"@type": "SoftwareApplication", "@id": f"{SITE}{url_path}#dot", "name": f"{s['name']} (superDOTats)", "description": role + ". " + s["persona"],
         "applicationCategory": "CommunicationApplication", "operatingSystem": "WhatsApp", "inLanguage": "ca",
         "isAccessibleForFree": True, "offers": {"@type": "Offer", "price": "0", "priceCurrency": "EUR"},
         "featureList": tasks, "isPartOf": {"@id": f"{SITE}/#app"}, "publisher": {"@id": f"{SITE}/#org"}},
        {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]},
    ]}
    li = lambda items: "".join(f"<li>{e(x)}</li>" for x in items)
    return (head(title, desc, url_path, 2, extra=f'<link rel="stylesheet" href="../../agents.css">\n' + ld(ld_graph) + "\n")
            + "</head>\n<body>\n" + nav(2)
            + f'<p class="crumbs"><a href="../../">superDOTats</a> › <a href="../../sectors/{s["sector"]}/">{e(sec["name"])}</a> › {e(s["name"])}</p>'
            + f'<main id="c"><section class="hero"><div aria-hidden="true">{SPR[s["id"]]}</div><div><h1>{e(s["name"])} al teu WhatsApp</h1>'
            + f'<p class="lead">{e(role)}. {e(s["persona"])}</p><a class="btn" href="{APP_URL}">Prova {e(s["name"])}</a> <a class="btn g" href="../../#directori">Tots els Dots</a></div></section>'
            + f"<h2>Què pot fer</h2><ul class=\"chk\">{li(tasks)}</ul>"
            + f"<h2>En què és expert</h2><ul class=\"chk\">{li(s['expertise'])}</ul>"
            + f"<h2>Prova a preguntar-li</h2><div class=\"bub\">" + "".join(f"<span>{e(x)}</span>" for x in s["starters"]) + "</div>"
            + f"<h2>Límits i seguretat</h2><ul class=\"chk\">{li(safety)}</ul>"
            + f"<h2>Quan et derivarà a un professional</h2><p>{e(escalate)}</p>"
            + "<h2>Preguntes freqüents</h2>" + "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in faqs)
            + f'<h2>Més Dots de {e(sec["name"])}</h2><ul class="rel">' + "".join(f'<li><a href="../{r["id"]}/">{e(r["name"])}<small>{e(clip(r["role"], 60))}</small></a></li>' for r in rel) + "</ul>"
            + '<p class="note">superDOTats és un assistent d\'IA que dona informació general i educativa. No substitueix un professional col·legiat ni un servei d\'urgències; en cas d\'urgència, truca al 112.</p></main>'
            + foot(2) + "\n</body>\n</html>\n")


def sector_page(sid):
    sec = SECTORS[sid]
    items = by_sector()[sid]
    url_path = f"/sectors/{sid}/"
    title = clip(f"Dots d'{sec['name'].lower()} al WhatsApp ({len(items)}) | superDOTats", 68)
    desc = clip(f"{len(items)} agents d'IA de {sec['name'].lower()} en català pel teu WhatsApp: " + ", ".join(i["name"] for i in items[:5]) + " i més. Codi obert i gratuït.", 158)
    ld_graph = {"@context": "https://schema.org", "@graph": [
        ORG,
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "superDOTats", "item": f"{SITE}/"},
            {"@type": "ListItem", "position": 2, "name": sec["name"], "item": f"{SITE}{url_path}"}]},
        {"@type": "CollectionPage", "@id": f"{SITE}{url_path}", "url": f"{SITE}{url_path}", "name": title, "description": desc, "inLanguage": "ca",
         "isPartOf": {"@id": f"{SITE}/#site"}, "dateModified": TODAY},
        {"@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": s["name"], "url": f"{SITE}/agents/{s['id']}/"} for i, s in enumerate(items)]},
    ]}
    intro = " ".join(sec.get("safety", [])[:1]) or ""
    return (head(title, desc, url_path, 2, extra='<link rel="stylesheet" href="../../agents.css">\n' + ld(ld_graph) + "\n")
            + "</head>\n<body>\n" + nav(2)
            + f'<p class="crumbs"><a href="../../">superDOTats</a> › {e(sec["name"])}</p><main id="c"><h1>Dots d\'{e(sec["name"].lower())} al WhatsApp</h1>'
            + f'<p class="lead">{len(items)} agents d\'IA especialitzats, en català, que et responen pel WhatsApp. {e(intro)}</p><ul class="rel">'
            + "".join(f'<li><a href="../../agents/{s["id"]}/">{e(s["name"])}<small>{e(clip(s["role"], 70))}</small></a></li>' for s in items)
            + "</ul><h2>Com funciona</h2><p>Tries un Dot, el connectes al teu número de WhatsApp amb l'API oficial de Meta i li escrius com a qualsevol contacte. Quan el tema el supera, et deriva a un professional.</p>"
            + '<p class="note">Informació general i educativa; no substitueix un professional. En cas d\'urgència, truca al 112.</p></main>' + foot(2) + "\n</body>\n</html>\n")


shutil.rmtree(here / "agents", ignore_errors=True)
shutil.rmtree(here / "sectors", ignore_errors=True)
for s in SPECS:
    d = here / "agents" / s["id"]
    d.mkdir(parents=True)
    (d / "index.html").write_text(agent_page(s), encoding="utf-8")
for sid, items in by_sector().items():
    if items:
        d = here / "sectors" / sid
        d.mkdir(parents=True)
        (d / "index.html").write_text(sector_page(sid), encoding="utf-8")

# ---------------------------------------------------------------- robots, sitemap, llms.txt, manifest
AI_BOTS = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-User", "Claude-SearchBot", "PerplexityBot", "Google-Extended", "Applebot-Extended", "CCBot"]
robots = "User-agent: *\nAllow: /\n\n" + "".join(f"User-agent: {b}\nAllow: /\n\n" for b in AI_BOTS) + f"Sitemap: {SITE}/sitemap.xml\n"
(here / "robots.txt").write_text(robots, encoding="utf-8")

urls = [("/", "1.0", "weekly")] + [(f"/sectors/{k}/", "0.8", "monthly") for k, v in by_sector().items() if v] + [(f"/agents/{s['id']}/", "0.7", "monthly") for s in SPECS]
sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for path, prio, freq in urls:
    sm.append(f"<url><loc>{SITE}{path}</loc><lastmod>{TODAY}</lastmod><changefreq>{freq}</changefreq><priority>{prio}</priority></url>")
sm.append("</urlset>")
(here / "sitemap.xml").write_text("\n".join(sm) + "\n", encoding="utf-8")

llms = [f"# superDOTats", "",
        "> superDOTats és una plataforma de codi obert (llicència MIT) per crear agents d'IA, anomenats Dots, i connectar-los al WhatsApp amb l'API oficial de Meta. "
        "Inclou un catàleg de 88 Dots especialitzats en català (metge, fontaner, assessor fiscal, mestra, cuiner…), memòria per persona i un panell d'administració. "
        "Dona informació general i educativa; no substitueix professionals.", "",
        "## Fets clau", "- Nom: superDOTats (escrit amb majúscules a DOT).", f"- Web: {SITE}/", f"- Codi: {GITHUB}",
        "- Llicència: MIT. Idioma per defecte: català (respon també en castellà i anglès).", "- Canal principal: WhatsApp Cloud API de Meta.", "",
        "## Pàgines principals", f"- [Inici]({SITE}/): què és i com funciona", f"- [Preguntes freqüents]({SITE}/#faq): respostes curtes",
        f"- [Directori de Dots]({SITE}/#directori): tots els Dots per sector", f"- [Text complet per a models]({SITE}/llms-full.txt)", ""]
for sid, items in by_sector().items():
    if not items:
        continue
    llms += [f"## {SECTORS[sid]['name']}", ""] + [f"- [{s['name']}]({SITE}/agents/{s['id']}/): {s['role']}" for s in items] + [""]
(here / "llms.txt").write_text("\n".join(llms), encoding="utf-8")

full = ["# superDOTats: text complet", "", llms[2][2:], "", "## Preguntes freqüents", ""]
for f in FAQ:
    full += [f"### {f['q']}", f["a"], ""]
for sid, items in by_sector().items():
    for s in items:
        sec = SECTORS[sid]
        full += [f"## {s['name']} ({sec['name']})", f"URL: {SITE}/agents/{s['id']}/", f"Rol: {s['role']}. {s['persona']}", "Tasques: " + "; ".join(s["tasks"]),
                 "Expert en: " + "; ".join(s["expertise"]), "Exemples de preguntes: " + " | ".join(s["starters"]),
                 "Derivació: " + (" ".join(x for x in (sec.get("escalate", ""), s.get("escalate", "")) if x) or "Recomana un professional qualificat."), ""]
(here / "llms-full.txt").write_text("\n".join(full), encoding="utf-8")

manifest = {"name": "superDOTats", "short_name": "superDOTats", "description": HOME_DESC, "lang": "ca", "start_url": "/", "display": "standalone",
            "background_color": "#ffffff", "theme_color": "#ffffff",
            "icons": [{"src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png"}, {"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png"}]}
(here / "site.webmanifest").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"seo ok: {len(SPECS)} agents, {len(by_sector())} sectors, site={SITE}")
