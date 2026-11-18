// The classic CPT plot: cone resistance, sleeve friction, soil behaviour type index and
// liquefaction factor of safety against depth, side by side. Plain SVG.

import { FS_CLASSES, factorOfSafety, fsClass, lpi, lpiLabel } from "./liquefaction";
import type { DetailRow, Hole, SitesData } from "./types";

const W = 132; // panel width
const GAP = 14;
const TOP = 34;
const LEFT = 40;
const H = 380; // plot height

// Robertson zone boundaries on the Isbt axis, for the Ic panel's background bands.
const IC_BANDS: [number, number, string][] = [
  [1.0, 1.31, "7"],
  [1.31, 2.05, "6"],
  [2.05, 2.6, "5"],
  [2.6, 2.95, "4"],
  [2.95, 3.6, "3"],
  [3.6, 4.0, "2"],
];

const niceMax = (v: number) => {
  if (!(v > 0)) return 1;
  const p = 10 ** Math.floor(Math.log10(v));
  return [1, 2, 2.5, 5, 10].map((m) => m * p).find((m) => m >= v) ?? v;
};

function polyline(rows: DetailRow[], col: number, x: (v: number) => number, y: (d: number) => number, max: number): string {
  // Break the line where values are missing, so gaps aren't joined across.
  const parts: string[] = [];
  let cur: string[] = [];
  for (const r of rows) {
    const v = r[col];
    if (v === null || !Number.isFinite(v)) {
      if (cur.length > 1) parts.push(cur.join(" "));
      cur = [];
      continue;
    }
    cur.push(`${x(Math.min(Math.max(v, 0), max)).toFixed(1)},${y(r[0]).toFixed(1)}`);
  }
  if (cur.length > 1) parts.push(cur.join(" "));
  return parts.map((p) => `<polyline points="${p}"/>`).join("");
}

export function traceChart(hole: Hole, rows: DetailRow[], data: SitesData, pga: number): string {
  const maxDepth = Math.ceil(hole.depth ?? rows[rows.length - 1]?.[0] ?? 10);
  const y = (d: number) => TOP + (d / maxDepth) * H;
  const qcMax = niceMax(Math.max(...rows.map((r) => r[1] ?? 0)));
  const fsMax = niceMax(Math.max(...rows.map((r) => r[2] ?? 0)));
  const fsRows = rows.map((r) => [r[0], factorOfSafety(r, pga)] as [number, number | null]);

  const panels = [
    { title: "Cone resistance qc", unit: "MPa", max: qcMax },
    { title: "Sleeve friction fs", unit: "MPa", max: fsMax },
    { title: "Soil type index Ic", unit: "", max: 4 },
    { title: `Factor of safety (${pga} g)`, unit: "", max: 2 },
  ];
  const width = LEFT + panels.length * (W + GAP);
  const height = TOP + H + 30;
  const px = (i: number) => LEFT + i * (W + GAP);

  const out: string[] = [`<svg viewBox="0 0 ${width} ${height}" class="trace" role="img" aria-label="CPT trace for ${hole.id}">`];

  // Depth gridlines and labels (shared).
  const step = maxDepth > 12 ? 2 : 1;
  for (let d = 0; d <= maxDepth; d += step) {
    out.push(`<line class="grid" x1="${LEFT}" x2="${width - GAP}" y1="${y(d)}" y2="${y(d)}"/>`);
    out.push(`<text class="tick" x="${LEFT - 6}" y="${y(d) + 3.5}" text-anchor="end">${d}</text>`);
  }
  out.push(`<text class="axis" transform="translate(11 ${TOP + H / 2}) rotate(-90)" text-anchor="middle">depth (m)</text>`);

  panels.forEach((p, i) => {
    const x0 = px(i);
    const x = (v: number) => x0 + (v / p.max) * W;
    out.push(`<text class="title" x="${x0 + W / 2}" y="14" text-anchor="middle">${p.title}</text>`);

    if (i === 2) {
      for (const [lo, hi, zone] of IC_BANDS) {
        const xl = x0 + ((lo - 1) / 3) * W;
        const xr = x0 + ((hi - 1) / 3) * W;
        out.push(`<rect x="${xl}" y="${TOP}" width="${xr - xl}" height="${H}" fill="${data.zones[zone].colour}" opacity="0.35"><title>${data.zones[zone].label}</title></rect>`);
      }
    }
    if (i === 3) {
      // Colour the FS panel's background by class, depth by depth.
      let prev = 0;
      for (const [d, fs] of fsRows) {
        const c = fsClass(fs);
        out.push(`<rect x="${x0}" y="${y(prev)}" width="${W}" height="${Math.max(y(d) - y(prev), 0.5)}" fill="${c.colour}" opacity="${c === FS_CLASSES.na ? 0.25 : 0.45}"/>`);
        prev = d;
      }
    }

    out.push(`<rect class="frame" x="${x0}" y="${TOP}" width="${W}" height="${H}"/>`);
    const ticks = i === 2 ? [1, 2, 3, 4] : [0, p.max / 2, p.max];
    for (const t of ticks) {
      const tx = i === 2 ? x0 + ((t - 1) / 3) * W : x(t);
      out.push(`<text class="tick" x="${tx}" y="${TOP - 5}" text-anchor="middle">${+t.toFixed(2)}</text>`);
    }
    if (p.unit) out.push(`<text class="tick" x="${x0 + W}" y="${TOP + H + 14}" text-anchor="end">${p.unit}</text>`);

    if (i === 0) out.push(`<g class="line">${polyline(rows, 1, x, y, p.max)}</g>`);
    if (i === 1) out.push(`<g class="line">${polyline(rows, 2, x, y, p.max)}</g>`);
    if (i === 2) {
      const xIc = (v: number) => x0 + ((Math.min(Math.max(v, 1), 4) - 1) / 3) * W;
      out.push(`<g class="line">${polyline(rows, 4, xIc, y, 4)}</g>`);
    }
    if (i === 3) {
      const fsAsRows = fsRows.map(([d, fs]) => [d, fs] as unknown as DetailRow);
      out.push(`<g class="line">${polyline(fsAsRows, 1, x, y, p.max)}</g>`);
      out.push(`<line class="fs-one" x1="${x(1)}" x2="${x(1)}" y1="${TOP}" y2="${TOP + H}"/>`);
    }
  });

  if (hole.gw !== null) {
    out.push(`<line class="water" x1="${LEFT}" x2="${width - GAP}" y1="${y(hole.gw)}" y2="${y(hole.gw)}"/>`);
    out.push(`<text class="water-label" x="${width - GAP}" y="${y(hole.gw) - 4}" text-anchor="end">groundwater ${hole.gw} m</text>`);
  }
  out.push("</svg>");

  const index = lpi(rows, pga);
  return `
    <header>
      <div><strong>${hole.id}</strong> · ${hole.date} · ${hole.depth} m deep</div>
      <button class="close" aria-label="Close">×</button>
    </header>
    ${out.join("")}
    <p class="lpi">Liquefaction potential index at ${pga} g: <strong>${index.toFixed(1)}</strong> (${lpiLabel(index)}).
    Readings shown every 2 cm.</p>`;
}
