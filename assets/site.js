/* Progressive enhancements; all reading and navigation work without JavaScript. */
document.documentElement.classList.add("js");
const normalize = (value) =>
  value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("ro")
    .trim();
const search = document.querySelector("#search");
if (search) {
  search.closest(".search-box").hidden = false;
  const entries = [...document.querySelectorAll("[data-entry]")];
  const sections = [...document.querySelectorAll("[data-section]")];
  const index = entries.map((entry) => {
    const number = entry.querySelector(".item-number")?.textContent.trim();
    const lesson = entry.closest("#lectii, #andras") && Number(number);
    return {
      entry,
      text: normalize(`${entry.dataset.search} ${lesson ? `Lecția ${lesson}` : ""}`).replace(
        /familia/g,
        "familia familie",
      ),
    };
  });
  const status = document.querySelector("#search-status");
  let timer;
  search.addEventListener("input", () => {
    const query = normalize(search.value);
    const lesson = query.match(/\blectia\s+(\d+)\b/);
    const lessonPattern = lesson ? new RegExp(`\\blectia 0*${Number(lesson[1])}\\b`) : null;
    const words = query
      .replace(/\blectia\s+\d+\b/, "")
      .split(/\s+/)
      .filter(Boolean);
    let count = 0;
    index.forEach(({ entry, text }) => {
      entry.hidden =
        (lessonPattern !== null && !lessonPattern.test(text)) ||
        !words.every((word) => text.includes(word));
      if (!entry.hidden) count++;
    });
    sections.forEach((section) => {
      section.hidden = ![...section.querySelectorAll("[data-entry]")].some(
        (entry) => !entry.hidden,
      );
      const disclosure = section.querySelector(":scope > details");
      if (disclosure) disclosure.open = Boolean(query);
    });
    document.querySelector(".empty-state").hidden = count !== 0;
    clearTimeout(timer);
    timer = setTimeout(() => {
      status.textContent = query ? `${count} materiale găsite.` : "";
    }, 200);
  });
}
// Accents matter in Hungarian: ő and ö must never be treated as equivalent.
const normalizeAnswer = (value) =>
  value.normalize("NFC").toLocaleLowerCase("hu").replace(/\s+/g, " ").trim();
const resizeCloze = (field) => {
  const minimum = field.tagName === "SELECT" ? 6 : 12;
  const length = [...field.value.normalize("NFC")].length + 2;
  field.style.setProperty("--gap-width", `${Math.max(minimum, Math.min(60, length))}ch`);
};
document.querySelectorAll(".cloze-input, select[data-cloze]").forEach((field) => {
  resizeCloze(field);
  field.addEventListener("input", () => resizeCloze(field));
  field.addEventListener("change", () => resizeCloze(field));
});
const check = document.querySelector("[data-check]");
if (check) {
  const fields = [...document.querySelectorAll("[data-answers]")];
  const status = document.querySelector(".feedback");
  const descriptions = new Map(
    fields.map((field) => [field, field.getAttribute("aria-describedby")]),
  );
  const focusAnswer = (field) => {
    const target = field.matches("[data-choice]")
      ? field.querySelector("input:checked") || field.querySelector("input")
      : field;
    target?.focus();
  };
  const clear = () => {
    document.querySelectorAll(".answer-result").forEach((node) => node.remove());
    fields.forEach((field) => {
      field.removeAttribute("aria-invalid");
      const description = descriptions.get(field);
      if (description) field.setAttribute("aria-describedby", description);
      else field.removeAttribute("aria-describedby");
    });
    status.textContent = "";
  };
  check.addEventListener("click", () => {
    clear();
    let correct = 0,
      answered = 0,
      checked = 0;
    fields.forEach((field, i) => {
      const solutions = JSON.parse(field.dataset.answers);
      if (!solutions.length) return;
      checked++;
      const selected = field.matches("[data-choice]")
        ? field.querySelector("input:checked")?.value || ""
        : field.value;
      const value = normalizeAnswer(selected);
      if (value) answered++;
      const valid = solutions.some((solution) => normalizeAnswer(solution) === value);
      if (valid) correct++;
      const result = document.createElement("span");
      result.className = "answer-result";
      result.lang = "ro";
      result.id = `rezultat-${i}`;
      result.dataset.correct = String(valid);
      result.textContent = valid
        ? "Corect."
        : value
          ? "Încearcă din nou. Verifică și accentele."
          : field.matches("[data-choice]")
            ? "Alege o variantă."
            : "Completează acest răspuns.";
      field.setAttribute("aria-invalid", String(!valid));
      field.setAttribute(
        "aria-describedby",
        [descriptions.get(field), result.id].filter(Boolean).join(" "),
      );
      if (field.matches("[data-choice]")) field.append(result);
      else if (field.matches(".cloze-input, select[data-cloze]")) {
        const host = field.closest(".cloze-item, td, p") || field.parentElement;
        if (valid) result.classList.add("visually-hidden");
        else {
          const link = document.createElement("a");
          link.href = `#${field.id}`;
          const number = field.id.match(/\d+$/);
          link.textContent = number ? `Spațiul ${Number(number[0]) + 1}` : "Răspuns";
          result.prepend(link, ": ");
        }
        host.append(result);
      } else field.insertAdjacentElement("afterend", result);
    });
    status.textContent = `${correct} din ${checked} răspunsuri corecte.${answered < checked ? " Mai sunt răspunsuri necompletate." : ""}`;
    const invalid = fields.find((field) => field.getAttribute("aria-invalid") === "true");
    if (invalid) focusAnswer(invalid);
  });
  document.querySelector("[data-reset]").addEventListener("click", () => {
    clear();
    fields.forEach((field) => {
      if (field.matches("[data-choice]")) {
        field.querySelectorAll("input").forEach((radio) => {
          radio.checked = false;
        });
      } else field.value = "";
      if (field.matches(".cloze-input, select[data-cloze]")) resizeCloze(field);
    });
    document.querySelectorAll(".solutions").forEach((details) => {
      details.open = false;
    });
    if (fields[0]) focusAnswer(fields[0]);
  });
}
document.addEventListener(
  "play",
  (event) => {
    if (event.target.tagName === "AUDIO")
      document.querySelectorAll("audio").forEach((audio) => {
        if (audio !== event.target) audio.pause();
      });
  },
  true,
);
document.querySelectorAll("[data-quiz]").forEach((button) => {
  button.addEventListener("click", () => {
    const prefix = "q" + button.dataset.quiz;
    const fields = [...document.querySelectorAll("select[id]")]
      .filter(
        (field) => field.id.startsWith(prefix) && /^[a-z]$/.test(field.id.slice(prefix.length)),
      )
      .sort((a, b) => a.id.localeCompare(b.id));
    const status = document.getElementById(prefix);
    if (!status) return;
    if (!fields.length || fields.some((field) => !field.value || field.value === "0")) {
      status.textContent = "Completează toate spațiile.";
      return;
    }
    const guess = "#" + fields.map((field) => field.value).join("") + "#";
    status.textContent = button.dataset.answer.includes(guess) ? "Corect." : "Încearcă din nou.";
  });
});
