/**
 * The Tech Briefing — 3D voxel world map
 * Static country geometry + live intelligence overlay from dashboard.json
 *
 * THREE is resolved via the page import map (`three` → hashed vendor module).
 */
import * as THREE from "three";

var TTB = (window.TTB = window.TTB || {});

var COLORS = {
  ocean: 0x050608,
  geography: 0x141c22,
  entities: 0x2a3844,
  signals: 0x61f6c5,
  signalsDim: 0x1a4038,
  accent2: 0x70a7ff,
  hover: 0x9fffe0,
  select: 0xe8f0f2,
};

var STAGE = {
  MODULE: "module",
  GEOMETRY: "geometry",
  WEBGL: "webgl",
  RENDERER: "renderer",
  SCENE: "scene",
  VOXELS: "voxels",
  EVENTS: "events",
  RENDER: "render",
};

function isDevHost() {
  var host = window.location && window.location.hostname;
  return host === "localhost" || host === "127.0.0.1" || host === "[::1]";
}

function logStageError(stage, err) {
  var message = err && err.message ? err.message : String(err);
  console.error("[ttb:voxel:" + stage + "]", message, err);
  if (isDevHost() && err && err.stack) {
    console.error(err.stack);
  }
}

function prefersReducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function VoxelWorld(container) {
  this.container = container;
  this.canvas = null;
  this.renderer = null;
  this.scene = null;
  this.camera = null;
  this.mesh = null;
  this.raycaster = new THREE.Raycaster();
  this.pointer = new THREE.Vector2();
  this.world = null;
  this.intelByCountry = {};
  this.countryEvents = {};
  this.instanceCountry = [];
  this.countryInstances = {};
  this.baseColors = [];
  this.hoverCountry = null;
  this.selectedCountry = null;
  this.visSignalIds = null;
  this.animId = 0;
  this.dragging = false;
  this.lastX = 0;
  this.lastY = 0;
  this.dragStartX = 0;
  this.dragStartY = 0;
  this.yaw = 0.55;
  this.pitch = 0.82;
  this.distance = 95;
  this.target = new THREE.Vector3(0, 2, 0);
  this.ready = false;
  this.stage = null;
  this.fallback = document.getElementById("voxel-fallback");
}

VoxelWorld.prototype._showDiagnostic = function (stage, title, detail) {
  this.stage = stage;
  if (this.fallback) {
    this.fallback.hidden = false;
    var strong = this.fallback.querySelector("strong");
    var p = this.fallback.querySelector("p");
    if (strong) strong.textContent = title;
    if (p) p.textContent = detail;
  }
  if (this.container) this.container.classList.add("is-fallback");
  window.dispatchEvent(
    new CustomEvent("ttb:voxel-error", {
      detail: { stage: stage, title: title, detail: detail },
    })
  );
};

VoxelWorld.prototype._fetchGeometry = function () {
  var self = this;
  return fetch("/data/geo/voxel-world.v1.json")
    .then(function (res) {
      if (!res.ok) {
        throw new Error("HTTP " + res.status + " loading voxel-world.v1.json");
      }
      return res.json();
    })
    .then(function (world) {
      if (!world || !Array.isArray(world.voxels) || !world.cols || !world.rows) {
        throw new Error("voxel-world.v1.json is missing cols/rows/voxels");
      }
      self.world = world;
      return world;
    })
    .catch(function (err) {
      logStageError(STAGE.GEOMETRY, err);
      self._showDiagnostic(
        STAGE.GEOMETRY,
        "GEOMETRY UNAVAILABLE",
        isDevHost()
          ? err.message
          : "Country geometry could not be loaded. Use the country index below."
      );
      throw err;
    });
};

VoxelWorld.prototype._createCanvas = function () {
  this.canvas = document.createElement("canvas");
  this.canvas.className = "voxel-canvas";
  this.canvas.setAttribute("aria-hidden", "true");
  this.container.insertBefore(this.canvas, this.container.firstChild);
};

