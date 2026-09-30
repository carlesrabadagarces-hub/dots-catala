#!/bin/sh
# Genera body.html (font de l'artifact) i index.html (pàgina completa).
cd "$(dirname "$0")"
python3 build.py
{ printf '<!doctype html>\n<html lang="ca">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">\n'
  printf '<style>html,body{margin:0}</style>\n'; cat body.html; printf '\n</html>\n'; } > index.html
