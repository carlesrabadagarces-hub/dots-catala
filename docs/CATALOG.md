# Catàleg de Dots

Més de 80 agents llestos per a tots els sectors: educació, salut, legal i fiscal, oficis i llar, negoci i màrqueting, hostaleria, tecnologia, vida quotidiana, administració i camp/indústria/transport.

## Com estan fets
Cada Dot és una fitxa compacta a `server/app/services/catalog_data.py` (ofici, caràcter, coneixements, tasques, preguntes d'exemple i límits). `catalog_service.build_prompt` la converteix en un prompt complet amb el mateix mètode per a tots:
- Entendre l'objectiu i fer com a màxim dues preguntes si falta informació.
- Conclusió primer, després el perquè, i el següent pas concret.
- Opcions amb avantatges i inconvenients quan hi ha decisions.
- Distingir el que sap del que suposa; no inventar dades, fonts, lleis, dosis ni preus.
- Revisar la resposta abans d'enviar-la i corregir-se si s'equivoca.
- Regles de seguretat per sector (salut: no diagnostica i 112; legal: sense inventar terminis; oficis: gas i electricitat només per a professionals, etc.) i quan derivar a un professional.
- Format pensat per a WhatsApp: text pla, curt, en català.

## API
- `GET /api/v1/catalog?sector=&q=` llista de Dots.
- `GET /api/v1/catalog/sectors` sectors amb recompte.
- `POST /api/v1/catalog/{id}/install` afegeix el Dot al compte de la persona.
- `POST /api/v1/catalog/generate` `{ "description": "..." }` dissenya un Dot nou amb el model configurat (nom, coneixements, límits, exemples) i l'afegeix. També hi ha el Dot «Creador de Dots» al catàleg per fer-ho en xat.

## Afegir-ne més
Afegeix una crida `A(...)` a `CATALOG`, executa `python -m unittest discover -s tests` (comprova cobertura, prompts complets i ids únics) i `python scripts/export_catalog.py` per actualitzar el web.

## Limitacions
- Són orientacions generals: no substitueixen un metge, advocat ni tècnic habilitat, i els prompts ho diuen.
- Els Dots són tan bons com el model que hi hagi configurat. Els prompts no s'han avaluat contra models reals, només amb tests de forma i contingut.