VoxelWorld.prototype._createRenderer = function () {
  var configs = [
    { antialias: true, alpha: false, powerPreference: "default", failIfMajorPerformanceCaveat: false },
    { antialias: false, alpha: false, powerPreference: "default", failIfMajorPerformanceCaveat: false },
    { antialias: false, alpha: false, failIfMajorPerformanceCaveat: false },
  ];
  var lastErr = null;
  for (var i = 0; i < configs.length; i++) {
    try {
      this.renderer = new THREE.WebGLRenderer(
        Object.assign({ canvas: this.canvas }, configs[i])
      );
      if (this.renderer.getContext()) {
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        this.renderer.setClearColor(COLORS.ocean, 1);
        return;
      }
      this.renderer.dispose();
      this.renderer = null;
    } catch (err) {
      lastErr = err;
      if (this.renderer) {
        this.renderer.dispose();
        this.renderer = null;
      }
    }
  }
  var message = lastErr && lastErr.message ? lastErr.message : "WebGLRenderer could not acquire a context";
  logStageError(STAGE.RENDERER, lastErr || new Error(message));
  this._showDiagnostic(
    STAGE.WEBGL,
    "WEBGL UNAVAILABLE",
    isDevHost()
      ? message
      : "This browser could not initialize the 3D renderer. Use the country index to inspect records."
  );
  throw lastErr || new Error(message);
};

VoxelWorld.prototype._createScene = function () {
  this.scene = new THREE.Scene();
  this.scene.fog = new THREE.Fog(COLORS.ocean, 70, 180);

  var aspect = 1;
  this.camera = new THREE.PerspectiveCamera(42, aspect, 0.5, 400);
  this._updateCamera();

  var ambient = new THREE.AmbientLight(0x8aa0a8, 0.55);
  var key = new THREE.DirectionalLight(0x61f6c5, 0.85);
  key.position.set(40, 80, 30);
  var fill = new THREE.DirectionalLight(0x203040, 0.45);
  fill.position.set(-50, 20, -40);
  this.scene.add(ambient, key, fill);
};

VoxelWorld.prototype._buildVoxels = function () {
  var world = this.world;
  var voxels = world.voxels || [];
  var count = voxels.length;
  var cols = world.cols;
  var rows = world.rows;
  var geo = new THREE.BoxGeometry(0.92, 1, 0.92);
  var mat = new THREE.MeshStandardMaterial({
    color: 0xffffff,
    roughness: 0.72,
    metalness: 0.08,
    flatShading: true,
  });

  this.mesh = new THREE.InstancedMesh(geo, mat, count);
  if (this.mesh.instanceMatrix.setUsage) {
    this.mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  }
  this.instanceCountry = new Array(count);
  this.countryInstances = {};
  this.baseColors = new Array(count);

  var dummy = new THREE.Object3D();
  var color = new THREE.Color();
  var offsetX = cols / 2;
  var offsetZ = rows / 2;

  for (var i = 0; i < count; i++) {
    var v = voxels[i];
    var cid = String(v.c);
    var x = v.x - offsetX;
    var z = v.y - offsetZ;
    var h = 0.45;

    dummy.position.set(x, h * 0.5, z);
    dummy.scale.set(1, h, 1);
    dummy.updateMatrix();
    this.mesh.setMatrixAt(i, dummy.matrix);

    color.setHex(COLORS.geography);
    this.mesh.setColorAt(i, color);
    this.baseColors[i] = color.clone();

    this.instanceCountry[i] = cid;
    if (!this.countryInstances[cid]) this.countryInstances[cid] = [];
    this.countryInstances[cid].push(i);
  }

  this.mesh.instanceMatrix.needsUpdate = true;
  if (this.mesh.instanceColor) this.mesh.instanceColor.needsUpdate = true;
  this.scene.add(this.mesh);

  var floor = new THREE.Mesh(
    new THREE.PlaneGeometry(cols + 20, rows + 20),
    new THREE.MeshStandardMaterial({ color: COLORS.ocean, roughness: 1, metalness: 0 })
  );
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -0.05;
  this.scene.add(floor);

  var grid = new THREE.GridHelper(Math.max(cols, rows), 24, 0x1d2a2e, 0x101820);
  grid.position.y = 0.01;
  this.scene.add(grid);
};

