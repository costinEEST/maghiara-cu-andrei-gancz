/* Installation and offline storage are optional enhancements to the static site. */
(() => {
  const script = document.currentScript;
  const root = new URL("../", script.src);
  const installButton = document.querySelector("[data-install-app]");
  const installStatus = document.querySelector("[data-install-status]");
  const downloadButton = document.querySelector("[data-download-course]");
  const cancelButton = document.querySelector("[data-cancel-download]");
  const updateButton = document.querySelector("[data-update-app]");
  const offlineStatus = document.querySelector("[data-offline-status]");
  const progress = document.querySelector("[data-offline-progress]");
  const nativeInstall = typeof navigator.install === "function";
  const standalone = () =>
    matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  let deferredPrompt;
  let registration;
  let refreshAfterUpdate = false;
  let downloading = false;
  let lastAnnouncement = 0;

  const installed = () => {
    if (installButton) installButton.hidden = true;
    if (installStatus)
      installStatus.textContent = "Site-ul este deschis din pictograma de pe acest dispozitiv.";
  };
  if (standalone()) installed();
  else if (installButton && nativeInstall && isSecureContext) installButton.hidden = false;
  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    deferredPrompt = event;
    if (installButton && !standalone()) installButton.hidden = false;
  });
  window.addEventListener("appinstalled", installed);
  installButton?.addEventListener("click", async () => {
    if (installButton.getAttribute("aria-disabled") === "true") return;
    installButton.setAttribute("aria-disabled", "true");
    try {
      if (nativeInstall) {
        // Keep this call inside the user gesture; do not await registration first.
        await navigator.install();
        installStatus.textContent = "Site-ul a fost adăugat pe ecranul principal sau deschis.";
        installButton.hidden = true;
      } else if (deferredPrompt) {
        const event = deferredPrompt;
        deferredPrompt = undefined;
        await event.prompt();
        const choice = await event.userChoice;
        installStatus.textContent =
          choice.outcome === "accepted"
            ? "Instalarea a fost acceptată."
            : "Instalarea a fost anulată.";
        if (!deferredPrompt) installButton.hidden = true;
      }
    } catch {
      installStatus.textContent = "Instalarea nu s-a încheiat. Poți folosi și meniul browserului.";
      if (!nativeInstall && !deferredPrompt) installButton.hidden = true;
    } finally {
      installButton.removeAttribute("aria-disabled");
    }
  });

  function receive(message) {
    if (!offlineStatus) return;
    if (message.type === "progress") {
      progress.hidden = false;
      progress.max = message.total;
      progress.value = message.count;
      if (Date.now() - lastAnnouncement > 1000) {
        offlineStatus.textContent = `Se salvează cursul: ${message.count} din ${message.total} fișiere.`;
        lastAnnouncement = Date.now();
      }
      return;
    }
    if (message.type === "status") {
      if (downloading) return;
      const mb = (message.bytes / 1_000_000).toLocaleString("ro", { maximumFractionDigits: 1 });
      offlineStatus.textContent = message.complete
        ? "Cursul este salvat pe acest dispozitiv: lecții, imagini și MP3."
        : `Poți salva întregul curs pentru offline (aproximativ ${mb} MB). Paginile vizitate se salvează automat.`;
      downloadButton.textContent = message.complete
        ? "Verifică salvarea offline"
        : "Salvează cursul offline";
    } else {
      downloading = false;
      downloadButton.removeAttribute("aria-disabled");
      cancelButton.hidden = true;
      progress.hidden = true;
      const endings = {
        complete:
          "Cursul este salvat. Poți deconecta internetul și deschide lecțiile, imaginile și înregistrările MP3.",
        cancelled:
          "Descărcarea a fost oprită. Fișierele deja salvate rămân disponibile; poți relua mai târziu.",
        error:
          "Cursul nu a fost salvat integral. Verifică legătura la internet și spațiul disponibil, apoi reia. Fișierele deja salvate se păstrează.",
        busy: "Salvarea este în curs într-o altă pagină a site-ului. Revino aici după finalizare.",
      };
      offlineStatus.textContent = endings[message.type] || "Starea salvării nu este disponibilă.";
    }
  }

  function send(type) {
    const worker = registration?.active;
    if (!worker) return;
    const channel = new MessageChannel();
    channel.port1.onmessage = (event) => {
      receive(event.data);
      if (event.data.type !== "progress") channel.port1.close();
    };
    worker.postMessage({ type }, [channel.port2]);
  }

  if (
    !("serviceWorker" in navigator) ||
    !isSecureContext ||
    !["http:", "https:"].includes(location.protocol)
  ) {
    if (offlineStatus)
      offlineStatus.textContent =
        "Pentru instalare și salvare offline, deschide site-ul prin HTTPS sau pe localhost într-un browser compatibil.";
    return;
  }
  downloadButton?.addEventListener("click", () => {
    if (downloading || downloadButton.getAttribute("aria-disabled") === "true") return;
    downloading = true;
    lastAnnouncement = 0;
    downloadButton.setAttribute("aria-disabled", "true");
    cancelButton.hidden = false;
    send("CACHE_COURSE");
  });
  cancelButton?.addEventListener("click", () => {
    registration?.active?.postMessage({ type: "CANCEL_DOWNLOAD" });
  });
  updateButton?.addEventListener("click", () => {
    if (!registration?.waiting) return;
    refreshAfterUpdate = true;
    registration.waiting.postMessage({ type: "SKIP_WAITING" });
  });
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (refreshAfterUpdate) location.reload();
  });
  navigator.serviceWorker
    .register(new URL("sw.js", root), { scope: root.href, updateViaCache: "none" })
    .then(async (result) => {
      registration = result;
      const offerUpdate = () => {
        if (registration.waiting && updateButton) updateButton.hidden = false;
      };
      offerUpdate();
      registration.addEventListener("updatefound", () => {
        registration.installing?.addEventListener("statechange", offerUpdate);
      });
      if (!registration.active) {
        const worker = registration.installing || registration.waiting;
        if (!worker) throw new Error("Worker unavailable");
        await new Promise((resolve, reject) => {
          const changed = () => {
            if (worker.state === "activated" || worker.state === "redundant") {
              worker.removeEventListener("statechange", changed);
              worker.state === "activated" ? resolve() : reject(new Error("Worker unavailable"));
            }
          };
          worker.addEventListener("statechange", changed);
          changed();
        });
      }
      if (downloadButton) {
        downloadButton.disabled = false;
        send("GET_STATUS");
      }
    })
    .catch(() => {
      if (offlineStatus)
        offlineStatus.textContent =
          "Salvarea offline nu este disponibilă acum. Poți continua să folosești site-ul și să reîncerci după reconectare.";
    });
})();
