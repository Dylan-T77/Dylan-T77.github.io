/* ============================================================
   The Tech Briefing - network console
   Reads /data/dashboard.json (derived from data/network.json at
   build time). Every rendered number traces to a published record.
   Progressive enhancement only: without this file the homepage
   remains a complete static document.
   ============================================================ */

(function () {
  "use strict";

  var REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- analytics hooks ----------
     Interaction telemetry for a future GA4 (or similar) integration.
     Events queue on window.TTB.events; TTB.track() is the single
     integration point a vendor snippet can wrap or replace.
     This measures visitor interaction only - never site intelligence
     data. */
  var TTB = (window.TTB = window.TTB || {});
  TTB.events = TTB.events || [];
  TTB.track = function (name, payload) {
    var rec = { event: name, payload: payload || {}, ts: new Date().toISOString() };
    TTB.events.push(rec);
    if (window.console && typeof console.debug === "function") {
      console.debug("[ttb:track]", name, payload || {});
    }
    /* GA4 wiring point: gtag("event", name, payload) */
  };

  var consoleEl = document.getElementById("console");
  if (!consoleEl) return;

  /* ---------- tiny dom helpers ---------- */

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  function esc(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function fmtDay(iso) {
    var months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
    var parts = String(iso || "").slice(0, 10).split("-");
    if (parts.length !== 3) return iso || "UNDATED";
    var m = parseInt(parts[1], 10);
    return parts[2] + " " + (months[m - 1] || parts[1]);
  }
  function plural(n, word) { return n + " " + word + (n === 1 ? "" : "S"); }

  /* ---------- state ---------- */

  var DATA = null;
  var state = { topic: "all", window: "all" };

  function editionDate() { return DATA.meta.edition.date; }

  function inWindow(sig) {
    if (state.window === "all") return true;
    var ed = editionDate();
    var end = new Date(ed + "T23:59:59Z").getTime();
    var start = new Date(ed + "T00:00:00Z");
    if (state.window === "7d") start.setUTCDate(start.getUTCDate() - 6);
    else if (state.window === "30d") start.setUTCDate(start.getUTCDate() - 29);
    var t = new Date(String(sig.published).slice(0, 10) + "T00:00:00Z").getTime();
    return t >= start.getTime() && t <= end;
  }

  function inTopic(sig) {
    return state.topic === "all" || (sig.topics || []).indexOf(state.topic) !== -1;
  }

  function visibleSignals() {
    return DATA.signals.filter(function (s) { return inWindow(s) && inTopic(s); });
  }
  function windowSignals() {
    return DATA.signals.filter(inWindow);
  }

  var WINDOW_LABELS = { today: "TODAY", "7d": "7 DAYS", "30d": "30 DAYS", all: "ALL TIME" };

  /* ---------- filter bar ---------- */

  function initFilters() {
    $$(".f-chip", consoleEl).forEach(function (chip) {
      chip.addEventListener("click", function () {
        if (chip.dataset.topic != null) {
          state.topic = chip.dataset.topic;
          $$(".f-chip[data-topic]", consoleEl).forEach(function (c) {
            c.classList.toggle("is-active", c.dataset.topic === state.topic);
          });
          TTB.track("filter_topic", { topic: state.topic, via: "filter_bar" });
        } else if (chip.dataset.window != null) {
          state.window = chip.dataset.window;
          $$(".f-chip[data-window]", consoleEl).forEach(function (c) {
            c.classList.toggle("is-active", c.dataset.window === state.window);
          });
          TTB.track("filter_window", { window: state.window });
        }
        applyFilters();
      });
    });
  }

  function applyFilters() {
    var vis = visibleSignals();
    var visIds = {};
    vis.forEach(function (s) { visIds[s.id] = true; });

    /* signals list */
    $$(".sig-row", $("#sig-list")).forEach(function (rowEl) {
      rowEl.classList.toggle("is-hidden", !visIds[rowEl.getAttribute("data-sid")]);
    });
    var listEl = $("#sig-list");
    var emptyEl = $("#sig-empty", listEl);
    if (!vis.length) {
      if (!emptyEl) {
        emptyEl = document.createElement("div");
        emptyEl.id = "sig-empty";
        emptyEl.className = "data-state";
        emptyEl.innerHTML = "<strong>NO SIGNALS IN THIS VIEW</strong><p>No published record matches this topic and window. Widen the window or clear the topic filter.</p>";
        listEl.appendChild(emptyEl);
      }
    } else if (emptyEl) {
      emptyEl.remove();
    }

    /* readouts */
    var readout = $("#filter-readout");
    if (readout) {
      var topicLabel = state.topic === "all" ? "ALL TOPICS" : state.topic.toUpperCase();
      readout.textContent = vis.length + " / " + DATA.signals.length + " SIGNALS IN VIEW · " +
        topicLabel + " · " + (WINDOW_LABELS[state.window] || "");
    }
    var countNote = $("#signals-count");
    if (countNote) countNote.textContent = plural(vis.length, "RECORD");
    var statSignals = $("#stat-signals");
    if (statSignals) {
      statSignals.textContent = state.topic === "all" && state.window === "all"
        ? DATA.signals.length + " PUBLISHED"
        : vis.length + " IN VIEW / " + DATA.signals.length + " PUBLISHED";
    }

    renderTopicBars();
    renderStatusBars(vis);
    renderSourceBars(vis);
    refreshMapCounts(visIds);
    refreshNetFilter(vis, visIds);
    refreshLocIndex(visIds);
  }

  /* ---------- bar charts ---------- */

  function barRowHtml(label, count, top, key, attr, href) {
    var pct = count ? Math.round((100 * count) / top) : 0;
    var labelHtml = href ? '<a href="' + esc(href) + '">' + esc(label) + "</a>" : esc(label);
    return '<div class="bar-row" ' + attr + '="' + esc(key) + '" role="button" tabindex="0" aria-label="Filter: ' + esc(label) + '">' +
      '<span class="bar-label">' + labelHtml + "</span>" +
      '<span class="bar-track"><span class="bar-fill" style="width:' + pct + '%"></span></span>' +
      '<span class="bar-value">' + count + "</span></div>";
  }

  function bindChartBars(container, attr, onPick) {
    if (!container) return;
    function handler(ev) {
      var rowEl = ev.target.closest ? ev.target.closest(".bar-row") : null;
      if (!rowEl) return;
      if (ev.type === "keydown" && ev.key !== "Enter" && ev.key !== " ") return;
      if (ev.target.tagName === "A") return;
      ev.preventDefault();
      onPick(rowEl.getAttribute(attr));
    }
    container.addEventListener("click", handler);
    container.addEventListener("keydown", handler);
  }

  function renderTopicBars() {
    var el = $("#chart-topics");
    if (!el) return;
    var inWin = windowSignals();
    var counts = {};
    DATA.topics.forEach(function (t) { counts[t.id] = 0; });
    inWin.forEach(function (s) {
      (s.topics || []).forEach(function (t) { if (t in counts) counts[t] += 1; });
    });
    var top = 1;
    DATA.topics.forEach(function (t) { top = Math.max(top, counts[t.id]); });
    el.innerHTML = DATA.topics.map(function (t) {
      return barRowHtml(t.name, counts[t.id], top, t.id, "data-topic", t.url);
    }).join("");
    $$(".bar-row", el).forEach(function (rowEl) {
      rowEl.classList.toggle("is-active", rowEl.getAttribute("data-topic") === state.topic);
    });
  }

  function renderStatusBars(vis) {
    var el = $("#chart-status");
    if (!el) return;
    var counts = {};
    vis.forEach(function (s) { counts[s.status] = (counts[s.status] || 0) + 1; });
    var keys = Object.keys(counts).sort();
    if (!keys.length) {
      el.innerHTML = '<div class="data-state"><strong>NO SIGNALS IN VIEW</strong><p>Nothing matches the current filter window.</p></div>';
      return;
    }
    var top = 1;
    keys.forEach(function (k) { top = Math.max(top, counts[k]); });
    el.innerHTML = keys.map(function (k) {
      return barRowHtml(k, counts[k], top, k, "data-status", null);
    }).join("");
  }

  function renderSourceBars(vis) {
    var el = $("#chart-sources");
    if (!el) return;
    var counts = {};
    vis.forEach(function (s) {
      (s.sources || []).forEach(function (src) { counts[src] = (counts[src] || 0) + 1; });
    });
    var keys = Object.keys(counts).sort(function (a, b) { return counts[b] - counts[a] || (a < b ? -1 : 1); });
    if (!keys.length) {
      el.innerHTML = '<div class="data-state"><strong>NO CITATIONS IN VIEW</strong><p>No signals in the current view, so no sources are cited.</p></div>';
      return;
    }
    var top = 1;
    keys.forEach(function (k) { top = Math.max(top, counts[k]); });
    el.innerHTML = keys.map(function (k) {
      return barRowHtml(k.toUpperCase().replace(/-/g, " "), counts[k], top, k, "data-source", null);
    }).join("");
  }

  /* ---------- voxel world map ---------- */

  var selectedCountry = null;

  function countryById(id) {
    var found = null;
    (DATA.countries || []).forEach(function (c) {
      if (c.id === id) found = c;
    });
    if (found) return found;
    (DATA.world_countries || []).forEach(function (c) {
      if (c.id === id) found = c;
    });
    return found;
  }

  function countryCountInView(country, visIds) {
    var n = 0;
    (country.signals || []).forEach(function (sid) {
      if (visIds[sid]) n += 1;
    });
    return n;
  }

  function visSignalMap() {
    var visIds = {};
    visibleSignals().forEach(function (s) {
      visIds[s.id] = true;
    });
    return visIds;
  }

  function syncVoxelIntelligence() {
    if (!TTB.voxelWorld || !TTB.voxelWorld.isReady()) return;
    TTB.voxelWorld.setIntelligence(DATA.countries || [], visSignalMap());
  }

  function initVoxelMap() {
    syncVoxelIntelligence();

    window.addEventListener("ttb:country-select", function (ev) {
      var cid = ev.detail && ev.detail.countryId;
      if (cid) selectCountry(cid, { track: "map" });
    });

    $$(".country-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var id = btn.getAttribute("data-country");
        TTB.track("map_country_click", { country: id, via: "index" });
        selectCountry(id, { focus: true, track: "index" });
      });
    });

    if (!TTB.voxelWorld.isReady()) {
      window.addEventListener("ttb:voxel-ready", function onReady() {
        window.removeEventListener("ttb:voxel-ready", onReady);
        syncVoxelIntelligence();
      });
    }
  }

  function selectCountry(id, opts) {
    var country = countryById(id);
    if (!country) {
      country = {
        id: id,
        name: id,
        has_entity_presence: false,
        has_signals: false,
        entities: [],
        sites: [],
        topics: [],
        briefings: [],
        signals: [],
        signal_count: 0,
        latest: null,
      };
    }
    opts = opts || {};
    selectedCountry = id;

    $$(".country-btn").forEach(function (btn) {
      btn.classList.toggle("is-active", btn.getAttribute("data-country") === id);
    });

    if (TTB.voxelWorld && TTB.voxelWorld.isReady()) {
      TTB.voxelWorld.selectCountry(id, { emit: false });
    }

    if (opts.track) {
      TTB.track("map_country_select", {
        country: id,
        via: opts.track,
        signals: country.signal_count,
      });
    }

    renderCountryDetail(country);
  }

  function renderCountryDetail(country) {
    var el = $("#map-detail");
    if (!el) return;
    var visIds = visSignalMap();
    var inView = countryCountInView(country, visIds);

    var ents = (country.entities || []).map(function (ent) {
      return '<a href="' + esc(ent.url) + '">' + esc(ent.name) + "</a> (" + esc(ent.type) + ")";
    }).join("<br>");

    var sites = (country.sites || []).map(function (site) {
      return esc(site.city.toUpperCase()) + " · " + esc(site.name) + " · " + site.signal_count + " SIG";
    }).join("<br>");

    var topics = (country.topics || []).map(function (t) {
      return esc(t.toUpperCase());
    }).join(" · ") || "NONE ON RECORD";

    var latest = country.latest
      ? '<a href="' + esc(country.latest.url) + '" data-track="signal">' + esc(country.latest.title) + "</a><br>" +
        '<span class="node-status">' + esc(country.latest.status) + " · " + esc(fmtDay(country.latest.published)) + "</span>"
      : country.has_entity_presence
        ? "Entity presence on record. No published signal attached yet."
        : "No intelligence on record for this country.";

    var briefs = (country.briefings || []).length
      ? '<dt>BRIEFINGS</dt><dd>' + country.briefings.map(function (b) {
          return '<a href="' + esc(b.url) + '" data-track="briefing">' + esc(b.title) + "</a>";
        }).join("<br>") + "</dd>"
      : "";

    var presenceLine = country.has_signals
      ? plural(country.signal_count, "SIGNAL") + " ON RECORD · " + inView + " IN VIEW"
      : country.has_entity_presence
        ? "ENTITY PRESENCE · 0 SIGNALS ON RECORD"
        : "NO RECORDED PRESENCE";

    el.innerHTML =
      "<h3>" + esc(country.name.toUpperCase()) + "</h3>" +
      '<span class="loc-count">' + esc(presenceLine) + "</span>" +
      "<dl>" +
      "<dt>ENTITIES</dt><dd>" + (ents || "None on record.") + "</dd>" +
      "<dt>SITES</dt><dd>" + (sites || "None on record.") + "</dd>" +
      "<dt>TOPICS</dt><dd>" + topics + "</dd>" +
      "<dt>LATEST</dt><dd>" + latest + "</dd>" +
      briefs +
      "</dl>" +
      '<a class="detail-go" href="/signals/" data-track="signals_index">VIEW SIGNALS →</a>';
  }

  function refreshMapCounts(visIds) {
    syncVoxelIntelligence();
    if (selectedCountry) {
      var country = countryById(selectedCountry);
      if (country) renderCountryDetail(country);
    }
  }

  function refreshLocIndex(visIds) {
    $$(".country-btn").forEach(function (btn) {
      var id = btn.getAttribute("data-country");
      var country = countryById(id);
      if (!country) return;
      var meta = btn.querySelector(".loc-meta b");
      if (!meta) return;
      if (country.has_signals) {
        meta.textContent = countryCountInView(country, visIds) + " IN VIEW / " +
          country.signal_count + " ON RECORD";
      } else if (country.has_entity_presence) {
        meta.textContent = "ENTITY PRESENCE · 0 SIGNALS";
      }
    });
  }

  /* ---------- network graph ---------- */

  var net = {
    canvas: null,
    ctx: null,
    nodes: [],
    edges: [],
    byId: {},
    selected: null,
    hover: null,
    activeIds: null, /* null = everything active */
    t0: 0,
  };

  function initNet() {
    var canvas = $("#net-canvas");
    if (!canvas || !canvas.getContext) return;
    net.canvas = canvas;
    net.ctx = canvas.getContext("2d");

    net.nodes = DATA.graph.nodes.map(function (n, i) {
      return {
        id: n.id, label: n.label, kind: n.kind, url: n.url, status: n.status,
        weight: n.weight, phase: (i * 137.5) % 360, x: 0, y: 0, bx: 0, by: 0, vx: 0, vy: 0,
      };
    });
    net.edges = DATA.graph.edges.map(function (ed) { return { source: ed.source, target: ed.target, weight: ed.weight }; });
    net.nodes.forEach(function (n, i) { net.byId[n.id] = i; });

    sizeNet();
    layoutNet();

    canvas.addEventListener("mousemove", function (ev) {
      var p = canvasPoint(ev);
      net.hover = hitNode(p.x, p.y);
      canvas.style.cursor = net.hover ? "pointer" : "crosshair";
      if (REDUCED) drawNet();
    });
    canvas.addEventListener("mouseleave", function () {
      net.hover = null;
      if (REDUCED) drawNet();
    });
    canvas.addEventListener("click", function (ev) {
      var p = canvasPoint(ev);
      var hit = hitNode(p.x, p.y);
      if (hit) {
        net.selected = net.selected === hit.id ? null : hit.id;
        if (net.selected) {
          var n = net.nodes[net.byId[hit.id]];
          TTB.track("net_node_click", { node: hit.id, kind: hit.kind, label: n.label });
          renderNodeDetail(hit);
        } else {
          renderNetDefault();
        }
      } else {
        net.selected = null;
        renderNetDefault();
      }
      if (REDUCED) drawNet();
    });

    window.addEventListener("resize", function () {
      sizeNet();
      layoutNet();
      if (REDUCED) drawNet();
    });

    if (REDUCED) {
      drawNet();
    } else {
      net.t0 = performance.now();
      requestAnimationFrame(netTick);
    }
  }

  function sizeNet() {
    var canvas = net.canvas;
    var dpr = window.devicePixelRatio || 1;
    var w = canvas.clientWidth || 600;
    var h = canvas.clientHeight || 440;
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    net.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    net.w = w;
    net.h = h;
  }

  function layoutNet() {
    var n = net.nodes.length;
    var cx = net.w / 2;
    var cy = net.h / 2;
    var R = Math.min(net.w, net.h) * 0.34;

    net.nodes.forEach(function (node, i) {
      var a = (i / n) * Math.PI * 2 - Math.PI / 2;
      node.x = node.bx = cx + Math.cos(a) * R;
      node.y = node.by = cy + Math.sin(a) * R;
      node.vx = node.vy = 0;
    });

    var i, j, k, ed, a, b, dx, dy, d2, d, f, it;
    for (it = 0; it < 320; it++) {
      for (i = 0; i < n; i++) {
        a = net.nodes[i];
        for (j = i + 1; j < n; j++) {
          b = net.nodes[j];
          dx = a.x - b.x; dy = a.y - b.y;
          d2 = dx * dx + dy * dy || 0.01;
          f = Math.min(1400 / d2, 4);
          d = Math.sqrt(d2);
          dx /= d; dy /= d;
          a.vx += dx * f; a.vy += dy * f;
          b.vx -= dx * f; b.vy -= dy * f;
        }
      }
      for (k = 0; k < net.edges.length; k++) {
        ed = net.edges[k];
        a = net.nodes[net.byId[ed.source]];
        b = net.nodes[net.byId[ed.target]];
        if (!a || !b) continue;
        dx = b.x - a.x; dy = b.y - a.y;
        d = Math.sqrt(dx * dx + dy * dy) || 0.01;
        f = (d - 118) * 0.014;
        dx /= d; dy /= d;
        a.vx += dx * f; a.vy += dy * f;
        b.vx -= dx * f; b.vy -= dy * f;
      }
      for (i = 0; i < n; i++) {
        a = net.nodes[i];
        a.vx += (cx - a.x) * 0.006;
        a.vy += (cy - a.y) * 0.006;
        a.vx *= 0.82; a.vy *= 0.82;
        a.x += a.vx; a.y += a.vy;
      }
    }
    net.nodes.forEach(function (node) { node.bx = node.x; node.by = node.y; });
    drawNet();
  }

  function nodeRadius(node) {
    return Math.max(4, Math.min(11, 3 + node.weight * 1.4));
  }

  function isActive(node) {
    if (!net.activeIds) return true;
    return !!net.activeIds[node.id];
  }

  function drawNet() {
    var ctx = net.ctx;
    if (!ctx) return;
    ctx.clearRect(0, 0, net.w, net.h);

    var i, ed, a, b;
    var selNeighbors = {};
    if (net.selected != null) {
      net.edges.forEach(function (e2) {
        if (e2.source === net.selected) selNeighbors[e2.target] = true;
        if (e2.target === net.selected) selNeighbors[e2.source] = true;
      });
    }
    var hoverId = net.hover ? net.hover.id : null;

    for (i = 0; i < net.edges.length; i++) {
      ed = net.edges[i];
      a = net.nodes[net.byId[ed.source]];
      b = net.nodes[net.byId[ed.target]];
      if (!a || !b) continue;
      var alpha = Math.min(0.05 + ed.weight * 0.045, 0.3);
      var hot = net.selected != null && (ed.source === net.selected || ed.target === net.selected);
      var hov = hoverId && (ed.source === hoverId || ed.target === hoverId);
      if (hot || hov) alpha = 0.55;
      if (net.selected != null && !hot) alpha *= 0.35;
      if (!isActive(a) || !isActive(b)) alpha *= 0.3;
      ctx.strokeStyle = "rgba(97, 246, 197, " + alpha.toFixed(3) + ")";
      ctx.lineWidth = ed.weight >= 4 ? 1.4 : 1;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    }

    for (i = 0; i < net.nodes.length; i++) {
      var node = net.nodes[i];
      var r = nodeRadius(node);
      var active = isActive(node);
      var selected = net.selected === node.id;
      var neighbor = selNeighbors[node.id];
      var hovered = hoverId === node.id;
      var alphaNode = active ? 1 : 0.18;
      if (net.selected != null && !selected && !neighbor) alphaNode *= 0.35;

      ctx.globalAlpha = alphaNode;
      ctx.lineWidth = selected || hovered ? 1.8 : 1.1;

      if (node.kind === "topic") {
        ctx.strokeStyle = selected || hovered ? "#61f6c5" : "rgba(97, 246, 197, .9)";
        ctx.fillStyle = "rgba(97, 246, 197, .12)";
        ctx.strokeRect(node.x - r, node.y - r, r * 2, r * 2);
        ctx.fillRect(node.x - r, node.y - r, r * 2, r * 2);
      } else if (node.kind === "briefing") {
        ctx.strokeStyle = selected || hovered ? "#70a7ff" : "rgba(112, 167, 255, .9)";
        ctx.fillStyle = "rgba(112, 167, 255, .12)";
        ctx.beginPath();
        ctx.moveTo(node.x, node.y - r - 2);
        ctx.lineTo(node.x + r + 2, node.y);
        ctx.lineTo(node.x, node.y + r + 2);
        ctx.lineTo(node.x - r - 2, node.y);
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
      } else {
        ctx.strokeStyle = selected || hovered ? "#e8f0f2" : "rgba(169, 184, 188, .85)";
        ctx.fillStyle = "rgba(232, 240, 242, .08)";
        ctx.beginPath();
        ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
      }

      ctx.font = "600 8.5px ui-monospace, monospace";
      ctx.textAlign = "center";
      ctx.fillStyle = selected || hovered ? "#e8f0f2" : "rgba(127, 141, 146, .9)";
      var label = node.label.length > 26 ? node.label.slice(0, 25) + "…" : node.label;
      ctx.fillText(label, node.x, node.y + r + 13);
      ctx.globalAlpha = 1;
    }
  }

  function netTick(now) {
    var t = (now - net.t0) / 1000;
    net.nodes.forEach(function (node) {
      var wob = 2.6;
      node.x = node.bx + Math.sin(t * 0.5 + node.phase) * wob;
      node.y = node.by + Math.cos(t * 0.38 + node.phase * 1.7) * wob;
    });
    drawNet();
    requestAnimationFrame(netTick);
  }

  function canvasPoint(ev) {
    var rect = net.canvas.getBoundingClientRect();
    return { x: ev.clientX - rect.left, y: ev.clientY - rect.top };
  }

  function hitNode(x, y) {
    var best = null;
    var bestD = 18;
    net.nodes.forEach(function (node) {
      var dx = node.x - x;
      var dy = node.y - y;
      var d = Math.sqrt(dx * dx + dy * dy) - nodeRadius(node);
      if (d < bestD) { bestD = d; best = node; }
    });
    return best;
  }

  function signalsForNode(node) {
    var id = node.id.split(":")[1];
    if (node.kind === "topic") {
      return DATA.signals.filter(function (s) { return (s.topics || []).indexOf(id) !== -1; });
    }
    if (node.kind === "entity") {
      return DATA.signals.filter(function (s) { return (s.entities || []).indexOf(id) !== -1; });
    }
    return DATA.signals.filter(function (s) { return (s.briefings || []).indexOf(id) !== -1; });
  }

  function renderNodeDetail(node) {
    var el = $("#net-detail");
    if (!el) return;
    var links = [];
    net.edges.forEach(function (ed) {
      var other = null;
      if (ed.source === node.id) other = ed.target;
      else if (ed.target === node.id) other = ed.source;
      if (other) links.push({ id: other, weight: ed.weight });
    });
    links.sort(function (x, y) { return y.weight - x.weight; });
    var linkRows = links.slice(0, 6).map(function (l) {
      var n2 = net.nodes[net.byId[l.id]];
      return '<a href="' + esc(n2.url) + '">' + esc(n2.label) + "</a> · " + l.weight + " REC";
    }).join("<br>");

    var sigs = signalsForNode(node);
    var sigRows = sigs.slice(0, 3).map(function (s) {
      return '<a href="' + esc(s.url) + '" data-track="signal">' + esc(s.title) + "</a><br>" +
        '<span class="node-status">' + esc(s.status) + " · " + esc(fmtDay(s.published)) + "</span>";
    }).join('<br>');

    el.innerHTML =
      '<span class="node-kind">' + esc(node.kind.toUpperCase()) + ' // <span class="node-status">' + esc(node.status || "RECORD") + "</span></span>" +
      "<h3>" + esc(node.label) + "</h3>" +
      "<dl>" +
      "<dt>RECORDS</dt><dd>" + plural(node.weight, "ATTACHED RECORD") + "</dd>" +
      "<dt>CONNECTIONS</dt><dd>" + (linkRows || "None on record.") + "</dd>" +
      "<dt>LATEST SIGNALS</dt><dd>" + (sigRows || "No signal attached yet.") + "</dd>" +
      "</dl>" +
      '<a class="detail-go" href="' + esc(node.url) + '">OPEN RECORD →</a>';
  }

  function renderNetDefault() {
    var el = $("#net-detail");
    if (!el) return;
    var top = net.edges.slice().sort(function (a, b) { return b.weight - a.weight; }).slice(0, 6);
    el.innerHTML =
      '<p class="mini-label">TOP CONNECTIONS</p><ul class="top-links">' +
      top.map(function (ed) {
        var a = net.nodes[net.byId[ed.source]];
        var b = net.nodes[net.byId[ed.target]];
        return "<li><span>" + esc(a.label) + "</span><i>↔</i><span>" + esc(b.label) + "</span><b>" + ed.weight + " REC</b></li>";
      }).join("") +
      '</ul><p class="detail-hint">SELECT A NODE TO INSPECT ITS RECORD.</p>';
  }

  function refreshNetFilter(vis) {
    if (!net.canvas) return;
    var activeTopics = {};
    var activeEntities = {};
    var activeBriefings = {};
    vis.forEach(function (s) {
      (s.topics || []).forEach(function (t) { activeTopics[t] = true; });
      (s.entities || []).forEach(function (en) { activeEntities[en] = true; });
      (s.briefings || []).forEach(function (b) { activeBriefings[b] = true; });
    });
    var everything = state.topic === "all" && state.window === "all";
    if (everything) {
      net.activeIds = null;
    } else {
      var ids = {};
      net.nodes.forEach(function (node) {
        var key = node.id.split(":")[1];
        if (node.kind === "topic" && activeTopics[key]) ids[node.id] = true;
        if (node.kind === "entity" && activeEntities[key]) ids[node.id] = true;
        if (node.kind === "briefing" && activeBriefings[key]) ids[node.id] = true;
      });
      net.activeIds = ids;
    }
    if (REDUCED) drawNet();
  }

  /* ---------- interaction tracking (static links) ---------- */

  function initTracking() {
    document.addEventListener("click", function (ev) {
      var link = ev.target.closest ? ev.target.closest("a[data-track]") : null;
      if (link) {
        TTB.track(link.getAttribute("data-track") + "_click", {
          href: link.getAttribute("href"),
          text: (link.textContent || "").trim().slice(0, 80),
        });
        return;
      }
      var tl = ev.target.closest ? ev.target.closest("#story-timeline li") : null;
      if (tl) {
        TTB.track("timeline_event_click", {
          date: tl.getAttribute("data-date") || "",
          label: (tl.querySelector("strong") || {}).textContent || "",
        });
      }
    });
  }

  /* ---------- boot ---------- */

  fetch("/data/dashboard.json")
    .then(function (res) { return res.ok ? res.json() : null; })
    .then(function (payload) {
      if (!payload) return;
      DATA = payload;
      /* Debug/analytics handle: lets a future analytics layer read console
         state and lets tests drive the same public surface. */
      TTB.console = { data: DATA, state: state, net: net, selectCountry: selectCountry };
      initFilters();
      initTracking();
      initVoxelMap();
      initNet();
      applyFilters();
      bindChartBars($("#chart-topics"), "data-topic", function (key) {
        state.topic = state.topic === key ? "all" : key;
        $$(".f-chip[data-topic]", consoleEl).forEach(function (c) {
          c.classList.toggle("is-active", c.dataset.topic === state.topic);
        });
        TTB.track("filter_topic", { topic: state.topic, via: "topic_chart" });
        applyFilters();
      });
    })
    .catch(function () {
      /* Static fallback stays on screen: panels keep their build-time HTML. */
    });
})();
