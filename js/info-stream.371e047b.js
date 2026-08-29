/**
 * Information stream sector filter (homepage inbox articles).
 */
(function () {
  var active = "all";
  var rows = document.querySelectorAll(".info-row");
  var chips = document.querySelectorAll(".info-sector-chip");
  var readout = document.getElementById("info-stream-readout");

  function applyFilter() {
    var visible = 0;
    rows.forEach(function (row) {
      var primary = row.getAttribute("data-primary") || "";
      var sectors = (row.getAttribute("data-sectors") || "").split(",").filter(Boolean);
      var show = active === "all" || primary === active || sectors.indexOf(active) >= 0;
      row.classList.toggle("is-hidden", !show);
      if (show) visible += 1;
    });
    if (readout) readout.textContent = visible + " IN VIEW";
  }

  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      active = chip.getAttribute("data-sector") || "all";
      chips.forEach(function (c) {
        c.classList.toggle("is-active", c === chip);
      });
      applyFilter();
    });
  });

  applyFilter();
})();
