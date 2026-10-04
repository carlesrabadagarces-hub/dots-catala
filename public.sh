#!/usr/bin/env bash
# Obre superDOTats a internet des del teu ordinador, amb una adreça https temporal.
#   ./public.sh        (cal: brew install cloudflared)
# Qualsevol persona amb l'enllaç podrà crear-se un compte. Aturar-ho: Ctrl+C.
set -e
cd "$(dirname "$0")"

command -v cloudflared >/dev/null 2>&1 || { echo "Cal cloudflared. Mac: brew install cloudflared"; exit 1; }
PY=""
for c in python3.13 python3.12 python3.11 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info>=(3,11) else 1)' 2>/dev/null; then PY="$c"; break; fi
done
[ -n "$PY" ] || { echo "Cal Python 3.11 o superior. Mac: brew install python@3.12"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Cal Node 18 o superior. Mac: brew install node"; exit 1; }

[ -d server/.venv ] || "$PY" -m venv server/.venv
server/.venv/bin/pip install -q -r server/requirements.txt
[ -d client/node_modules ] || (cd client && npm install --no-audit --no-fund)

LOG="$(mktemp -d)"
cleanup() { kill $TUNNEL $API $WEB 2>/dev/null || true; }
trap cleanup EXIT INT TERM

echo "Obrint el túnel…"
cloudflared tunnel --url http://127.0.0.1:3000 >"$LOG/tunnel.log" 2>&1 &
TUNNEL=$!
URL=""
for _ in $(seq 1 40); do
  URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$LOG/tunnel.log" | head -1 || true)
  [ -n "$URL" ] && break
  sleep 1
done
[ -n "$URL" ] || { echo "No s'ha pogut obrir el túnel. Mira $LOG/tunnel.log"; exit 1; }

# Contrasenya d'admin: la tries tu amb ADMIN_PASSWORD=... ./public.sh, o se'n genera una.
ADMIN_PASSWORD="${ADMIN_PASSWORD:-$("$PY" -c 'import secrets; print(secrets.token_urlsafe(9))')}"

echo "Preparant la web…"
(cd client && NEXT_PUBLIC_API_URL=/api/v1 npx next build >"$LOG/build.log" 2>&1) || { echo "Ha fallat la build. Mira $LOG/build.log"; exit 1; }

(cd server && PUBLIC_BASE_URL="$URL" FRONTEND_URL="$URL" CORS_ORIGINS="$URL" AUTH_COOKIE_SECURE=1 ALLOW_LOCAL_LOGIN=0 \
  ADMIN_PASSWORD="$ADMIN_PASSWORD" ../server/.venv/bin/python -c "import uvicorn; uvicorn.run('app.main:app', host='127.0.0.1', port=8000)") &
API=$!
(cd client && npx next start -p 3000) &
WEB=$!

sleep 6
echo
echo "=============================================="
echo " Enllaç públic:   $URL"
echo " Admin:           $URL/admin"
echo " Usuari:          admin"
echo " Contrasenya:     $ADMIN_PASSWORD"
echo "=============================================="
echo "Cada persona es crea el seu compte i posa la seva clau de model (Groq, Gemini…)."
echo "L'enllaç canvia cada cop que l'engegues. Ctrl+C per aturar."
wait
