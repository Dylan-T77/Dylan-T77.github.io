/* ============================================================
   Dylan Thiart // Portfolio enhancements
   Vanilla JS, zero dependencies. Respects prefers-reduced-motion.
   ============================================================ */

(function () {
  "use strict";

  const REDUCE_MOTION = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- 1. Boot sequence overlay ---------- */
  function bootSequence() {
    if (REDUCE_MOTION) return;

    const overlay = document.createElement("div");
    overlay.id = "boot-overlay";
    overlay.innerHTML = `
      <div class="boot-lines">
        <p>&gt; INITIALIZING SYSTEM<span class="cursor-blink">_</span></p>
      </div>`;
    document.body.prepend(overlay);
    document.body.classList.add("boot-lock");

    const lines = [
      "LOADING MODULES ....... OK",
      "MOUNTING INTERFACE ..... OK",
      "SYSTEM ONLINE",
    ];
    const container = overlay.querySelector(".boot-lines");
    let i = 0;

    const step = () => {
      if (i < lines.length) {
        const p = document.createElement("p");
        p.textContent = "> " + lines[i];
        container.appendChild(p);
        i++;
        setTimeout(step, 160);
      } else {
        setTimeout(() => {
          overlay.classList.add("boot-out");
          document.body.classList.remove("boot-lock");
          setTimeout(() => overlay.remove(), 500);
        }, 250);
      }
    };
    setTimeout(step, 200);
  }

  /* ---------- 2. Live UTC+02:00 clock in the HUD corner ---------- */
  function liveClock() {
    const el = document.querySelector(".top-right");
    if (!el) return;
    const locationLine = "01. // CAPE TOWN";

    function render() {
      const now = new Date(Date.now() + 2 * 60 * 60 * 1000); // UTC+02:00
      const hh = String(now.getUTCHours()).padStart(2, "0");
      const mm = String(now.getUTCMinutes()).padStart(2, "0");
      const ss = String(now.getUTCSeconds()).padStart(2, "0");
      el.innerHTML = `${locationLine}<br>UTC+02:00 // ${hh}:${mm}:${ss}`;
    }
    render();
    setInterval(render, 1000);
  }

  /* ---------- 3. Animated particle / network-grid background ---------- */
  function particleField() {
    if (REDUCE_MOTION) return;

    const canvas = document.createElement("canvas");
    canvas.id = "bg-field";
    document.body.prepend(canvas);
    const ctx = canvas.getContext("2d");

    let w, h, particles;
    const DENSITY = 14000; // px^2 per particle — lower = more particles
    const LINK_DIST = 130;
    const mouse = { x: null, y: null };

    function resize() {
      w = canvas.width = window.innerWidth;
      h = canvas.height = window.innerHeight;
      const count = Math.min(120, Math.floor((w * h) / DENSITY));
      particles = Array.from({ length: count }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.25,
        vy: (Math.random() - 0.5) * 0.25,
      }));
    }

    function step() {
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = "rgba(97,246,197,0.55)";
      ctx.strokeStyle = "rgba(97,246,197,0.12)";

      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0 || p.x > w) p.vx *= -1;
        if (p.y < 0 || p.y > h) p.vy *= -1;

        // gentle pull toward cursor
        if (mouse.x !== null) {
          const dx = mouse.x - p.x;
          const dy = mouse.y - p.y;
          const dist = Math.hypot(dx, dy);
          if (dist < 160) {
            p.x += dx * 0.0025;
            p.y += dy * 0.0025;
          }
        }
      }

      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const a = particles[i], b = particles[j];
          const d = Math.hypot(a.x - b.x, a.y - b.y);
          if (d < LINK_DIST) {
            ctx.globalAlpha = 1 - d / LINK_DIST;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
      }
      ctx.globalAlpha = 1;
      for (const p of particles) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, 1.4, 0, Math.PI * 2);
        ctx.fill();
      }

      requestAnimationFrame(step);
    }

    window.addEventListener("resize", resize);
    window.addEventListener("mousemove", (e) => {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
    });
    window.addEventListener("mouseleave", () => {
      mouse.x = null;
      mouse.y = null;
    });

    resize();
    requestAnimationFrame(step);
  }

  /* ---------- 4. Scroll-triggered reveal ---------- */
  function scrollReveal() {
    const targets = document.querySelectorAll(
      ".section-content, .project, .system-panel, .reference-card, .device"
    );
    if (!targets.length) return;

    targets.forEach((el) => el.classList.add("reveal"));

    if (REDUCE_MOTION || !("IntersectionObserver" in window)) {
      targets.forEach((el) => el.classList.add("in-view"));
      return;
    }

    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("in-view");
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15, rootMargin: "0px 0px -40px 0px" }
    );

    targets.forEach((el) => io.observe(el));
  }

  /* ---------- 5. Glitch-scramble intro on the hero heading ---------- */
  function glitchHeading() {
    const target = document.querySelector(".hero h1");
    if (!target || REDUCE_MOTION) return;

    const chars = "!<>-_\\/[]{}—=+*^?#01";
    // capture original nodes (text + <span> child) so we can restore exactly
    const original = target.innerHTML;
    const plain = target.textContent;
    let frame = 0;
    const totalFrames = 18;

    function scramble() {
      let out = "";
      const revealCount = Math.floor((frame / totalFrames) * plain.length);
      for (let i = 0; i < plain.length; i++) {
        if (plain[i] === "\n" || plain[i] === " ") {
          out += plain[i];
        } else if (i < revealCount) {
          out += plain[i];
        } else {
          out += chars[Math.floor(Math.random() * chars.length)];
        }
      }
      target.textContent = out;
      frame++;
      if (frame <= totalFrames) {
        requestAnimationFrame(() => setTimeout(scramble, 28));
      } else {
        target.innerHTML = original; // restore real markup (the <span> styling)
      }
    }
    scramble();
  }

  /* ---------- init ---------- */
  document.addEventListener("DOMContentLoaded", () => {
    bootSequence();
    liveClock();
    particleField();
    scrollReveal();
    glitchHeading();
  });

  console.log("Dylan Thiart portfolio loaded // enhanced build.");
})();
