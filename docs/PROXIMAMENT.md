# Mode «Pròximament» de la web

Mentre l'app no s'obre al públic, la web (la carpeta `site/`) pot dir que els superDOTats arriben aviat i recollir correus en una llista d'espera.

## Què canvia amb `COMING_SOON=1`
- Els botons «Entra» i «Entra i comença» passen a «Avisa'm quan surti» i porten al formulari.
- El títol de la portada diu «Molt aviat · Privat · Segur · Fàcil».
- Apareix la secció **Els superDOTats arriben aviat** amb el formulari (correu, quin Dot t'agradaria i casella de consentiment).
- A les preguntes freqüents hi ha una de nova: «Quan estarà disponible?».
- Les pàgines de cada Dot, `llms.txt` i el menú també diuen que és pròximament.

## Construir-la
```
COMING_SOON=1 WAITLIST_URL=https://formspree.io/f/xxxxxxx \
SITE_URL=https://superdots.vercel.app PRIVATE=1 sh site/build.sh
```
Quan tinguis el domini de debò, treu `PRIVATE=1` i posa-hi `SITE_URL=https://el-teu-domini`.

## On van els correus
Una web estàtica no pot desar res per ella mateixa. Tens dues opcions:

1. **`WAITLIST_URL` (recomanat).** Crea un formulari gratuït a [Formspree](https://formspree.io) (o un servei equivalent) i copia'n l'adreça `https://formspree.io/f/…`. Els correus t'arriben a la safata i en pots descarregar la llista. El formulari envia un JSON amb `email`, `idea` i `source`.
2. **`CONTACT_EMAIL`.** El formulari obre el correu de la persona amb un missatge preparat cap a aquesta adreça. És més pesat per a qui s'apunta i no garanteix que enviï el missatge.

Si no n'hi poses cap, es mostren dos botons que porten a X: **Segueix @carlesrgm** (`X_HANDLE`, per defecte `carlesrgm`) i **Escriu-nos «avisa'm»**, que obre una publicació preparada que l'esmenta. No es recull cap correu; només tindràs seguidors i mencions.

## Privacitat
La casella de consentiment diu que només es farà servir el correu per avisar del llançament. Abans de recollir correus de debò afegeix una pàgina de privacitat (responsable, finalitat, com esborrar-se) i fes servir només per avisar el que hi diu.

## Tornar a obrir l'app
Construeix sense `COMING_SOON`, amb `APP_URL=https://app.el-teu-domini`.
