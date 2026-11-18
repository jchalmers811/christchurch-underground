// 3D viewer for the OSU CPT sites. Data comes from `python -m chch_pipeline.export_web`.
//
// The scene is a local Cartesian frame in metres: x = east, y = north (NZTM2000, relative
// to the site centre), z = up. Depths below ground become negative z, multiplied by the
// vertical exaggeration.

import { COORDINATE_SYSTEM, Deck, OrbitView, type OrbitViewState, type PickingInfo } from "@deck.gl/core";
import { ColumnLayer, PathLayer, SolidPolygonLayer, TextLayer } from "@deck.gl/layers";

type Interval = [top: number, bottom: number, zone: number];

interface Hole {
  id: string;
  source: "osu" | "nzgd";
  kind: string;
  x: number;
  y: number;
  ground: number;
  depth: number | null;
  gw: number | null;
  date: string;
  intervals?: Interval[];
}

interface Site {
  id: string;
  name: string;
  caption: string;
  origin: [number, number];
  holes: Hole[];
}

interface Data {
  zones: Record<string, { label: string; colour: string }>;
  sites: Site[];
}

/** One drawable slice of a CPT column. */
interface Slice {
  hole: Hole;
  top: number;
  bottom: number;
  zone: number;
}

type RGBA = [number, number, number, number];
type P3 = [number, number, number];

const COLUMN_RADIUS = 0.3; // m. The real cone is 3.6 cm across; drawn wider to be visible.
const WATER_RGBA: RGBA = [47, 127, 209, 255];
const NZGD_RGBA: RGBA = [120, 114, 104, 255];
const GRID_STEP = 5; // m

const state = {
  data: null as Data | null,
  site: null as Site | null,
  exag: 1,
  showWater: true,
  showNzgd: true,
};

const hexToRgba = (hex: string, alpha = 255): RGBA => [
  parseInt(hex.slice(1, 3), 16),
  parseInt(hex.slice(3, 5), 16),
  parseInt(hex.slice(5, 7), 16),
  alpha,
];

const isDark = () => window.matchMedia("(prefers-color-scheme: dark)").matches;

const deck = new Deck<OrbitView>({
  parent: document.getElementById("viewer") as HTMLDivElement,
  views: new OrbitView({ orbitAxis: "Z", fovy: 35 }),
  controller: true,
  initialViewState: { target: [0, 0, 0], zoom: 3, rotationX: 25, rotationOrbit: -35 },
  getTooltip: ({ object, layer }: PickingInfo) => {
    if (!object || !state.data) return null;
    if (layer?.id === "cpt") {
      const s = object as Slice;
      const label = state.data.zones[String(s.zone)]?.label ?? "Unknown";
      return {
        html: `<strong>${s.hole.id}</strong><br>${s.top.toFixed(2)}–${s.bottom.toFixed(2)} m · ${label}`,
      };
    }
    const h = object as Hole;
    if (layer?.id === "nzgd") {
      return { html: `<strong>${h.id}</strong> · ${h.kind} · ${h.depth ?? "?"} m<br>Held in the NZGD, not available here` };
    }
    if (layer?.id === "water") {
      return { html: `<strong>${h.id}</strong><br>Groundwater at ${h.gw} m (from CPT)` };
    }
    return null;
  },
});

/** Fit the camera to a site: centred on the middle of the columns, sized to the window. */
function viewFor(site: Site): OrbitViewState {
  const xs = site.holes.map((h) => h.x);
  const ys = site.holes.map((h) => h.y);
  const maxDepth = Math.max(...site.holes.map((h) => h.depth ?? 0));
  const extent = Math.max(
    Math.max(...xs) - Math.min(...xs),
    Math.max(...ys) - Math.min(...ys),
    maxDepth * state.exag,
  ) + 8;
  const viewer = document.getElementById("viewer")!;
  const px = Math.min(viewer.clientWidth, viewer.clientHeight);
  return {
    target: [0, 0, (-maxDepth * state.exag) / 2],
    zoom: Math.log2((px * 0.75) / extent),
    rotationX: 25,
    rotationOrbit: -35,
    transitionDuration: 600,
  } as OrbitViewState;
}

