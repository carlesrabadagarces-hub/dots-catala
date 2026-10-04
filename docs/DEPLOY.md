# Posar superDOTats en un servidor (enllaç fix, ràpid i sempre encès)

Resultat: la landing a `https://superdotats.cat` i l'app a `https://app.superdotats.cat`, amb HTTPS automàtic. Això és el que cal també per al WhatsApp de debò, perquè Meta vol una adreça que no canviï.

## Què necessites
- **Un servidor** Linux (Ubuntu 24.04), p. ex. Hetzner CX22 (uns 4-5 €/mes, 2 CPU / 4 GB). Amb 2 GB ja arrenca, però la compilació de la web hi va justa.
- **Un domini** i poder crear-hi dos registres DNS.
- Una clau de model (Groq, Gemini…). Pots deixar-la buida i que cada persona posi la seva.

## Passos

### 1. Servidor
Crea el servidor i anota'n la **IP**. Entra-hi: `ssh root@LA_IP`.

### 2. DNS
Al panell del teu domini, crea dos registres **A** apuntant a la IP del servidor:
- `superdotats.cat` → `LA_IP` (la landing)
- `app.superdotats.cat` → `LA_IP` (l'app)

Espera uns minuts a què s'escampin. Caddy no podrà treure els certificats fins que el DNS apunti bé.

### 3. Docker
```
curl -fsSL https://get.docker.com | sh
```

### 4. Baixa el codi
```
git clone https://github.com/carlesrabadagarces-hub/dots-catala.git
cd dots-catala
git checkout claude/open-dots-whatsapp-integration-hn623w
```
El repositori és privat: com a contrasenya fes servir un *Personal Access Token* de GitHub (permís de lectura del repositori).

### 5. Configura
```
cp .env.example .env
nano .env
```
Omple com a mínim `SITE_DOMAIN`, `APP_DOMAIN` i `ADMIN_PASSWORD` (llarga: usuari `admin`). Desa amb `Ctrl+O`, `Enter`, `Ctrl+X`.

### 6. Engega
```
docker compose up -d --build
```
El primer cop triga uns 5-10 minuts (compila la web i la landing).

### 7. Comprova
- `https://app.superdotats.cat`: ha de sortir la pantalla d'accés.
- `https://app.superdotats.cat/admin`: usuari `admin` i la teva contrasenya.
- `https://superdotats.cat`: la landing.

## Dia a dia
| Què | Ordre |
| --- | --- |
| Veure què passa | `docker compose logs -f api` (o `web`, `caddy`) |
| Actualitzar | `git pull && docker compose up -d --build` |
| Aturar | `docker compose down` (les dades es conserven) |
| Reiniciar | `docker compose restart` |
| Estat | `docker compose ps` |

## Còpia de seguretat (fes-la!)
Comptes, Dots, converses i claus xifrades són al volum `data`:
```
docker run --rm -v dots-catala_data:/data -v "$PWD":/backup alpine tar czf /backup/dots-backup-$(date +%F).tgz -C /data .
```
Descarrega el `.tgz` al teu ordinador. Guarda'l: **conté les claus de xifratge**; qui el tingui pot llegir les claus dels usuaris.

## Quan ho tinguis
- **Google/Apple:** vegeu `docs/AUTH.md`. Les adreces de retorn són `https://app.superdotats.cat/api/v1/auth/oauth/google/callback` i `…/apple/callback`.
- **WhatsApp:** a la pantalla WhatsApp de l'app, la *Callback URL* ja surt amb la teva adreça fixa. Vegeu `docs/WHATSAPP.md`.
- **Tancar els registres:** `SIGNUP_OPEN=0` a `.env` i `docker compose up -d`.

## Seguretat
- Obre només els ports 80 i 443 (`ufw allow 22,80,443/tcp && ufw enable`). El port 8000 de l'API no està publicat: només hi arriba Caddy.
- No posis `MODEL_API_KEY` al servidor si no vols pagar les peticions de tothom.
- Hi ha usuaris desconeguts: abans d'obrir-ho de debò, afegeix pàgines de privacitat i condicions, i un correu de contacte.
- Aquests fitxers no s'han pogut provar en un servidor real des de l'entorn on s'han escrit (no hi havia Docker en marxa). Si alguna ordre falla, copia'm l'error.

## Si no et funciona
- *Caddy no treu certificat*: el DNS encara no apunta bé, o els ports 80/443 estan bloquejats. Mira `docker compose logs caddy`.
- *"Posa ADMIN_PASSWORD…"*: falta omplir `.env`.
- *La web carrega però no entra*: `docker compose logs api`.
