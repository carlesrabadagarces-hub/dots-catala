# Media

Deixa aquí els dos vídeos generats amb Higgsfield:

- `hero.mp4`: invasió de 30 s (Sagrada Família i carrers de Barcelona).
- `finale.mp4`: final de 10 s (el Dot salta al mig i la massa forma "superDOTats").

La pàgina els reprodueix un darrere l'altre com un sol vídeo. Si no hi són, intenta carregar-los dels enllaços directes de Higgsfield (només fora dels artifacts).

Per generar un únic MP4 de 40 s:

```
printf "file 'hero.mp4'\nfile 'finale.mp4'\n" > list.txt
ffmpeg -f concat -safe 0 -i list.txt -c copy superdotats.mp4
```
