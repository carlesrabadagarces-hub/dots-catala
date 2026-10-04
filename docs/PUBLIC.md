# Provar superDOTats en públic (sense servidor ni domini)

`./public.sh` obre l'app des del teu ordinador a una adreça `https://….trycloudflare.com`. Qualsevol persona amb l'enllaç hi pot crear un compte. Mentre no aturis l'script, el teu ordinador és el servidor.

## Requisits (un cop)
```
brew install cloudflared python@3.12 node
```

## Passos
1. `git pull origin claude/open-dots-whatsapp-integration-hn623w`
2. `./public.sh`
3. Espera uns minuts (el primer cop instal·la i compila). Al final surt un quadre amb:
   - l'**enllaç públic**,
   - el panell d'admin (`/admin`), usuari `admin` i una **contrasenya generada**. Si en vols una de pròpia: `ADMIN_PASSWORD=la-teva-1234 ./public.sh`.
4. Obre l'enllaç, crea't un compte i a Configuració → Model provider tria Groq i posa la teva clau.
5. Passa l'enllaç a qui vulguis. Cada persona es crea el seu compte i posa la seva pròpia clau de model.
6. `Ctrl+C` ho atura tot i l'enllaç deixa de funcionar.

## Què cal saber
- **L'enllaç canvia cada cop** que l'engegues. És una adreça de prova.
- **No posis `MODEL_API_KEY` al servidor** en aquest mode: així ningú gasta la teva clau. Cadascú porta la seva.
- Si tanques el portàtil o dorm, l'app s'atura.
- Comptes, Dots i converses es guarden al teu ordinador (`~/.open-dots`).
- WhatsApp: Meta necessita una adreça fixa. Per al WhatsApp de debò cal un servidor permanent o un túnel amb nom; l'adreça temporal serveix per fer una prova ràpida, però s'ha de tornar a posar a Meta cada cop.
- No hi ha correu de verificació ni de recuperar contrasenya.
- Tanca els registres amb `SIGNUP_OPEN=0` si ja no vols gent nova.
