// Decorative hero background: one budget fanning out to three recipients.
// Sits at z-index -3 behind .hero-veil, so it stays quiet under the headline.
// The page must remain fully functional if this never draws.
//
// public.js imports this module and renders <canvas class="hero-flow">, so the
// module mounts itself onto those canvases and follows the router's re-renders.
// mountHeroFlow stays exported and idempotent: calling it directly on a canvas
// this module already mounted returns the existing stop function rather than
// starting a second loop.

const ACCENT = "255,75,0"; // --accent #ff4b00
const MUTED = "174,184,201"; // --muted #aeb8c9

// Recipient shares of the spend pool: Amara 40%, Kwame 35%, Elena 25%.
const LANES = [
  { end: 0.24, weight: 0.4 },
  { end: 0.5, weight: 0.35 },
  { end: 0.76, weight: 0.25 },
];

const live = new Map(); // canvas -> stop()

const point = (from, control, to, t) => {
  const inv = 1 - t;
  return {
    x: inv * inv * from.x + 2 * inv * t * control.x + t * t * to.x,
    y: inv * inv * from.y + 2 * inv * t * control.y + t * t * to.y,
  };
};

export function mountHeroFlow(canvas) {
  if (!canvas) return () => {};
  const already = live.get(canvas);
  if (already) return already;

  canvas.setAttribute("aria-hidden", "true");

  const context = canvas.getContext && canvas.getContext("2d");
  if (!context) return () => {};

  const stillOnly = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let width = 0;
  let height = 0;
  let frame = 0;
  let stopped = false;

  const particles = LANES.flatMap((lane, index) =>
    Array.from({ length: 5 }, (_, step) => ({
      lane: index,
      t: (step + index * 0.3) / 5,
      speed: 0.0016 + lane.weight * 0.0022,
    })),
  );

  function resize() {
    const rect = canvas.getBoundingClientRect();
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    width = rect.width;
    height = rect.height;
    canvas.width = Math.max(1, Math.round(width * ratio));
    canvas.height = Math.max(1, Math.round(height * ratio));
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
  }

  function geometry(lane) {
    return {
      from: { x: width * 0.08, y: height * 0.52 },
      control: { x: width * 0.52, y: height * (0.52 - (lane.end - 0.5) * 0.5) },
      to: { x: width * 0.94, y: height * lane.end },
    };
  }

  function draw() {
    if (width < 2 || height < 2) return;
    context.clearRect(0, 0, width, height);

    // Faint measure lines, so the open right half still reads as a surface.
    context.strokeStyle = `rgba(${MUTED},0.05)`;
    context.lineWidth = 1;
    for (let x = width * 0.2; x < width; x += width * 0.12) {
      context.beginPath();
      context.moveTo(x, height * 0.12);
      context.lineTo(x, height * 0.88);
      context.stroke();
    }

    LANES.forEach((lane) => {
      const { from, control, to } = geometry(lane);
      context.strokeStyle = `rgba(${ACCENT},${0.1 + lane.weight * 0.16})`;
      context.lineWidth = 1 + lane.weight * 1.6;
      context.beginPath();
      context.moveTo(from.x, from.y);
      context.quadraticCurveTo(control.x, control.y, to.x, to.y);
      context.stroke();

      // Recipient node, sized by that recipient's share.
      context.fillStyle = `rgba(${ACCENT},0.5)`;
      context.beginPath();
      context.arc(to.x, to.y, 3 + lane.weight * 3, 0, Math.PI * 2);
      context.fill();
    });

    particles.forEach((particle) => {
      const lane = LANES[particle.lane];
      const { from, control, to } = geometry(lane);
      const at = point(from, control, to, particle.t);
      const fade = Math.sin(Math.PI * particle.t);
      context.fillStyle = `rgba(${ACCENT},${0.25 + fade * 0.5})`;
      context.beginPath();
      context.arc(at.x, at.y, 1.4 + lane.weight * 2.2, 0, Math.PI * 2);
      context.fill();
    });

    // The single budget the three lanes come out of.
    const source = geometry(LANES[1]).from;
    context.fillStyle = `rgba(${ACCENT},0.75)`;
    context.beginPath();
    context.arc(source.x, source.y, 5, 0, Math.PI * 2);
    context.fill();
    context.strokeStyle = `rgba(${ACCENT},0.22)`;
    context.lineWidth = 1;
    context.beginPath();
    context.arc(source.x, source.y, 12, 0, Math.PI * 2);
    context.stroke();
  }

  function tick() {
    if (stopped) return;
    if (width < 2 || height < 2) {
      frame = 0; // hidden or unsized; the resize observer restarts the loop
      return;
    }
    particles.forEach((particle) => {
      particle.t += particle.speed;
      if (particle.t > 1) particle.t -= 1;
    });
    draw();
    frame = window.requestAnimationFrame(tick);
  }

  function restart() {
    if (stopped) return;
    resize();
    draw();
    if (stillOnly) return;
    window.cancelAnimationFrame(frame);
    frame = window.requestAnimationFrame(tick);
  }

  let observer = null;
  if (typeof ResizeObserver === "function") {
    observer = new ResizeObserver(restart);
    observer.observe(canvas);
  } else {
    window.addEventListener("resize", restart);
  }

  restart();

  const stop = () => {
    stopped = true;
    window.cancelAnimationFrame(frame);
    if (observer) observer.disconnect();
    else window.removeEventListener("resize", restart);
    live.delete(canvas);
  };
  live.set(canvas, stop);
  return stop;
}

function sweep() {
  document.querySelectorAll("canvas.hero-flow").forEach((canvas) => mountHeroFlow(canvas));
  live.forEach((stop, canvas) => {
    if (!canvas.isConnected) stop();
  });
}

function watch() {
  sweep();
  if (typeof MutationObserver !== "function") return;
  // The router replaces #main-content wholesale, so re-scan after each render.
  new MutationObserver(sweep).observe(document.body, { childList: true, subtree: true });
}

if (typeof document !== "undefined") {
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", watch, { once: true });
  else watch();
}
