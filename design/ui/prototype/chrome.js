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

  // Shared fine vertical scrollbar reveal: hidden in static state, shown on scroll or right-edge hover
  if (!window.__avrigSbInit) {
    window.__avrigSbInit = true;
    var hotEl = null;
    var sbTimers = new WeakMap();
    document.addEventListener("mousemove", function (event) {
      var el = event.target;
      var found = null;
      while (el && el !== document.body && el !== document.documentElement) {
        if (el.scrollHeight > el.clientHeight + 2) {
          var rect = el.getBoundingClientRect();
          if (event.clientX >= rect.right - 28 && event.clientX <= rect.right + 4) {
            found = el;
            break;
          }
        }
        el = el.parentElement;
      }
      if (!found && document.documentElement.scrollHeight > document.documentElement.clientHeight + 2) {
        if (event.clientX >= window.innerWidth - 28) found = document.documentElement;
      }
      if (hotEl && hotEl !== found) hotEl.removeAttribute("data-sb-hot");
      if (found) found.setAttribute("data-sb-hot", "true");
      hotEl = found;
    }, { passive: true });
    document.addEventListener("scroll", function (event) {
      var target = event.target === document ? document.documentElement : event.target;
      if (!target || target.nodeType !== 1 || target.scrollHeight <= target.clientHeight + 2) return;
      target.setAttribute("data-sb-scrolling", "true");
      var prev = sbTimers.get(target);
      if (prev) clearTimeout(prev);
      sbTimers.set(target, setTimeout(function () {
        target.removeAttribute("data-sb-scrolling");
      }, 850));
    }, { capture: true, passive: true });
    document.addEventListener("mouseleave", function () {
      if (hotEl) { hotEl.removeAttribute("data-sb-hot"); hotEl = null; }
    });

    // Global viewport-bottom-pinned animated horizontal scrollbar across all pages
    var hsbRail = document.createElement("div");
    hsbRail.id = "avrig-hsb-rail";
    hsbRail.className = "avrig-hsb-rail";
    hsbRail.setAttribute("aria-hidden", "true");
    hsbRail.innerHTML = '<div class="avrig-hsb-track"><div class="avrig-hsb-thumb"></div></div>';
    document.body.appendChild(hsbRail);
    var hsbTrack = hsbRail.querySelector(".avrig-hsb-track");
    var hsbThumb = hsbRail.querySelector(".avrig-hsb-thumb");

    var hsbTarget = null;
    var hsbHideTimer = null;
    var hsbHoverBottom = false;
    var hsbScrolling = false;
    var hsbDragging = false;

    function isHScrollable(el) {
      if (!el || el.nodeType !== 1) return false;
      if (el.scrollWidth <= el.clientWidth + 2) return false;
      var style = window.getComputedStyle(el);
      var ox = style.overflowX;
      if (el !== document.documentElement && ox !== "auto" && ox !== "scroll") return false;
      var r = el.getBoundingClientRect();
      return r.width > 40 && r.height > 20 && r.bottom > 0 && r.top < window.innerHeight;
    }

    function findActiveHTarget(fromEl) {
      var cur = fromEl;
      while (cur && cur !== document.body && cur !== document.documentElement) {
        if (isHScrollable(cur)) return cur;
        cur = cur.parentElement;
      }
      if (isHScrollable(document.documentElement)) return document.documentElement;
      var candidates = document.querySelectorAll(".trello-board, .ana-table-wrap, .repo-code-body, .rf-wrap, [data-hscroll]");
      var best = null;
      var bestOverflow = 0;
      for (var i = 0; i < candidates.length; i++) {
        var c = candidates[i];
        if (isHScrollable(c)) {
          var ov = c.scrollWidth - c.clientWidth;
          if (ov > bestOverflow) { bestOverflow = ov; best = c; }
        }
      }
      return best;
    }

    function syncHsbGeometry() {
      if (!hsbTarget || !isHScrollable(hsbTarget)) {
        hsbTarget = findActiveHTarget(null);
      }
      if (!hsbTarget) {
        hsbRail.classList.remove("is-visible");
        return;
      }
      var isRoot = hsbTarget === document.documentElement;
      var rect = isRoot ? { left: 8, width: window.innerWidth - 16 } : hsbTarget.getBoundingClientRect();
      var left = Math.max(8, Math.round(rect.left));
      var width = Math.min(window.innerWidth - left - 8, Math.round(rect.width));
      if (width < 40) { hsbRail.classList.remove("is-visible"); return; }
      hsbRail.style.left = left + "px";
      hsbRail.style.width = width + "px";

      var maxScroll = Math.max(1, hsbTarget.scrollWidth - hsbTarget.clientWidth);
      var ratio = hsbTarget.clientWidth / hsbTarget.scrollWidth;
      var thumbW = Math.max(40, Math.round(width * ratio));
      var maxLeft = Math.max(0, width - thumbW);
      var thumbX = Math.round((hsbTarget.scrollLeft / maxScroll) * maxLeft);
      hsbThumb.style.width = thumbW + "px";
      hsbThumb.style.transform = "translateX(" + thumbX + "px)";

      if (hsbHoverBottom || hsbScrolling || hsbDragging) {
        hsbRail.classList.add("is-visible");
      } else {
        hsbRail.classList.remove("is-visible");
      }
    }

    function pulseHsb(el) {
      if (el && isHScrollable(el)) hsbTarget = el;
      hsbScrolling = true;
      syncHsbGeometry();
      if (hsbHideTimer) clearTimeout(hsbHideTimer);
      hsbHideTimer = setTimeout(function () {
        hsbScrolling = false;
        syncHsbGeometry();
      }, 900);
    }

    document.addEventListener("mousemove", function (event) {
      if (hsbDragging) return;
      var overRail = hsbRail.contains(event.target);
      var nearBottom = event.clientY >= window.innerHeight - 44;
      hsbHoverBottom = overRail || nearBottom;
      if (hsbHoverBottom) {
        var hit = overRail ? hsbTarget : findActiveHTarget(event.target);
        if (hit) hsbTarget = hit;
      }
      syncHsbGeometry();
    }, { passive: true });

    document.addEventListener("scroll", function (event) {
      var target = event.target === document ? document.documentElement : event.target;
      if (isHScrollable(target)) {
        pulseHsb(target);
      } else if (hsbTarget && (hsbHoverBottom || hsbScrolling)) {
        syncHsbGeometry();
      }
    }, { capture: true, passive: true });

    document.addEventListener("mouseleave", function () {
      if (!hsbDragging) {
        hsbHoverBottom = false;
        syncHsbGeometry();
      }
    });

    window.addEventListener("resize", syncHsbGeometry, { passive: true });

    hsbThumb.addEventListener("pointerdown", function (event) {
      if (!hsbTarget) return;
      event.preventDefault();
      event.stopPropagation();
      hsbDragging = true;
      hsbRail.classList.add("is-dragging");
      var startX = event.clientX;
      var startScroll = hsbTarget.scrollLeft;
      var railW = hsbTrack.getBoundingClientRect().width;
      var thumbW = hsbThumb.getBoundingClientRect().width;
      var maxLeft = Math.max(1, railW - thumbW);
      var maxScroll = Math.max(1, hsbTarget.scrollWidth - hsbTarget.clientWidth);
      function onMove(ev) {
        var dx = ev.clientX - startX;
        hsbTarget.scrollLeft = startScroll + (dx / maxLeft) * maxScroll;
        syncHsbGeometry();
      }
      function onUp() {
        hsbDragging = false;
        hsbRail.classList.remove("is-dragging");
        window.removeEventListener("pointermove", onMove);
        window.removeEventListener("pointerup", onUp);
        syncHsbGeometry();
      }
      window.addEventListener("pointermove", onMove);
      window.addEventListener("pointerup", onUp);
    });

    hsbTrack.addEventListener("click", function (event) {
      if (!hsbTarget || event.target === hsbThumb) return;
      var r = hsbTrack.getBoundingClientRect();
      var pct = Math.max(0, Math.min(1, (event.clientX - r.left) / Math.max(1, r.width)));
      hsbTarget.scrollLeft = pct * (hsbTarget.scrollWidth - hsbTarget.clientWidth);
      pulseHsb(hsbTarget);
    });
  }
})();
