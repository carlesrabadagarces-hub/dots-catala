#!/usr/bin/env bash
# Engega superDOTats en local (servidor + web) amb una sola ordre.
#   ./start.sh          -> http://127.0.0.1:3000   (admin / admin per al panell)
set -e
cd "$(dirname "$0")"

PY=""
for c in python3.13 python3.12 python3.11 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info>=(3,11) else 1)' 2>/dev/null; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then echo "Cal Python 3.11 o superior. Mac: brew install python@3.12"; exit 1; fi
if ! command -v node >/dev/null 2>&1; then echo "Cal Node 18 o superior. Mac: brew install node"; exit 1; fi
if ! node -e 'process.exit(parseInt(process.versions.node)>=18?0:1)'; then echo "Node és massa antic (cal 18+). Mac: brew upgrade node"; exit 1; fi

if [ ! -d server/.venv ]; then echo "Creant entorn Python..."; "$PY" -m venv server/.venv; fi
echo "Instal·lant dependències del servidor..."
server/.venv/bin/pip install -q -r server/requirements.txt
if [ ! -d client/node_modules ]; then echo "Instal·lant dependències de la web (uns minuts)..."; (cd client && npm install --no-audit --no-fund); fi

cleanup() { kill "$API" "$WEB" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

(cd server && ../server/.venv/bin/python -c "import uvicorn; uvicorn.run('app.main:app', host='127.0.0.1', port=8000)") &
API=$!
(cd client && npm run dev -- -p 3000) &
WEB=$!

echo
echo "Quan vegis 'Ready', obre http://127.0.0.1:3000  (usuari: admin · contrasenya: admin, i ves a /admin)"
echo "Per aturar-ho: Ctrl+C"
wait
