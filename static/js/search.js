// Site search: loads a small index of every post, framework and book, then
// matches all typed words against title, topic and summary.
(function () {
  var input = document.getElementById("sq"), list = document.getElementById("search-results"), status = document.getElementById("search-status");
  if (!input) return;
  var items = [];
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function run() {
    var words = input.value.toLowerCase().split(/\s+/).filter(Boolean);
    var url = new URL(location.href);
    if (words.length) url.searchParams.set("q", input.value); else url.searchParams.delete("q");
    history.replaceState(null, "", url);
    if (!words.length) { list.innerHTML = ""; status.textContent = items.length + " items to search."; return; }
    var hits = items.map(function (it) {
      var title = it.title.toLowerCase(), all = (it.title + " " + it.topic + " " + it.kind + " " + it.summary).toLowerCase();
      if (!words.every(function (w) { return all.indexOf(w) >= 0; })) return null;
      var score = words.reduce(function (s, w) { return s + (title.indexOf(w) >= 0 ? 3 : 1); }, 0);
      return { it: it, score: score };
    }).filter(Boolean).sort(function (a, b) { return b.score - a.score; });
    status.textContent = hits.length ? hits.length + (hits.length === 1 ? " result" : " results") : "No results. Try a different word.";
    list.innerHTML = hits.map(function (h) {
      var it = h.it;
      return '<li><a href="' + esc(it.url) + '"><span class="search-kind">' + esc(it.kind) + (it.topic ? " · " + esc(it.topic) : "") + '</span><span class="search-title">' + esc(it.title) + '</span><span class="search-summary">' + esc(it.summary) + "</span></a></li>";
    }).join("");
  }
  fetch(window.SEARCH_INDEX).then(function (r) { return r.json(); }).then(function (data) {
    items = data;
    var q = new URL(location.href).searchParams.get("q");
    if (q) input.value = q;
    run();
  });
  input.addEventListener("input", run);
  input.form.addEventListener("submit", function (e) { e.preventDefault(); run(); });
})();