VoxelWorld.prototype._setupScene = function () {
  this._createCanvas();
  this._createRenderer();
  try {
    this._createScene();
  } catch (err) {
    logStageError(STAGE.SCENE, err);
    this._showDiagnostic(
      STAGE.SCENE,
      "SCENE SETUP FAILED",
      isDevHost() ? err.message : "Lighting or camera setup failed."
    );
    throw err;
  }
  try {
    this._buildVoxels();
  } catch (err) {
    logStageError(STAGE.VOXELS, err);
    this._showDiagnostic(
      STAGE.VOXELS,
      "VOXEL BUILD FAILED",
      isDevHost() ? err.message : "Country voxel geometry could not be constructed."
    );
    throw err;
  }
  try {
    this._bindEvents();
  } catch (err) {
    logStageError(STAGE.EVENTS, err);
    this._showDiagnostic(
      STAGE.EVENTS,
      "INTERACTION SETUP FAILED",
      isDevHost() ? err.message : "Map controls could not be attached."
    );
    throw err;
  }
  try {
    this._resize();
    if (!prefersReducedMotion()) {
      this._animate();
    } else {
      this.renderer.render(this.scene, this.camera);
    }
  } catch (err) {
    logStageError(STAGE.RENDER, err);
    this._showDiagnostic(
      STAGE.RENDER,
      "RENDER FAILED",
      isDevHost() ? err.message : "Initial frame could not be drawn."
    );
    throw err;
  }
  this.ready = true;
};

VoxelWorld.prototype.init = function () {
  var self = this;
  if (!this.container) return Promise.resolve(false);

  return this._fetchGeometry()
    .then(function () {
      try {
        self._setupScene();
        if (self.fallback) self.fallback.hidden = true;
        self.container.classList.remove("is-fallback");
        return true;
      } catch (err) {
        if (!self.stage) {
          logStageError(STAGE.SCENE, err);
          self._showDiagnostic(
            STAGE.SCENE,
            "SCENE SETUP FAILED",
            isDevHost() ? err.message : "The voxel world could not be constructed."
          );
        }
        return false;
      }
    })
    .catch(function () {
      return false;
    });
};

VoxelWorld.prototype.setIntelligence = function (countries, visSignalIds, countryEvents) {
  this.intelByCountry = {};
  (countries || []).forEach(function (c) {
    this.intelByCountry[c.id] = c;
  }, this);
  this.countryEvents = countryEvents || {};
  this.visSignalIds = visSignalIds || {};
  this._applyColors();
};

VoxelWorld.prototype._countInView = function (country) {
  if (!country || !country.signals) return 0;
  var vis = this.visSignalIds || {};
  var n = 0;
  country.signals.forEach(function (sid) {
    if (vis[sid]) n += 1;
  });
  return n;
};

VoxelWorld.prototype._countryColor = function (cid) {
  var intel = this.intelByCountry[cid];
  var events = this.countryEvents[cid];
  if (intel) {
    var inView = this._countInView(intel);
    if (inView > 0) {
      var t = Math.min(1, 0.45 + inView * 0.18);
      return new THREE.Color(COLORS.signals).lerp(new THREE.Color(COLORS.select), 1 - t);
    }
    if (intel.has_signals) {
      return new THREE.Color(COLORS.signalsDim);
    }
    if (intel.has_entity_presence) {
      return new THREE.Color(COLORS.entities);
    }
  }
  if (events && events.event_count > 0) {
    var intensity = Math.min(1, 0.35 + events.recent_count * 0.25 + events.event_count * 0.05);
    if (events.recent_count > 0) {
      return new THREE.Color(COLORS.signalsDim).lerp(new THREE.Color(COLORS.signals), intensity);
    }
    return new THREE.Color(COLORS.entities).lerp(new THREE.Color(COLORS.signalsDim), intensity * 0.6);
  }
  return new THREE.Color(COLORS.geography);
};

