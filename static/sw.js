const CACHE = "sbeup-v1";
const STATIC_FILES = ["/static/index.html", "/offline"];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(STATIC_FILES))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (url.pathname === "/" || url.pathname === "/static/index.html") {
    e.respondWith(
      caches.match("/static/index.html").then((cached) => cached || fetch(e.request))
    );
    return;
  }
  if (url.pathname.startsWith("/api") || url.pathname.startsWith("/ciudadanos") || url.pathname.startsWith("/busqueda") || url.pathname === "/health") {
    e.respondWith(
      fetch(e.request).catch(() => new Response(
        JSON.stringify({ error: "Sin conexión al servidor" }),
        { status: 503, headers: { "Content-Type": "application/json" } }
      ))
    );
    return;
  }
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request))
  );
});
