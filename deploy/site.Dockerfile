# Builds the landing (with your real addresses) and serves it, together with the app, through Caddy.
FROM node:20-bookworm-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends python3 && rm -rf /var/lib/apt/lists/*
ARG SITE_URL
ARG APP_URL
WORKDIR /src
COPY server/app server/app
COPY client/lib client/lib
COPY site site
RUN SITE_URL="$SITE_URL" APP_URL="$APP_URL" sh site/build.sh

FROM caddy:2-alpine
COPY --from=build /src/site /srv/site
COPY deploy/Caddyfile /etc/caddy/Caddyfile