VoxelWorld.prototype._applyColors = function () {
  if (!this.mesh) return;
  var self = this;
  Object.keys(this.countryInstances).forEach(function (cid) {
    var color = self._countryColor(cid);
    var indices = self.countryInstances[cid];
    for (var j = 0; j < indices.length; j++) {
      var idx = indices[j];
      self.baseColors[idx] = color.clone();
      self.mesh.setColorAt(idx, color);
    }
  });
  if (this.mesh.instanceColor) this.mesh.instanceColor.needsUpdate = true;
  this._applyHighlight();
  if (prefersReducedMotion() && this.renderer) {
    this.renderer.render(this.scene, this.camera);
  }
};

VoxelWorld.prototype._applyHighlight = function () {
  if (!this.mesh) return;
  var active = this.selectedCountry || this.hoverCountry;
  var self = this;
  Object.keys(this.countryInstances).forEach(function (cid) {
    var indices = self.countryInstances[cid];
    var base = self._countryColor(cid);
    var color = base.clone();
    if (active && cid === active) {
      color.lerp(new THREE.Color(self.selectedCountry === cid ? COLORS.select : COLORS.hover), 0.55);
    } else if (active) {
      color.multiplyScalar(0.72);
    }
    for (var j = 0; j < indices.length; j++) {
      self.mesh.setColorAt(indices[j], color);
    }
  });
  if (this.mesh.instanceColor) this.mesh.instanceColor.needsUpdate = true;
};

VoxelWorld.prototype._updateCamera = function () {
  var cx = Math.cos(this.pitch) * Math.sin(this.yaw);
  var cy = Math.sin(this.pitch);
  var cz = Math.cos(this.pitch) * Math.cos(this.yaw);
  this.camera.position.set(
    this.target.x + cx * this.distance,
    this.target.y + cy * this.distance,
    this.target.z + cz * this.distance
  );
  this.camera.lookAt(this.target);
};

VoxelWorld.prototype._resize = function () {
  if (!this.renderer || !this.container) return;
  var rect = this.container.getBoundingClientRect();
  var w = Math.floor(rect.width) || this.container.clientWidth || 640;
  var h = Math.floor(rect.height) || this.container.clientHeight || 430;
  if (w < 2 || h < 2) return;
  this.renderer.setSize(w, h, false);
  this.camera.aspect = w / h;
  this.camera.updateProjectionMatrix();
};

VoxelWorld.prototype._pickCountry = function (clientX, clientY) {
  if (!this.mesh || !this.canvas) return null;
  var rect = this.canvas.getBoundingClientRect();
  if (!rect.width || !rect.height) return null;
  this.pointer.x = ((clientX - rect.left) / rect.width) * 2 - 1;
  this.pointer.y = -((clientY - rect.top) / rect.height) * 2 + 1;
  this.raycaster.setFromCamera(this.pointer, this.camera);
  var hit = this.raycaster.intersectObject(this.mesh)[0];
  if (!hit || hit.instanceId == null) return null;
  return this.instanceCountry[hit.instanceId] || null;
};

