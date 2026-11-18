// deck.gl layers for one OSU site: CPT columns or a fence diagram, coloured by soil
// behaviour type or by liquefaction factor of safety.

import { COORDINATE_SYSTEM, type Layer } from "@deck.gl/core";
import { ColumnLayer, PathLayer, SolidPolygonLayer, TextLayer } from "@deck.gl/layers";
import { factorOfSafety, fsClass } from "./liquefaction";
import type { Hole, P3, RGBA, Site, SiteDetail, SitesData, Slice } from "./types";

export type ColourBy = "soil" | "liquefaction";
export type Shape = "columns" | "fence";

export interface SiteOptions {
  exag: number;
  colourBy: ColourBy;
  shape: Shape;
  pga: number;
  showWater: boolean;
  showNzgd: boolean;
  dark: boolean;
}

const COLUMN_RADIUS = 0.3; // m. The real cone is 3.6 cm across; drawn wider to be visible.
const FENCE_THICKNESS = 0.14; // m
const FENCE_MAX_HALF = 1.0; // m. Don't stretch a panel more than this either side.
const WATER_RGBA: RGBA = [47, 127, 209, 255];
const NZGD_RGBA: RGBA = [120, 114, 104, 255];
const GRID_STEP = 5; // m
const CARTESIAN = { coordinateSystem: COORDINATE_SYSTEM.CARTESIAN };

export const hexToRgba = (hex: string, alpha = 255): RGBA => [
  parseInt(hex.slice(1, 3), 16),
  parseInt(hex.slice(3, 5), 16),
  parseInt(hex.slice(5, 7), 16),
  alpha,
];

/** Coloured slices for every OSU CPT at a site. */
export function buildSlices(site: Site, data: SitesData, detail: SiteDetail | null, opts: SiteOptions): Slice[] {
  const osu = site.holes.filter((h) => h.source === "osu");
  if (opts.colourBy === "liquefaction" && detail) {
    // Merge consecutive 2 cm rows that fall in the same FS class.
    return osu.flatMap((hole) => {
      const rows = detail.holes[hole.id] ?? [];
      const out: Slice[] = [];
      let prev = 0;
      for (const row of rows) {
        const c = fsClass(factorOfSafety(row, opts.pga));
        const last = out[out.length - 1];
        if (last && last.label === c.label) last.bottom = row[0];
        else out.push({ hole, top: prev, bottom: row[0], rgba: c.rgba, label: c.label });
        prev = row[0];
      }
      return out;
    });
  }
  return osu.flatMap((hole) =>
    (hole.intervals ?? []).map(([top, bottom, zone]) => ({
      hole,
      top,
      bottom,
      rgba: hexToRgba(data.zones[String(zone)].colour),
      label: data.zones[String(zone)].label,
    })),
  );
}

/**
 * Fence panels: each CPT owns the stretch of the line halfway to its neighbours
 * (nearest-neighbour, nothing invented between holes), capped at FENCE_MAX_HALF.
 * Panels sit on the fitted line, so GPS jitter doesn't make them zig-zag.
 * Where two CPTs are within 0.5 m (S-9, S-9A, S-9B) only the deepest is used.
 */
function fenceExtents(site: Site): Map<string, [number, number]> {
  const osu = site.holes
    .filter((h) => h.source === "osu")
    .sort((a, b) => a.s - b.s)
    .filter((h, _, all) => !all.some((o) => o !== h && Math.abs(o.s - h.s) < 0.5 && (o.depth ?? 0) > (h.depth ?? 0)));
  const ext = new Map<string, [number, number]>();
  osu.forEach((h, i) => {
    const left = i > 0 ? Math.min((h.s - osu[i - 1].s) / 2, FENCE_MAX_HALF) : 0.75;
    const right = i < osu.length - 1 ? Math.min((osu[i + 1].s - h.s) / 2, FENCE_MAX_HALF) : 0.75;
    ext.set(h.id, [h.s - left, h.s + right]);
  });
  return ext;
}

