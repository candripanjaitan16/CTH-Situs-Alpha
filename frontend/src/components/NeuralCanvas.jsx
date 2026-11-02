import { useEffect, useRef } from "react";
import "./NeuralCanvas.css";

const WIDTH = 1280;
const HEIGHT = 720;
const CENTER = { x: WIDTH / 2, y: HEIGHT / 2 };
const TAU = Math.PI * 2;
const clamp = (value, low, high) => Math.max(low, Math.min(high, value));

function seededRandom(seed) {
  let state = seed >>> 0;
  return () => {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    return state / 4294967296;
  };
}

function bezier(start, first, second, end, t) {
  const u = 1 - t;
  return {
    x: u ** 3 * start.x + 3 * u ** 2 * t * first.x + 3 * u * t ** 2 * second.x + t ** 3 * end.x,
    y: u ** 3 * start.y + 3 * u ** 2 * t * first.y + 3 * u * t ** 2 * second.y + t ** 3 * end.y,
  };
}

// Semua jalur disusun dari anak menuju induk, berakhir di pusat.
export function buildNeuralNetwork() {
  const random = seededRandom(2048);
  const nodes = [];
  const edges = [];
  const routes = [];
  const radii = [0.21, 0.44, 0.69, 0.95];
  const sectors = 10;
  const sectorWidth = TAU / sectors;

  function branch(parent, angle, spread, depth) {
    const radius = radii[depth] + (random() - 0.5) * 0.035;
    const node = {
      id: nodes.length,
      x: CENTER.x + Math.cos(angle) * 596 * radius,
      y: CENTER.y + Math.sin(angle) * 320 * radius,
      depth,
      parent,
      children: [],
      phase: random() * TAU,
    };
    nodes.push(node);
    if (parent) parent.children.push(node);

    const end = parent || CENTER;
    const dx = end.x - node.x;
    const dy = end.y - node.y;
    const length = Math.hypot(dx, dy);
    const bend = (random() - 0.5) * length * 0.25;
    const normal = { x: -dy / length, y: dx / length };
    const first = { x: node.x + dx * 0.35 + normal.x * bend, y: node.y + dy * 0.35 + normal.y * bend };
    const second = { x: node.x + dx * 0.72 - normal.x * bend * 0.45, y: node.y + dy * 0.72 - normal.y * bend * 0.45 };
    const samples = Array.from({ length: 25 }, (_, i) => bezier(node, first, second, end, i / 24));
    node.edge = { start: node, first, second, end, samples };
    edges.push(node.edge);

    if (depth < radii.length - 1) {
      const offset = spread * 0.27;
      branch(node, angle - offset + (random() - 0.5) * spread * 0.04, spread / 2, depth + 1);
      branch(node, angle + offset + (random() - 0.5) * spread * 0.04, spread / 2, depth + 1);
    } else {
      const points = [];
      let current = node;
      while (current) {
        points.push(...current.edge.samples.slice(points.length ? 1 : 0));
        current = current.parent;
      }
      let distance = 0;
      const samples = points.map((point, index) => {
        if (index) distance += Math.hypot(point.x - points[index - 1].x, point.y - points[index - 1].y);
        return { ...point, distance };
      });
      routes.push({ samples, length: distance, phase: random(), speed: 67 + random() * 34 });
    }
    return node;
  }

  for (let index = 0; index < sectors; index += 1) {
    branch(null, index * sectorWidth - Math.PI / 2 + 0.035, sectorWidth * 0.91, 0);
  }
  return { nodes, edges, routes };
}

export function pointOnRoute(route, distance) {
  const samples = route.samples;
  const target = clamp(distance, 0, route.length);
  let low = 1;
  let high = samples.length - 1;
  while (low < high) {
    const middle = (low + high) >> 1;
    if (samples[middle].distance < target) low = middle + 1;
    else high = middle;
  }
  const previous = samples[low - 1];
  const next = samples[low];
  const t = (target - previous.distance) / Math.max(0.0001, next.distance - previous.distance);
  return { x: previous.x + (next.x - previous.x) * t, y: previous.y + (next.y - previous.y) * t };
}