VoxelWorld.prototype._bindEvents = function () {
  var self = this;
  var el = this.container;

  el.addEventListener("pointerdown", function (ev) {
    if (ev.button !== 0) return;
    self.dragging = true;
    self.dragStartX = ev.clientX;
    self.dragStartY = ev.clientY;
    self.lastX = ev.clientX;
    self.lastY = ev.clientY;
    el.setPointerCapture(ev.pointerId);
  });

  el.addEventListener("pointermove", function (ev) {
    if (self.dragging) {
      var dx = ev.clientX - self.lastX;
      var dy = ev.clientY - self.lastY;
      self.lastX = ev.clientX;
      self.lastY = ev.clientY;
      self.yaw -= dx * 0.006;
      self.pitch = Math.max(0.25, Math.min(1.35, self.pitch + dy * 0.004));
      self._updateCamera();
      if (prefersReducedMotion() && self.renderer) {
        self.renderer.render(self.scene, self.camera);
      }
      return;
    }
    var cid = self._pickCountry(ev.clientX, ev.clientY);
    if (cid !== self.hoverCountry) {
      self.hoverCountry = cid;
      self._applyHighlight();
      el.style.cursor = cid ? "pointer" : "grab";
      if (prefersReducedMotion() && self.renderer) {
        self.renderer.render(self.scene, self.camera);
      }
    }
  });

  el.addEventListener("pointerup", function (ev) {
    if (!self.dragging) return;
    var moved = Math.abs(ev.clientX - self.dragStartX) + Math.abs(ev.clientY - self.dragStartY);
    self.dragging = false;
    try {
      el.releasePointerCapture(ev.pointerId);
    } catch (_e) {
      /* ignore */
    }
    if (moved < 4) {
      var cid = self._pickCountry(ev.clientX, ev.clientY);
      if (cid) {
        self.selectCountry(cid, { emit: true });
      }
    }
  });

  el.addEventListener(
    "wheel",
    function (ev) {
      ev.preventDefault();
      self.distance = Math.max(55, Math.min(140, self.distance + ev.deltaY * 0.06));
      self._updateCamera();
      if (prefersReducedMotion() && self.renderer) {
        self.renderer.render(self.scene, self.camera);
      }
    },
    { passive: false }
  );

  window.addEventListener("resize", function () {
    self._resize();
    if (prefersReducedMotion() && self.renderer) {
      self.renderer.render(self.scene, self.camera);
    }
  });

  if (typeof ResizeObserver !== "undefined") {
    self._resizeObserver = new ResizeObserver(function () {
      self._resize();
      if (self.renderer && self.scene && self.camera) {
        self.renderer.render(self.scene, self.camera);
      }
    });
    self._resizeObserver.observe(el);
  }
};

VoxelWorld.prototype._animate = function () {
  var self = this;
  function frame() {
    self.animId = requestAnimationFrame(frame);
    if (!self.dragging && !self.selectedCountry) {
      self.yaw += 0.00045;
      self._updateCamera();
    }
    self.renderer.render(self.scene, self.camera);
  }
  frame();
};

VoxelWorld.prototype.selectCountry = function (cid, opts) {
  opts = opts || {};
  this.selectedCountry = cid;
  this._applyHighlight();
  if (prefersReducedMotion() && this.renderer) {
    this.renderer.render(this.scene, this.camera);
  }
  if (opts.emit) {
    window.dispatchEvent(
      new CustomEvent("ttb:country-select", { detail: { countryId: cid } })
    );
  }
};

VoxelWorld.prototype.destroy = function () {
  if (this.animId) cancelAnimationFrame(this.animId);
  if (this._resizeObserver) this._resizeObserver.disconnect();
  if (this.renderer) this.renderer.dispose();
};

var instance = null;

TTB.voxelWorld = {
  init: function (container) {
    if (instance) return Promise.resolve(instance.ready);
    instance = new VoxelWorld(container);
    return instance.init().then(function (ok) {
      window.dispatchEvent(new Event("ttb:voxel-ready"));
      return ok;
    });
  },
  setIntelligence: function (countries, visSignalIds, countryEvents) {
    if (instance && instance.ready) instance.setIntelligence(countries, visSignalIds, countryEvents);
  },
  selectCountry: function (cid, opts) {
    if (instance && instance.ready) instance.selectCountry(cid, opts || {});
  },
  isReady: function () {
    return !!(instance && instance.ready);
  },
};

var bootContainer = document.getElementById("dash-voxel-world");
if (bootContainer) {
  TTB.voxelWorld.init(bootContainer);
}
