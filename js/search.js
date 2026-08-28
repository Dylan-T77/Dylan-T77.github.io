(function () {
  "use strict";

  const INDEX_URL = "/data/search-index.json";
  const form = document.getElementById("search-form");
  const resultsEl = document.getElementById("search-results");
  const relatedEl = document.getElementById("search-related");
  const countEl = document.getElementById("search-count");
  const staticList = document.getElementById("search-static");

  if (!form || !resultsEl) return;

  const params = new URLSearchParams(window.location.search);

  ["q", "type", "topic", "source", "date"].forEach((name) => {
    const field = form.elements.namedItem(name);
    if (field && params.get(name)) field.value = params.get(name);
  });

  const esc = (value) =>
    String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[char]));

  function tokens(text) {
    return String(text || "")
      .toLowerCase()
      .split(/[^a-z0-9]+/)
      .filter((part) => part.length > 1);
  }

  function score(item, query) {
    if (!query) return 1;
    const hay = [
      item.title,
      item.summary,
      item.body,
      (item.topics || []).join(" "),
      (item.entities || []).join(" "),
      (item.sources || []).join(" "),
    ]
      .join(" ")
      .toLowerCase();
    let points = 0;
    for (const token of tokens(query)) {
      if (item.title.toLowerCase().includes(token)) points += 8;
      if ((item.topics || []).some((topic) => topic.includes(token))) points += 5;
      if ((item.entities || []).some((entity) => entity.includes(token))) points += 5;
      if (hay.includes(token)) points += 2;
      else return 0;
    }
    return points;
  }

  function matchesFilters(item, filters) {
    if (filters.type && item.type !== filters.type) return false;
    if (filters.topic && !(item.topics || []).includes(filters.topic)) return false;
    if (filters.source && !(item.sources || []).includes(filters.source)) return false;
    if (filters.date) {
      const year = String(item.date || "").slice(0, 4);
      if (year !== filters.date) return false;
    }
    return true;
  }

  function renderItems(items, heading) {
    if (!items.length) {
      return `<div class="empty-state"><strong>${esc(heading)}</strong>No matching records in the published index.</div>`;
    }
    return items
      .map(
        (item) => `<article class="row-item">
          <div class="row-meta"><b>${esc(item.type)}</b><br>${esc(item.date || "undated")}</div>
          <div>
            <h3><a href="${esc(item.url)}">${esc(item.title)}</a></h3>
            <p>${esc(item.summary || "")}</p>
            <div class="chip-row">${(item.topics || [])
              .map((topic) => `<a class="chip" href="/topics/${esc(topic)}/">${esc(topic)}</a>`)
              .join("")}</div>
          </div>
          <a class="row-go" href="${esc(item.url)}">OPEN</a>
        </article>`
      )
      .join("");
  }

  function relatedFor(matches, index) {
    const seen = new Set(matches.map((item) => item.id));
    const topicSet = new Set(matches.flatMap((item) => item.topics || []));
    const entitySet = new Set(matches.flatMap((item) => item.entities || []));
    return index
      .filter((item) => !seen.has(item.id))
      .map((item) => ({
        item,
        overlap:
          (item.topics || []).filter((topic) => topicSet.has(topic)).length +
          (item.entities || []).filter((entity) => entitySet.has(entity)).length,
      }))
      .filter((entry) => entry.overlap > 0)
      .sort((a, b) => b.overlap - a.overlap)
      .slice(0, 6)
      .map((entry) => entry.item);
  }

  async function run() {
    const filters = {
      q: (form.elements.namedItem("q")?.value || "").trim(),
      type: form.elements.namedItem("type")?.value || "",
      topic: form.elements.namedItem("topic")?.value || "",
      source: form.elements.namedItem("source")?.value || "",
      date: form.elements.namedItem("date")?.value || "",
    };

    let index = [];
    try {
      const response = await fetch(INDEX_URL, { cache: "no-store" });
      if (!response.ok) throw new Error("index unavailable");
      const payload = await response.json();
      index = Array.isArray(payload.items) ? payload.items : [];
    } catch (error) {
      resultsEl.innerHTML =
        '<div class="empty-state"><strong>INDEX OFFLINE</strong>Search needs the generated index at /data/search-index.json.</div>';
      return;
    }

    const matches = index
      .map((item) => ({ item, points: score(item, filters.q) }))
      .filter((entry) => entry.points > 0 && matchesFilters(entry.item, filters))
      .sort((a, b) => b.points - a.points || String(b.item.date).localeCompare(String(a.item.date)))
      .map((entry) => entry.item);

    if (staticList) staticList.hidden = true;
    countEl.textContent = `${matches.length} RECORD${matches.length === 1 ? "" : "S"} // CLIENT INDEX`;
    resultsEl.innerHTML = renderItems(matches, "NO RESULTS");

    const related = relatedFor(matches.slice(0, 5), index);
    if (relatedEl) {
      relatedEl.innerHTML = related.length
        ? `<h2 class="ed-label">CONNECTED RESULTS</h2><div class="row-list">${renderItems(related, "CONNECTED")}</div>`
        : "";
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const next = new URL(window.location.href);
    const data = new FormData(form);
    next.search = new URLSearchParams([...data.entries()].filter(([, value]) => value)).toString();
    history.replaceState({}, "", next);
    run();
  });

  run();
})();
