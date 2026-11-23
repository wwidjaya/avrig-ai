/* Shared chrome behaviour: theme, language, version. Every surface loads this
   after its own inline PAGE_COPY, so page strings and base strings merge here. */
(function () {
  // Port note: in the app this is __APP_VERSION__ (apps/web/vite.config.ts).
  // The prototype has no build, so the value is pinned to the shipped version.
  var VERSION = "0.6.0";

  var BASE_COPY = {
    en: {
      skip: "Skip to content",
      "theme.light": "Light",
      "theme.dark": "Dark",
      "theme.system": "System",
      "chrome.colourTheme": "Colour theme",
      "chrome.language": "Language",
      "chrome.version": "Product version",
      "chrome.changeTo": "Change to",
      "lang.name.en": "English",
      "lang.name.id": "Bahasa Indonesia",
      "lang.short.en": "EN",
      "lang.short.id": "ID",
    },
    id: {
      skip: "Lewati ke konten",
      "theme.light": "Terang",
      "theme.dark": "Gelap",
      "theme.system": "Sistem",
      "chrome.colourTheme": "Tema warna",
      "chrome.language": "Bahasa",
      "chrome.version": "Versi produk",
      "chrome.changeTo": "Ganti ke",
      "lang.name.en": "English",
      "lang.name.id": "Bahasa Indonesia",
      "lang.short.en": "EN",
      "lang.short.id": "ID",
    },
  };

  // Light, then system, then dark, and back: one button walks the three.
  var THEME_ORDER = ["light", "system", "dark"];
  var THEME_ICON = {
    light: '<circle cx="12" cy="12" r="4.2"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M18.4 5.6 17 7M7 17l-1.4 1.4"/>',
    system: '<rect x="3" y="4" width="18" height="12" rx="1.6"/><path d="M9 20h6M12 16v4"/>',
    dark: '<path d="M20 14.5A8.2 8.2 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5Z"/>',
  };
  var LANG_ICON =
    '<circle cx="12" cy="12" r="9"/><path d="M3 12h18"/>' +
    '<path d="M12 3c2.5 2.4 3.9 5.5 3.9 9s-1.4 6.6-3.9 9c-2.5-2.4-3.9-5.5-3.9-9s1.4-6.6 3.9-9Z"/>';

  var PAGE_COPY = window.PAGE_COPY || { en: {}, id: {} };

  var store = {
    get: function (key, fallback) {
      try { return localStorage.getItem(key) || fallback; } catch (error) { return fallback; }
    },
    set: function (key, value) {
      try { localStorage.setItem(key, value); } catch (error) {}
    },
  };

  var lang = store.get("avrig-lang", "en");
  if (!BASE_COPY[lang]) lang = "en";
  var theme = store.get("avrig-theme", "system");
  if (["light", "dark", "system"].indexOf(theme) === -1) theme = "system";

  function lookup(key, locale) {
    var page = PAGE_COPY[locale] || {};
    if (Object.prototype.hasOwnProperty.call(page, key)) return page[key];
    var base = BASE_COPY[locale] || {};
    if (Object.prototype.hasOwnProperty.call(base, key)) return base[key];
    return null;
  }

  function t(key) {
    return lookup(key, lang) || lookup(key, "en") || key;
  }

  function themeName(choice) { return t("theme." + choice); }

  function nextTheme() {
    return THEME_ORDER[(THEME_ORDER.indexOf(theme) + 1) % THEME_ORDER.length];
  }

  // One button per control. It shows the state in force and names the state a
  // click moves to, so the visible word and the announced label always agree.
  function renderControls() {
    var themeButton = document.getElementById("theme-tg");
    if (themeButton) {
      var upcoming = nextTheme();
      themeButton.querySelector(".tg-icon").innerHTML =
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true">' +
        THEME_ICON[theme] + "</svg>";
      var themeLabel = t("chrome.colourTheme") + ": " + themeName(theme) + ". " +
        t("chrome.changeTo") + " " + themeName(upcoming) + ".";
      themeButton.setAttribute("aria-label", themeLabel);
      themeButton.title = themeLabel;
    }

    var langButton = document.getElementById("lang-tg");
    if (langButton) {
      var other = lang === "en" ? "id" : "en";
      langButton.querySelector(".tg-icon").innerHTML =
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true">' +
        LANG_ICON + "</svg>";
      langButton.querySelector(".tg-label").textContent = t("lang.short." + lang);
      var langLabel = t("chrome.language") + ": " + t("lang.name." + lang) + ". " +
        t("chrome.changeTo") + " " + t("lang.name." + other) + ".";
      langButton.setAttribute("aria-label", langLabel);
      langButton.title = langLabel;
    }
  }

  function setTheme(choice, persist) {
    theme = choice;
    // Storage means "the user chose this". The load path applies the choice
    // without writing, so an untouched page keeps no stored value.
    if (persist !== false) store.set("avrig-theme", choice);
    var dark = choice === "dark" ||
      (choice === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    document.documentElement.style.colorScheme = dark ? "dark" : "light";
    renderControls();
  }

  function setLang(next) {
    if (!BASE_COPY[next]) return;
    lang = next;
    store.set("avrig-lang", next);
    applyCopy();
  }

  function applyCopy() {
    document.documentElement.lang = lang;
    var nodes = document.querySelectorAll("[data-i18n]");
    for (var i = 0; i < nodes.length; i++) nodes[i].textContent = t(nodes[i].dataset.i18n);

    var versions = document.querySelectorAll("[data-version]");
    for (var v = 0; v < versions.length; v++) versions[v].textContent = "v" + VERSION;

    renderControls();
    document.dispatchEvent(new CustomEvent("avrig:copy", { detail: { lang: lang } }));
  }

  // Each control is a single button: click walks to the next choice.
  var themeButton = document.getElementById("theme-tg");
  if (themeButton) {
    themeButton.addEventListener("click", function () { setTheme(nextTheme()); });
  }
  var langButton = document.getElementById("lang-tg");
  if (langButton) {
    langButton.addEventListener("click", function () {
      setLang(lang === "en" ? "id" : "en");
    });
  }

  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function () {
    if (theme === "system") setTheme("system");
  });

  window.avrig = {
    version: VERSION,
    t: t,
    lang: function () { return lang; },
    theme: function () { return theme; },
    setLang: setLang,
    setTheme: setTheme,
  };

  setTheme(theme, false);
  applyCopy();
})();
