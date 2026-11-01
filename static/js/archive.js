// Live search on the Writing page. Works without a server: it filters the
// posts already on the page.
(function () {
  const q = document.getElementById("q");
  const seriesOnly = document.getElementById("series-only");
  const status = document.getElementById("filter-status");
  if (!q) return;
  const entries = [...document.querySelectorAll(".archive .entry")];
  const groups = [...document.querySelectorAll(".year-group")];

  function apply() {
    const words = q.value.toLowerCase().split(/\s+/).filter(Boolean);
    let shown = 0;
    entries.forEach((li) => {
      const text = li.dataset.text || "";
      const ok = words.every((w) => text.includes(w)) && (!seriesOnly.checked || li.dataset.series === "thought-experiment");
      li.hidden = !ok;
      if (ok) shown++;
    });
    groups.forEach((g) => { g.hidden = !g.querySelector(".entry:not([hidden])"); });
    status.textContent = words.length || seriesOnly.checked
      ? (shown ? `${shown} matching post${shown === 1 ? "" : "s"}` : "No posts match. Try fewer or different words.")
      : "";
  }
  q.addEventListener("input", apply);
  seriesOnly.addEventListener("change", apply);
})();
