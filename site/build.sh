#!/bin/sh
# Genera body.html (font de l'artifact) i, amb build_seo.py, index.html + pàgines SEO/GEO.
#   SITE_URL=https://el-teu-domini.cat sh site/build.sh
cd "$(dirname "$0")"
python3 build.py
python3 build_seo.py
