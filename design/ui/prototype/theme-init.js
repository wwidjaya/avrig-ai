/* Runs before first paint so the page never flashes the wrong theme.
   No storage means "system", which is the default for every surface. */
(function () {
  var choice = "system";
  try { choice = localStorage.getItem("avrig-theme") || "system"; } catch (error) {}
  var dark = choice === "dark" ||
    (choice !== "light" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  var root = document.documentElement;
  root.dataset.theme = dark ? "dark" : "light";
  root.style.colorScheme = dark ? "dark" : "light";
})();
