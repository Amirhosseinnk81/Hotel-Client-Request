/*
 * Operator offline mode — service worker (registered by the operator
 * panel, production builds only).
 *
 * It only makes the APP load offline: build assets are cache-first, pages
 * and route payloads network-first with the last copy as fallback. It never
 * touches API calls (another origin): offline ticket data is handled by
 * lib/offline.ts in sessionStorage, where logout can wipe it. Caching the
 * API here would leave guests' ticket data in Cache Storage after logout.
 */
const VERSION = "hcr-shell-v1";

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== VERSION).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin) return;

  // Content-hashed build output never changes under the same URL.
  if (url.pathname.startsWith("/_next/static/")) {
    event.respondWith(
      caches.match(request).then(
        (hit) =>
          hit ||
          fetch(request).then((response) => {
            const copy = response.clone();
            caches.open(VERSION).then((cache) => cache.put(request, copy));
            return response;
          })
      )
    );
    return;
  }

  // Pages and client-side navigation payloads: fresh when possible.
  const isPage = request.mode === "navigate" || request.headers.get("RSC") === "1";
  if (!isPage) return;
  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(VERSION).then((cache) => cache.put(request, copy));
        }
        return response;
      })
      .catch(() =>
        caches
          .match(request)
          .then((hit) => hit || (request.mode === "navigate" ? caches.match("/operator") : undefined))
          .then((hit) => hit || Response.error())
      )
  );
});
