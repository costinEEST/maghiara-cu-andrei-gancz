import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";
import vm from "node:vm";
import { buildManifest, projectRoot } from "./build-offline.mjs";

const scope = "https://example.test/course/";
const workerSource = await readFile(resolve(projectRoot, "sw.js"), "utf8");
const files = ["index.html", "offline.html", "lesson.html", "audio.mp3"];

function worker() {
  const listeners = {};
  const stores = new Map();
  let network = async () => new Response("network");
  const caches = {
    async keys() {
      return [...stores.keys()];
    },
    async delete(name) {
      return stores.delete(name);
    },
    async open(name) {
      if (!stores.has(name)) stores.set(name, new Map());
      const entries = stores.get(name);
      return {
        async match(key) {
          return entries.get(typeof key === "string" ? key : key.url)?.clone();
        },
        async put(key, value) {
          entries.set(typeof key === "string" ? key : key.url, value.clone());
        },
        async keys() {
          return [...entries.keys()].map((url) => ({ url }));
        },
        async addAll(urls) {
          const responses = await Promise.all(urls.map((url) => network(url)));
          if (responses.some((response) => !response.ok)) throw new Error("Install failed");
          urls.forEach((url, index) => entries.set(url, responses[index].clone()));
        },
      };
    },
  };
  const self = {
    registration: { scope },
    clients: { async claim() {} },
    addEventListener(type, handler) {
      listeners[type] = handler;
    },
    skipWaiting() {},
  };
  vm.runInNewContext(workerSource, {
    self,
    caches,
    URL,
    Response,
    AbortController,
    fetch: (...args) => network(...args),
    importScripts() {
      self.NEBULA_OFFLINE = {
        version: "test",
        totalBytes: 100,
        assets: files.map((url) => ({ url })),
      };
    },
  });
  return {
    stores,
    caches,
    network(fn) {
      network = fn;
    },
    async seed(path, body, headers = {}) {
      const cache = await caches.open("nebula-%2Fcourse%2F-test");
      await cache.put(new URL(path, scope).href, new Response(body, { headers }));
    },
    fetch(path, { mode = "navigate", method = "GET", headers = {} } = {}) {
      let response;
      listeners.fetch({
        request: { url: new URL(path, scope).href, mode, method, headers: new Headers(headers) },
        respondWith(promise) {
          response = promise;
        },
      });
      return response;
    },
    async event(type, data) {
      const pending = [];
      const messages = [];
      listeners[type]({
        data,
        ports: [
          {
            postMessage(message) {
              messages.push(message);
            },
          },
        ],
        waitUntil(promise) {
          pending.push(promise);
        },
      });
      await Promise.all(pending);
      return messages;
    },
  };
}

test("offline inventory covers every page, uses local assets and excludes archives", async () => {
  const bundle = await buildManifest();
  const urls = new Set(bundle.assets.map((entry) => entry.url));
  const inventory = JSON.parse(
    await readFile(resolve(projectRoot, "assets/inventory.json"), "utf8"),
  );
  assert.equal(bundle.assets.filter((entry) => entry.url.endsWith(".mp3")).length, 131);
  assert.ok(urls.has("offline.html"));
  for (const font of [
    "literata-latin-roman.e42c54d5.woff2",
    "literata-latin-italic.85368b48.woff2",
    "OFL.txt",
  ]) {
    assert.ok(urls.has(`assets/fonts/literata/${font}`), font);
  }
  assert.ok(![...urls].some((url) => /\.rar$|\.zip$|^https?:/.test(url)));
  for (const page of [
    "index.html",
    "referinte/despre-editie.html",
    ...inventory.pages.map((page) => page.path),
  ]) {
    assert.ok(urls.has(page), page);
    const html = await readFile(resolve(projectRoot, page), "utf8");
    assert.match(html, /rel="manifest"/);
    assert.match(html, /assets\/pwa\.js/);
  }
  for (const icon of [
    "icon-192.png",
    "icon-512.png",
    "icon-maskable-512.png",
    "apple-touch-icon.png",
  ]) {
    const bytes = await readFile(resolve(projectRoot, "assets/pwa", icon));
    assert.equal(
      bytes.readUInt32BE(16),
      icon.includes("192") ? 192 : icon.includes("512") ? 512 : 180,
    );
  }
});

test("saved lessons remain readable offline; missing nested pages receive a usable fallback", async () => {
  const app = worker();
  app.network(async () => {
    throw new Error("offline");
  });
  await app.seed("lesson.html", "saved lesson");
  await app.seed("offline.html", "<html><head></head><body>offline</body></html>");
  assert.equal(await (await app.fetch("lesson.html?search=1")).text(), "saved lesson");
  const missing = await app.fetch("nested/missing.html");
  assert.equal(missing.status, 503);
  assert.match(await missing.text(), /<base href="https:\/\/example.test\/course\/">/);
});

test("cached audio supports byte ranges, suffix ranges and invalid positions", async () => {
  const app = worker();
  await app.seed("audio.mp3", "0123456789", { "Content-Type": "audio/mpeg" });
  const request = (range) => app.fetch("audio.mp3", { mode: "cors", headers: { Range: range } });
  const partial = await request("bytes=2-5");
  assert.equal(partial.status, 206);
  assert.equal(partial.headers.get("Content-Range"), "bytes 2-5/10");
  assert.equal(await partial.text(), "2345");
  assert.equal(await (await request("bytes=-3")).text(), "789");
  assert.equal((await request("bytes=50-")).status, 416);
  assert.equal((await request("bytes=1-2,4-5")).status, 416);
});