const NETWORK = buildNeuralNetwork();
const BRAIN_OUTLINE = "M44 12C34 1 19 8 18 20C5 21 1 37 10 45C2 57 13 70 25 68C27 81 40 82 44 73V12ZM44 12C54 1 69 8 70 20C83 21 87 37 78 45C86 57 75 70 63 68C61 81 48 82 44 73V12Z";
const BRAIN_FOLDS = [
  "M18 20C31 17 35 25 33 34", "M10 45C19 38 30 40 32 49",
  "M25 68C20 58 25 50 34 51", "M23 32C17 31 14 35 16 40",
  "M34 16C40 20 40 27 37 31", "M35 58C39 61 37 70 34 73",
  "M70 20C57 17 53 25 55 34", "M78 45C69 38 58 40 56 49",
  "M63 68C68 58 63 50 54 51", "M65 32C71 31 74 35 72 40",
  "M54 16C48 20 48 27 51 31", "M53 58C49 61 51 70 54 73",
  "M44 34L35 42M44 59L54 50",
];

export default function NeuralCanvas({ active = false }) {
  const containerRef = useRef(null);
  const canvasRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d", { alpha: false });
    if (!container || !context) return undefined;

    const background = document.createElement("canvas");
    const staticContext = background.getContext("2d", { alpha: false });
    if (!staticContext) return undefined;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const brain = new Path2D(BRAIN_OUTLINE);
    const folds = BRAIN_FOLDS.map(path => new Path2D(path));
    let frame = 0;
    let visible = true;
    let width = 0;
    let height = 0;
    let ratio = 1;
    let lastFrame = 0;
    let elapsed = 0;
    let previousTime = 0;
    let disposed = false;

    function worldTransform(ctx) {
      const scale = Math.min(width / WIDTH, height / HEIGHT);
      ctx.setTransform(ratio * scale, 0, 0, ratio * scale,
        ratio * (width - WIDTH * scale) / 2, ratio * (height - HEIGHT * scale) / 2);
    }

    function buildBackground() {
      const ctx = staticContext;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.fillStyle = "#010409";
      ctx.fillRect(0, 0, background.width, background.height);
      worldTransform(ctx);
      const halo = ctx.createRadialGradient(CENTER.x, CENTER.y, 5, CENTER.x, CENTER.y, 260);
      halo.addColorStop(0, "rgba(0, 100, 160, 0.11)");
      halo.addColorStop(0.45, "rgba(0, 40, 75, 0.045)");
      halo.addColorStop(1, "rgba(0, 10, 25, 0)");
      ctx.fillStyle = halo;
      ctx.fillRect(0, 0, WIDTH, HEIGHT);

      ctx.lineWidth = 0.62;
      ctx.strokeStyle = "rgba(27, 111, 164, 0.34)";
      for (const edge of NETWORK.edges) {
        ctx.beginPath();
        ctx.moveTo(edge.start.x, edge.start.y);
        ctx.bezierCurveTo(edge.first.x, edge.first.y, edge.second.x, edge.second.y, edge.end.x, edge.end.y);
        ctx.stroke();
      }
      for (const node of NETWORK.nodes) {
        const size = node.depth === 0 ? 5.4 : node.depth === 3 ? 3.2 : 4.2;
        ctx.fillStyle = node.depth === 3 ? "#071a2d" : "#09243c";
        ctx.strokeStyle = "rgba(45, 137, 195, 0.68)";
        ctx.lineWidth = 0.62;
        ctx.fillRect(node.x - size / 2, node.y - size / 2, size, size);
        ctx.strokeRect(node.x - size / 2, node.y - size / 2, size, size);
      }
    }

    function drawBrain(time, running) {
      const pulse = running ? 0.5 + Math.sin(time * 2.2) * 0.15 : 0.25;
      const halo = context.createRadialGradient(CENTER.x, CENTER.y, 4, CENTER.x, CENTER.y, 74);
      halo.addColorStop(0, `rgba(0, 157, 225, ${0.15 + pulse * 0.10})`);
      halo.addColorStop(1, "rgba(0, 130, 200, 0)");
      context.fillStyle = halo;
      context.fillRect(CENTER.x - 74, CENTER.y - 74, 148, 148);
      context.save();
      context.translate(CENTER.x, CENTER.y);
      context.scale(0.69, 0.69);
      context.translate(-44, -42);
      context.fillStyle = "#032238";
      context.strokeStyle = "#48d5ff";
      context.lineWidth = 1.15;
      context.lineJoin = "round";
      context.lineCap = "round";
      context.shadowColor = "#08afff";
      context.shadowBlur = running ? 14 : 6;
      context.fill(brain);
      context.stroke(brain);
      context.shadowBlur = 0;
      context.strokeStyle = "rgba(74, 205, 247, 0.83)";
      context.lineWidth = 0.9;
      for (const fold of folds) context.stroke(fold);
      context.restore();
    }

    function draw(time) {
      context.setTransform(1, 0, 0, 1, 0, 0);
      context.drawImage(background, 0, 0);
      worldTransform(context);
      const running = active && !reducedMotion.matches;
      if (running) {
        context.lineCap = "round";
        for (const route of NETWORK.routes) {
          const cycle = route.length + 150;
          const position = (time * route.speed + route.phase * cycle) % cycle;
          if (position > route.length + 20) continue;
          // Cahaya maju ke pusat; ekornya tertinggal di sisi sumber.
          for (let index = 5; index >= 0; index -= 1) {
            const head = position - index * 3.4;
            const tail = head - 3.8;
            if (head < 0 || tail > route.length) continue;
            const first = pointOnRoute(route, clamp(tail, 0, route.length));
            const second = pointOnRoute(route, clamp(head, 0, route.length));
            context.beginPath();
            context.moveTo(first.x, first.y);
            context.lineTo(second.x, second.y);
            context.strokeStyle = `rgba(65, 205, 255, ${(1 - index / 6) * 0.77})`;
            context.lineWidth = index === 0 ? 1.3 : 0.85;
            context.stroke();
          }
        }
        for (const node of NETWORK.nodes) {
          const intensity = Math.max(0, Math.sin(time * 1.2 + node.phase) - 0.76);
          if (!intensity) continue;
          context.fillStyle = `rgba(52, 175, 235, ${intensity * 1.9})`;
          context.fillRect(node.x - 1.8, node.y - 1.8, 3.6, 3.6);
        }
      }
      drawBrain(time, running);
    }

    function animate(timestamp) {
      frame = 0;
      if (disposed || !active || reducedMotion.matches || !visible || document.hidden) return;
      if (!previousTime) previousTime = timestamp;
      elapsed += Math.min((timestamp - previousTime) / 1000, 0.1);
      previousTime = timestamp;
      if (timestamp - lastFrame >= 1000 / 30) {
        lastFrame = timestamp;
        draw(elapsed);
      }
      frame = window.requestAnimationFrame(animate);
    }

    function syncAnimation() {
      window.cancelAnimationFrame(frame);
      frame = 0;
      previousTime = 0;
      draw(elapsed);
      if (active && !reducedMotion.matches && visible && !document.hidden) {
        frame = window.requestAnimationFrame(animate);
      }
    }

    function resize() {
      const rect = container.getBoundingClientRect();
      width = Math.max(1, rect.width);
      height = Math.max(1, rect.height);
      ratio = Math.min(window.devicePixelRatio || 1, 1.5);
      canvas.width = background.width = Math.round(width * ratio);
      canvas.height = background.height = Math.round(height * ratio);
      buildBackground();
      syncAnimation();
    }

    const resizeObserver = new ResizeObserver(resize);
    const intersectionObserver = new IntersectionObserver(entries => {
      visible = entries[0]?.isIntersecting ?? true;
      syncAnimation();
    }, { threshold: 0 });
    resizeObserver.observe(container);
    intersectionObserver.observe(container);
    reducedMotion.addEventListener("change", syncAnimation);
    document.addEventListener("visibilitychange", syncAnimation);
    resize();

    return () => {
      disposed = true;
      window.cancelAnimationFrame(frame);
      resizeObserver.disconnect();
      intersectionObserver.disconnect();
      reducedMotion.removeEventListener("change", syncAnimation);
      document.removeEventListener("visibilitychange", syncAnimation);
      background.width = background.height = 0;
    };
  }, [active]);

  return (
    <div className="cth-neural-field" ref={containerRef} data-active={active ? "true" : "false"}>
      <canvas ref={canvasRef} role="img"
        aria-label={`Jaringan 150 kotak bercabang dua menuju otak kecil di pusat. ${active ? "Aliran visual aktif dari kotak terluar ke otak." : "Aliran visual diam."}`} />
      <div className="cth-neural-field-caption" aria-hidden="true">
        <span className={active ? "is-active" : ""} />
        {active ? "ALIRAN MASUK · SUMBER MENUJU OTAK" : "JARINGAN SARAF · VISUAL DIAM"}
      </div>
    </div>
  );
}