function render(): void {
  const { data, site, exag } = state;
  if (!data || !site) return;

  const osu = site.holes.filter((h) => h.source === "osu");
  const nzgd = site.holes.filter((h) => h.source === "nzgd");
  const slices: Slice[] = osu.flatMap((hole) =>
    (hole.intervals ?? []).map(([top, bottom, zone]) => ({ hole, top, bottom, zone })),
  );
  const zoneRgba = Object.fromEntries(
    Object.entries(data.zones).map(([z, v]) => [z, hexToRgba(v.colour)]),
  ) as Record<string, RGBA>;

  // Ground plane and depth ruler, sized to the site.
  const xs = site.holes.map((h) => h.x);
  const ys = site.holes.map((h) => h.y);
  const pad = 4;
  const [x0, x1] = [Math.min(...xs) - pad, Math.max(...xs) + pad];
  const [y0, y1] = [Math.min(...ys) - pad, Math.max(...ys) + pad];
  const maxDepth = Math.ceil(Math.max(...site.holes.map((h) => h.depth ?? 0)));

  const grid: { path: P3[] }[] = [];
  for (let x = Math.ceil(x0 / GRID_STEP) * GRID_STEP; x <= x1; x += GRID_STEP) {
    grid.push({ path: [[x, y0, 0], [x, y1, 0]] });
  }
  for (let y = Math.ceil(y0 / GRID_STEP) * GRID_STEP; y <= y1; y += GRID_STEP) {
    grid.push({ path: [[x0, y, 0], [x1, y, 0]] });
  }

  const ruler: { path: P3[] }[] = [{ path: [[x0, y0, 0], [x0, y0, -maxDepth * exag]] }];
  const rulerLabels: { position: P3; text: string }[] = [];
  for (let d = 0; d <= maxDepth; d += 2) {
    ruler.push({ path: [[x0, y0, -d * exag], [x0 + 0.8, y0, -d * exag]] });
    rulerLabels.push({ position: [x0 - 0.4, y0, -d * exag], text: `${d} m` });
  }

  const dark = isDark();
  const ink: RGBA = dark ? [236, 232, 225, 255] : [31, 29, 26, 255];
  const muted: RGBA = dark ? [156, 150, 140, 255] : [107, 102, 94, 255];

  const common = { coordinateSystem: COORDINATE_SYSTEM.CARTESIAN };
  const z = (h: Hole, depth: number) => (h.ground - depth) * exag;

  deck.setProps({
    layers: [
      new ColumnLayer<Slice>({
        ...common,
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
        getFillColor: (s) => zoneRgba[String(s.zone)],
        updateTriggers: { getPosition: exag, getElevation: exag },
      }),
      new ColumnLayer<Hole>({
        ...common,
        id: "nzgd",
        data: nzgd,
        visible: state.showNzgd,
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
        ...common,
        id: "water",
        data: osu.filter((h) => h.gw !== null),
        visible: state.showWater,
        diskResolution: 20,
        radius: COLUMN_RADIUS * 1.9,
        extruded: true,
        pickable: true,
        getPosition: (h) => [h.x, h.y, z(h, h.gw ?? 0) - 0.03],
        getElevation: 0.06,
        getFillColor: WATER_RGBA,
        updateTriggers: { getPosition: exag },
      }),
      new SolidPolygonLayer({
        ...common,
        id: "ground",
        data: [{ polygon: [[x0, y0, 0], [x1, y0, 0], [x1, y1, 0], [x0, y1, 0]] }],
        getPolygon: (d: { polygon: P3[] }) => d.polygon,
        getFillColor: dark ? [90, 80, 64, 70] : [140, 120, 90, 45],
        // Translucent: don't write depth, so columns below still show through.
        parameters: { depthWriteEnabled: false },
      }),
      new PathLayer<{ path: P3[] }>({
        ...common,
        id: "grid",
        data: grid,
        getPath: (d) => d.path,
        getColor: dark ? [255, 255, 255, 40] : [60, 50, 40, 50],
        getWidth: 1,
        widthUnits: "pixels",
      }),
      new PathLayer<{ path: P3[] }>({
        ...common,
        id: "ruler",
        data: ruler,
        getPath: (d) => d.path,
        getColor: muted,
        getWidth: 1.5,
        widthUnits: "pixels",
        updateTriggers: { getPath: exag },
      }),
      new TextLayer<{ position: P3; text: string }>({
        ...common,
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
        ...common,
        id: "labels",
        data: site.holes.filter((h) => h.source === "osu" || state.showNzgd),
        getPosition: (h) => [h.x, h.y, h.ground * exag + 0.6],
        getText: (h) => h.id.replace(/^OSU /, ""),
        getSize: 11,
        getColor: (h) => (h.source === "osu" ? ink : muted),
        getAlignmentBaseline: "bottom",
        fontFamily: "system-ui, sans-serif",
        updateTriggers: { getPosition: exag },
      }),
    ],
  });
}