function fencePolygon(site: Site, from: number, to: number, z: number): P3[] {
  const [ux, uy] = site.axis;
  const [nx, ny] = [-uy * (FENCE_THICKNESS / 2), ux * (FENCE_THICKNESS / 2)];
  const a: [number, number] = [ux * from, uy * from];
  const b: [number, number] = [ux * to, uy * to];
  return [
    [a[0] - nx, a[1] - ny, z],
    [b[0] - nx, b[1] - ny, z],
    [b[0] + nx, b[1] + ny, z],
    [a[0] + nx, a[1] + ny, z],
  ];
}

export function siteLayers(site: Site, slices: Slice[], opts: SiteOptions): Layer[] {
  const { exag, dark } = opts;
  const z = (h: Hole, depth: number) => (h.ground - depth) * exag;
  const osu = site.holes.filter((h) => h.source === "osu");
  const nzgd = site.holes.filter((h) => h.source === "nzgd");
  const triggers = { exag, colourBy: opts.colourBy, pga: opts.pga, shape: opts.shape };

  // Ground plane, grid and depth ruler, sized to the site.
  const xs = site.holes.map((h) => h.x);
  const ys = site.holes.map((h) => h.y);
  const pad = 4;
  const [x0, x1] = [Math.min(...xs) - pad, Math.max(...xs) + pad];
  const [y0, y1] = [Math.min(...ys) - pad, Math.max(...ys) + pad];
  const maxDepth = Math.ceil(Math.max(...site.holes.map((h) => h.depth ?? 0)));

  const grid: { path: P3[] }[] = [];
  for (let x = Math.ceil(x0 / GRID_STEP) * GRID_STEP; x <= x1; x += GRID_STEP) grid.push({ path: [[x, y0, 0], [x, y1, 0]] });
  for (let y = Math.ceil(y0 / GRID_STEP) * GRID_STEP; y <= y1; y += GRID_STEP) grid.push({ path: [[x0, y, 0], [x1, y, 0]] });

  const ruler: { path: P3[] }[] = [{ path: [[x0, y0, 0], [x0, y0, -maxDepth * exag]] }];
  const rulerLabels: { position: P3; text: string }[] = [];
  for (let d = 0; d <= maxDepth; d += 2) {
    ruler.push({ path: [[x0, y0, -d * exag], [x0 + 0.8, y0, -d * exag]] });
    rulerLabels.push({ position: [x0 - 0.4, y0, -d * exag], text: `${d} m` });
  }

  const ink: RGBA = dark ? [236, 232, 225, 255] : [31, 29, 26, 255];
  const muted: RGBA = dark ? [156, 150, 140, 255] : [107, 102, 94, 255];

  const shapeLayer =
    opts.shape === "fence"
      ? (() => {
          const ext = fenceExtents(site);
          const panels = slices.filter((s) => ext.has(s.hole.id));
          return new SolidPolygonLayer<Slice>({
            ...CARTESIAN,
            // A different id from the columns: deck.gl can't swap a layer's type in place.
            id: "cpt-fence",
            data: panels,
            extruded: true,
            pickable: true,
            autoHighlight: true,
            highlightColor: [255, 255, 255, 90],
            getPolygon: (s) => {
              const [from, to] = ext.get(s.hole.id)!;
              return fencePolygon(site, from, to, z(s.hole, s.bottom));
            },
            getElevation: (s) => (s.bottom - s.top) * exag,
            getFillColor: (s) => s.rgba,
            updateTriggers: { getPolygon: triggers, getElevation: triggers, getFillColor: triggers },
          });
        })()
      : new ColumnLayer<Slice>({
          ...CARTESIAN,
          id: "cpt",
          data: slices,
          diskResolution: 20,
          radius: COLUMN_RADIUS,
          extruded: true,
          pickable: true,
          autoHighlight: true,
          highlightColor: [255, 255, 255, 90],
          getPosition: (s) => [s.hole.x, s.hole.y, z(s.hole, s.bottom)],
          getElevation: (s) => (s.bottom - s.top) * exag,
          getFillColor: (s) => s.rgba,
          updateTriggers: { getPosition: triggers, getElevation: triggers, getFillColor: triggers },
        });

  // Fence mode puts the water markers on the fitted line too, so they sit on the panels.
  const waterPos = (h: Hole): P3 =>
    opts.shape === "fence"
      ? [site.axis[0] * h.s, site.axis[1] * h.s, z(h, h.gw ?? 0) - 0.03]
      : [h.x, h.y, z(h, h.gw ?? 0) - 0.03];

  return [
    shapeLayer,
    new ColumnLayer<Hole>({
      ...CARTESIAN,
      id: "nzgd",
      data: nzgd,
      visible: opts.showNzgd,
      diskResolution: 12,
      radius: COLUMN_RADIUS,
      extruded: true,
      filled: false,
      wireframe: true,
      pickable: true,
      getPosition: (h) => [h.x, h.y, z(h, h.depth ?? 0)],
      getElevation: (h) => (h.depth ?? 0) * exag,
      getLineColor: NZGD_RGBA,
      updateTriggers: { getPosition: exag, getElevation: exag },
    }),
    new ColumnLayer<Hole>({
      ...CARTESIAN,
      id: "water",
      data: osu.filter((h) => h.gw !== null),
      visible: opts.showWater,
      diskResolution: 20,
      radius: opts.shape === "fence" ? 0.35 : COLUMN_RADIUS * 1.9,
      extruded: true,
      pickable: true,
      getPosition: waterPos,
      getElevation: 0.06,
      getFillColor: WATER_RGBA,
      updateTriggers: { getPosition: triggers },
    }),
    new SolidPolygonLayer<{ polygon: P3[] }>({
      ...CARTESIAN,
      id: "ground",
      data: [{ polygon: [[x0, y0, 0], [x1, y0, 0], [x1, y1, 0], [x0, y1, 0]] }],
      getPolygon: (d) => d.polygon,
      getFillColor: dark ? [90, 80, 64, 70] : [140, 120, 90, 45],
      // Translucent: don't write depth, so columns below still show through.
      parameters: { depthWriteEnabled: false },
    }),
    new PathLayer<{ path: P3[] }>({
      ...CARTESIAN,
      id: "grid",
      data: grid,
      getPath: (d) => d.path,
      getColor: dark ? [255, 255, 255, 40] : [60, 50, 40, 50],
      getWidth: 1,
      widthUnits: "pixels",
    }),
    new PathLayer<{ path: P3[] }>({
      ...CARTESIAN,
      id: "ruler",
      data: ruler,
      getPath: (d) => d.path,
      getColor: muted,
      getWidth: 1.5,
      widthUnits: "pixels",
      updateTriggers: { getPath: exag },
    }),
    new TextLayer<{ position: P3; text: string }>({
      ...CARTESIAN,
      id: "ruler-labels",
      data: rulerLabels,
      getPosition: (d) => d.position,
      getText: (d) => d.text,
      getSize: 11,
      getColor: muted,
      getTextAnchor: "end",
      getAlignmentBaseline: "center",
      fontFamily: "system-ui, sans-serif",
      updateTriggers: { getPosition: exag },
    }),
    new TextLayer<Hole>({
      ...CARTESIAN,
      id: "labels",
      data: site.holes.filter((h) => h.source === "osu" || opts.showNzgd),
      getPosition: (h) => [h.x, h.y, h.ground * exag + 0.6],
      getText: (h) => h.id.replace(/^OSU /, ""),
      getSize: 11,
      getColor: (h) => (h.source === "osu" ? ink : muted),
      getAlignmentBaseline: "bottom",
      fontFamily: "system-ui, sans-serif",
      updateTriggers: { getPosition: exag, getColor: dark },
    }),
  ];
}
