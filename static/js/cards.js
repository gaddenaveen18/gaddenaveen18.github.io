// Topic filter and "Show more" for card grids. Without JavaScript every card simply shows.
(function () {
  var list = document.querySelector(".cards[data-page-size]");
  if (!list) return;
  var cards = Array.prototype.slice.call(list.children);
  var size = parseInt(list.getAttribute("data-page-size"), 10) || 12;
  var shown = size, topic = "";
  var more = document.querySelector(".cards-more");
  var chips = document.querySelector(".chips");

  function render() {
    var matches = cards.filter(function (c) { return !topic || c.getAttribute("data-topic") === topic; });
    cards.forEach(function (c) { c.hidden = true; });
    matches.forEach(function (c, i) { c.hidden = i >= shown; });
    if (more) more.hidden = matches.length <= shown;
  }
  if (chips) {
    chips.hidden = false;
    chips.addEventListener("click", function (e) {
      var b = e.target.closest("button[data-topic]");
      if (!b) return;
      topic = b.getAttribute("data-topic");
      shown = size;
      chips.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
      render();
    });
  }
  if (more) more.querySelector("button").addEventListener("click", function () { shown += size; render(); });
  render();
})();