function selectSite(id: string, moveCamera = true): void {
  const site = state.data?.sites.find((s) => s.id === id) ?? state.data?.sites[0];
  if (!site) return;
  state.site = site;
  document.getElementById("site-caption")!.textContent = site.caption;
  document.querySelectorAll<HTMLButtonElement>("#site-buttons button").forEach((b) => {
    b.setAttribute("aria-selected", String(b.dataset.site === site.id));
  });
  if (location.hash !== `#${site.id}`) history.replaceState(null, "", `#${site.id}`);
  render();
  if (moveCamera) deck.setProps({ initialViewState: viewFor(site) });
}

function buildPanel(data: Data): void {
  const buttons = document.getElementById("site-buttons")!;
  for (const s of data.sites) {
    const b = document.createElement("button");
    b.textContent = s.name.replace(" Intermediate School", "");
    b.dataset.site = s.id;
    b.setAttribute("role", "tab");
    b.onclick = () => selectSite(s.id);
    buttons.append(b);
  }

  const legend = document.getElementById("legend")!;
  legend.innerHTML =
    Object.values(data.zones)
      .map((z) => `<li><span class="swatch" style="background:${z.colour}"></span>${z.label}</li>`)
      .join("") +
    `<li><span class="swatch water"></span>Groundwater (from CPT)</li>` +
    `<li><span class="swatch nzgd"></span>NZGD investigation (outline only)</li>`;

  const exag = document.getElementById("exag") as HTMLInputElement;
  const exagOut = document.getElementById("exag-value")!;
  exag.oninput = () => {
    state.exag = Number(exag.value);
    exagOut.textContent = `${state.exag}×`;
    render();
  };
  exag.onchange = () => state.site && deck.setProps({ initialViewState: viewFor(state.site) });

  const water = document.getElementById("show-water") as HTMLInputElement;
  water.onchange = () => { state.showWater = water.checked; render(); };
  const nzgd = document.getElementById("show-nzgd") as HTMLInputElement;
  nzgd.onchange = () => { state.showNzgd = nzgd.checked; render(); };
}

async function main(): Promise<void> {
  const res = await fetch(`${import.meta.env.BASE_URL}data/osu-sites.json`);
  if (!res.ok) throw new Error(`Couldn't load site data (${res.status})`);
  state.data = (await res.json()) as Data;
  buildPanel(state.data);
  selectSite(location.hash.slice(1));
  window.addEventListener("hashchange", () => selectSite(location.hash.slice(1)));
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", render);
}

main().catch((err) => {
  document.getElementById("site-caption")!.textContent = String(err);
});