test("external requests, other projects, writes and original archives bypass the worker", () => {
  const app = worker();
  assert.equal(app.fetch("https://elsewhere.test/course/lesson.html"), undefined);
  assert.equal(app.fetch("../other/index.html"), undefined);
  assert.equal(app.fetch("lesson.html", { method: "POST" }), undefined);
  assert.equal(app.fetch("original.rar", { mode: "cors" }), undefined);
});

test("activation removes only obsolete caches for this project", async () => {
  const app = worker();
  await app.caches.open("nebula-%2Fcourse%2F-old");
  await app.caches.open("nebula-%2Fother%2F-old");
  await app.caches.open("another-app");
  await app.caches.open("nebula-%2Fcourse%2F-test");
  await app.event("activate");
  assert.deepEqual(await app.caches.keys(), [
    "nebula-%2Fother%2F-old",
    "another-app",
    "nebula-%2Fcourse%2F-test",
  ]);
});

test("failed installation preserves the previous usable cache", async () => {
  const app = worker();
  await app.caches.open("nebula-%2Fcourse%2F-old");
  app.network(async () => new Response("missing", { status: 404 }));
  await assert.rejects(app.event("install"), /Install failed/);
  assert.ok((await app.caches.keys()).includes("nebula-%2Fcourse%2F-old"));
});

test("bulk download reports completion only after all resources are cached", async () => {
  const app = worker();
  await app.seed("index.html", "saved");
  let calls = 0;
  app.network(async () => {
    calls++;
    return new Response("file");
  });
  const messages = await app.event("message", { type: "CACHE_COURSE" });
  assert.equal(messages.at(-1).type, "complete");
  assert.equal(messages.at(-1).count, files.length);
  assert.equal(calls, files.length - 1);
  const again = await app.event("message", { type: "CACHE_COURSE" });
  assert.equal(again.at(-1).type, "complete");
  assert.equal(calls, files.length - 1);
});

test("failed bulk download never reports success and can resume", async () => {
  const app = worker();
  await app.seed("index.html", "saved");
  app.network(async () => new Response("failure", { status: 503 }));
  const messages = await app.event("message", { type: "CACHE_COURSE" });
  assert.equal(messages.at(-1).type, "error");
  assert.equal(messages.at(-1).complete, false);
  assert.equal(messages.at(-1).count, 1);
  app.network(async () => new Response("available"));
  assert.equal((await app.event("message", { type: "CACHE_COURSE" })).at(-1).type, "complete");
});

test("cancelled download retains partial progress and can resume", async () => {
  const app = worker();
  await app.seed("index.html", "saved");
  app.network(
    (_url, { signal }) =>
      new Promise((_resolve, reject) => {
        signal.addEventListener("abort", () => reject(new Error("cancelled")), { once: true });
      }),
  );
  const download = app.event("message", { type: "CACHE_COURSE" });
  // Let asynchronous cache lookups finish before cancelling active fetches.
  await new Promise((resolve) => setImmediate(resolve));
  await app.event("message", { type: "CANCEL_DOWNLOAD" });
  const messages = await download;
  assert.equal(messages.at(-1).type, "cancelled");
  assert.equal(messages.at(-1).count, 1);
  app.network(async () => new Response("available"));
  assert.equal((await app.event("message", { type: "CACHE_COURSE" })).at(-1).type, "complete");
});

const installSource = await readFile(resolve(projectRoot, "assets/pwa.js"), "utf8");
function installUI(nativeInstall) {
  const events = {};
  const clicks = {};
  const elements = new Map();
  for (const name of ["install-app", "install-status", "offline-status"]) {
    const attrs = new Map();
    elements.set(`[data-${name}]`, {
      hidden: name === "install-app",
      textContent: "",
      getAttribute(key) {
        return attrs.get(key) ?? null;
      },
      setAttribute(key, value) {
        attrs.set(key, value);
      },
      removeAttribute(key) {
        attrs.delete(key);
      },
      addEventListener(type, callback) {
        clicks[name] = callback;
      },
    });
  }
  vm.runInNewContext(installSource, {
    document: {
      currentScript: { src: scope + "assets/pwa.js" },
      querySelector(selector) {
        return elements.get(selector) ?? null;
      },
    },
    navigator: nativeInstall ? { install: nativeInstall } : {},
    URL,
    isSecureContext: true,
    location: { protocol: "https:" },
    matchMedia() {
      return { matches: false };
    },
    window: {
      addEventListener(type, callback) {
        events[type] = callback;
      },
    },
  });
  return {
    button: elements.get("[data-install-app]"),
    status: elements.get("[data-install-status]"),
    offer(event) {
      events.beforeinstallprompt({ preventDefault() {}, ...event });
    },
    click() {
      return clicks["install-app"]();
    },
  };
}

test("install button stays hidden when neither installation API is available", () => {
  assert.equal(installUI().button.hidden, true);
});

test("single-use install prompt is cleared on dismissal and on failure", async () => {
  for (const failure of [false, true]) {
    const ui = installUI();
    let count = 0;
    ui.offer({
      async prompt() {
        count++;
        if (failure) throw new Error("expired");
      },
      userChoice: Promise.resolve({ outcome: "dismissed" }),
    });
    assert.equal(ui.button.hidden, false);
    await ui.click();
    assert.equal(ui.button.hidden, true);
    assert.equal(ui.button.getAttribute("aria-disabled"), null);
    await ui.click();
    assert.equal(count, 1);
  }
});

test("native install remains available after cancellation and cleans up its busy state", async () => {
  let calls = 0;
  const ui = installUI(async () => {
    calls++;
    throw new Error("cancelled");
  });
  assert.equal(ui.button.hidden, false);
  await ui.click();
  assert.equal(calls, 1);
  assert.equal(ui.button.hidden, false);
  assert.equal(ui.button.getAttribute("aria-disabled"), null);
  assert.match(ui.status.textContent, /nu s-a încheiat/);
});
