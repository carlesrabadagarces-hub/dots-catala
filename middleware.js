/* Demana usuari i contrasenya abans de servir res.
   La contrasenya es posa a Vercel com a variable d'entorn SITE_PASSWORD
   (i, si vols, SITE_USER; per defecte l'usuari és "dots"). Només ASCII. */

export const config = { matcher: "/((?!_vercel/).*)" };

export default function middleware(request) {
  const password = process.env.SITE_PASSWORD;
  if (!password) {
    return new Response("Falta la variable SITE_PASSWORD al projecte de Vercel.", {
      status: 503,
      headers: { "content-type": "text/plain; charset=utf-8" },
    });
  }
  const user = process.env.SITE_USER || "dots";
  const given = request.headers.get("authorization") || "";
  if (given === "Basic " + btoa(user + ":" + password)) return;   // endavant
  return new Response("Aquesta web és privada.", {
    status: 401,
    headers: {
      "WWW-Authenticate": 'Basic realm="superDOTats", charset="UTF-8"',
      "content-type": "text/plain; charset=utf-8",
    },
  });
}
