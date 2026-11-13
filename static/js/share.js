// "Copy link" on share bars; on phones it opens the system share sheet instead.
document.addEventListener("click", function (e) {
  var b = e.target.closest("[data-share-copy]");
  if (!b) return;
  var bar = b.closest(".share"), url = bar.getAttribute("data-url"), title = bar.getAttribute("data-title");
  if (navigator.share && window.matchMedia("(pointer: coarse)").matches) {
    navigator.share({ title: title, url: url }).catch(function () {});
    return;
  }
  var done = function () { var t = b.textContent; b.textContent = "Link copied"; setTimeout(function () { b.textContent = t; }, 1800); };
  if (navigator.clipboard) { navigator.clipboard.writeText(url).then(done, function () { window.prompt("Copy this link:", url); }); }
  else { window.prompt("Copy this link:", url); }
});
