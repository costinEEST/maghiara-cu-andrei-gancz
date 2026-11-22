/* Classic worker: relative URLs keep each GitHub Pages project in its own scope. */
importScripts("./offline-assets.js");
const bundle = self.NEBULA_OFFLINE;
const base = self.registration.scope;
const prefix = `nebula-${encodeURIComponent(new URL(base).pathname)}-`;
const cacheName = prefix + bundle.version;
const absolute = (path) => new URL(path, base).href;
const assets = new Set(bundle.assets.map((entry) => absolute(entry.url)));
const shell = [
  "index.html",
  "offline.html",
  "manifest.webmanifest",
  "assets/site.css",
  "assets/site.js",
  "assets/pwa.js",
  "assets/fonts/literata/literata-latin-roman.e42c54d5.woff2",
  "assets/fonts/literata/literata-latin-italic.85368b48.woff2",
  "assets/favicon.svg",
  "assets/pwa/icon-192.png",
  "assets/pwa/icon-512.png",
  "assets/pwa/icon-maskable-512.png",
  "assets/pwa/apple-touch-icon.png",
];
let downloadJob;
let downloadController;

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(cacheName).then((cache) => cache.addAll(shell.map(absolute))));
});
self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const names = await caches.keys();
      await Promise.all(
        names
          .filter((name) => name.startsWith(prefix) && name !== cacheName)
          .map((name) => caches.delete(name)),
      );
      await self.clients.claim();
    })(),
  );
});

async function rangeResponse(response, range) {
  const match = /^bytes=(\d*)-(\d*)$/.exec(range);
  if (!match || (!match[1] && !match[2])) return new Response(null, { status: 416 });
  const data = await response.arrayBuffer();
  const size = data.byteLength;
  const start = match[1] ? Number(match[1]) : Math.max(0, size - Number(match[2]));
  const end = match[1] && match[2] ? Math.min(Number(match[2]), size - 1) : size - 1;
  if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start > end || start >= size) {
    return new Response(null, {
      status: 416,
      headers: { "Content-Range": `bytes */${size}` },
    });
  }
  return new Response(data.slice(start, end + 1), {
    status: 206,
    headers: {
      "Content-Type": response.headers.get("Content-Type") || "audio/mpeg",
      "Content-Range": `bytes ${start}-${end}/${size}`,
      "Content-Length": String(end - start + 1),
      "Accept-Ranges": "bytes",
    },
  });
}

async function offlineFallback(cache) {
  const saved = await cache.match(absolute("offline.html"));
  const html = saved
    ? (await saved.text()).replace("<head>", `<head><base href="${base}">`)
    : "Pagina nu este disponibilă offline.";
  return new Response(html, {
    status: 503,
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== new URL(base).origin || !url.href.startsWith(base))
    return;
  url.search = "";
  url.hash = "";
  if (url.href === base) url.pathname += "index.html";
  const key = url.href;
  const navigation = request.mode === "navigate";
  // Archive downloads and unknown resources are handled normally, not cached.
  if (!navigation && !assets.has(key)) return;
  event.respondWith(
    (async () => {
      const cache = await caches.open(cacheName);
      const saved = await cache.match(key);
      const range = request.headers.get("Range");
      if (range && saved) return rangeResponse(saved, range);
      if (!navigation && saved) return saved;
      try {
        const response = await fetch(request);
        if (response.status === 200 && assets.has(key) && !range) {
          // Keep the worker alive until a visited resource has really been saved.
          try {
            await cache.put(key, response.clone());
          } catch {
            // Storage limits must not prevent reading a successful online response.
          }
        }
        if (response.status >= 500 && saved) return saved;
        return response;
      } catch {
        if (saved) return saved;
        return navigation
          ? offlineFallback(cache)
          : new Response("Resursă nesalvată.", { status: 503 });
      }
    })(),
  );
});

async function cacheStatus() {
  const cache = await caches.open(cacheName);
  const keys = await cache.keys();
  const count = keys.filter((request) => assets.has(request.url)).length;
  return {
    count,
    total: assets.size,
    bytes: bundle.totalBytes,
    complete: count === assets.size,
  };
}

async function downloadCourse(port) {
  const send = (message) => port?.postMessage(message);
  downloadController = new AbortController();
  const controller = downloadController;
  const cache = await caches.open(cacheName);
  const initial = await cacheStatus();
  let count = initial.count;
  let position = 0;
  let failed = false;
  send({ type: "progress", count, total: assets.size });
  const entries = [...assets];
  try {
    await Promise.all(
      Array.from({ length: 4 }, async () => {
        while (position < entries.length && !controller.signal.aborted) {
          const url = entries[position++];
          if (await cache.match(url)) continue;
          try {
            const response = await fetch(url, {
              signal: controller.signal,
              cache: "reload",
            });
            if (response.status !== 200) throw new Error("Unavailable resource");
            await cache.put(url, response);
            count++;
            send({ type: "progress", count, total: assets.size });
          } catch {
            if (!controller.signal.aborted) failed = true;
            controller.abort();
            return;
          }
        }
      }),
    );
    const status = await cacheStatus();
    send({
      type: failed
        ? "error"
        : controller.signal.aborted
          ? "cancelled"
          : status.complete
            ? "complete"
            : "error",
      ...status,
    });
  } catch {
    send({ type: failed ? "error" : "cancelled", ...(await cacheStatus()) });
  } finally {
    if (downloadController === controller) downloadController = undefined;
  }
}

self.addEventListener("message", (event) => {
  const port = event.ports[0];
  if (event.data?.type === "SKIP_WAITING") {
    self.skipWaiting();
  } else if (event.data?.type === "GET_STATUS") {
    event.waitUntil(
      cacheStatus().then((status) => port?.postMessage({ type: "status", ...status })),
    );
  } else if (event.data?.type === "CANCEL_DOWNLOAD") {
    downloadController?.abort();
  } else if (event.data?.type === "CACHE_COURSE") {
    if (downloadJob) {
      port?.postMessage({ type: "busy" });
      return;
    }
    downloadJob = downloadCourse(port).finally(() => {
      downloadJob = undefined;
    });
    event.waitUntil(downloadJob);
  }
});
