// 3D viewer for Christchurch Underground. Data comes from
// `python -m chch_pipeline.export_web` (and `chch_pipeline.basemap` for the city image).
//
// Two scenes, both in a local Cartesian frame in metres (x = east, y = north from
// NZTM2000, z = up; depths below ground are negative z times the vertical exaggeration):
// - Sites: one OSU CPT line as columns or a fence, coloured by soil type or liquefaction.
// - City: every ECan well with a known depth, hanging below a map of Christchurch.

import { Deck, LinearInterpolator, OrbitView, type OrbitViewState, type PickingInfo } from "@deck.gl/core";
import { cityLayers, DEPTH_BANDS } from "./city-layers";
import { FS_CLASSES, lpi, lpiLabel } from "./liquefaction";
import { buildSlices, siteLayers, type ColourBy, type Shape } from "./site-layers";
import { traceChart } from "./trace-chart";
import type { Basemap, CityData, Hole, Site, SiteDetail, SitesData, Slice, WellRow } from "./types";

type Mode = "sites" | "city";

const BASE = import.meta.env.BASE_URL;
const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;

const state = {
  mode: "sites" as Mode,
  data: null as SitesData | null,
  site: null as Site | null,
  details: new Map<string, SiteDetail>(),
  city: null as CityData | null,
  basemap: null as Basemap | null,
  siteExag: 1,
  cityExag: 10,
  shape: "columns" as Shape,
  colourBy: "soil" as ColourBy,
  pga: 0.35,
  showWater: true,
  showNzgd: true,
  onlyLogged: false,
  traceHole: null as Hole | null,
  touring: false,
  view: null as OrbitViewState | null,
};

const dark = () => window.matchMedia("(prefers-color-scheme: dark)").matches;

// --- Deck ------------------------------------------------------------------------------------

const deck = new Deck<OrbitView>({
  parent: $<HTMLDivElement>("viewer"),
  views: new OrbitView({ orbitAxis: "Z", fovy: 35, far: 10000 }),
  controller: true,
  initialViewState: { target: [0, 0, 0], zoom: 3, rotationX: 25, rotationOrbit: -35 },
  onViewStateChange: ({ viewState }) => {
    state.view = viewState as OrbitViewState;
  },
  onInteractionStateChange: (s) => {
    if (s.isDragging || s.isZooming || s.isPanning || s.isRotating) stopTour();
  },
  getTooltip,
  onClick,
});

function setView(view: Partial<OrbitViewState> & Record<string, unknown>): void {
  deck.setProps({ initialViewState: view as OrbitViewState });
}

function getTooltip({ object, layer }: PickingInfo): { html: string } | null {
  if (!object) return null;
  switch (layer?.id) {
    case "cpt":
    case "cpt-fence": {
      const s = object as Slice;
      return { html: `<strong>${s.hole.id}</strong><br>${s.top.toFixed(2)}–${s.bottom.toFixed(2)} m · ${s.label}<br><em>Click for the full trace</em>` };
    }
    case "nzgd": {
      const h = object as Hole;
      return { html: `<strong>${h.id}</strong> · ${h.kind} · ${h.depth ?? "?"} m<br>Held in the NZGD, not available here` };
    }
    case "water": {
      const h = object as Hole;
      return { html: `<strong>${h.id}</strong><br>Groundwater at ${h.gw} m (from CPT)` };
    }
    case "wells": {
      const [, , depth, strata, no, year] = object as WellRow;
      return {
        html: `<strong>${no}</strong> · ECan well<br>${depth} m deep${year ? ` · drilled ${year}` : ""}<br>${strata > 0 ? `Soil log: ${strata} layers` : "No soil log"}`,
      };
    }
    case "city-sites": {
      const s = object as CityData["sites"][number];
      return { html: `<strong>${s.name}</strong><br>OSU CPT line · click to open` };
    }
  }
  return null;
}

function onClick({ object, layer }: PickingInfo): void {
  if (!object) return;
  if (layer?.id?.startsWith("cpt")) void openTrace((object as Slice).hole);
  if (layer?.id === "city-sites") selectSite((object as CityData["sites"][number]).id);
  if (layer?.id === "wells") {
    const no = (object as WellRow)[4];
    window.open(`https://www.ecan.govt.nz/data/well-search/welldetails/?WellNo=${encodeURIComponent(no)}`, "_blank", "noopener");
  }
}

// --- Rendering -------------------------------------------------------------------------------

function render(): void {
  const { data, site } = state;
  if (state.mode === "city") {
    if (!state.city) return;
    deck.setProps({
      layers: cityLayers(state.city, state.basemap, `${BASE}data/${state.basemap?.image ?? ""}`, {
        exag: state.cityExag,
        onlyLogged: state.onlyLogged,
        dark: dark(),
      }),
    });
    return;
  }
  if (!data || !site) return;
  const opts = {
    exag: state.siteExag,
    colourBy: state.colourBy,
    shape: state.shape,
    pga: state.pga,
    showWater: state.showWater,
    showNzgd: state.showNzgd,
    dark: dark(),
  };
  const detail = state.details.get(site.id) ?? null;
  deck.setProps({ layers: siteLayers(site, buildSlices(site, data, detail, opts), opts) });
  updateLiquefactionSummary();
  if (state.traceHole) void openTrace(state.traceHole);
}

/** Fit the camera to a site: centred on the middle of the columns, sized to the canvas. */
function siteView(site: Site): OrbitViewState {
  const xs = site.holes.map((h) => h.x);
  const ys = site.holes.map((h) => h.y);
  const maxDepth = Math.max(...site.holes.map((h) => h.depth ?? 0));
  const extent = Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys), maxDepth * state.siteExag) + 8;
  const viewer = $("viewer");
  const px = Math.min(viewer.clientWidth, viewer.clientHeight);
  return {
    target: [0, 0, (-maxDepth * state.siteExag) / 2],
    zoom: Math.log2((px * 0.75) / extent),
    rotationX: 25,
    rotationOrbit: -35,
    transitionDuration: 600,
  } as OrbitViewState;
}

function cityView(): OrbitViewState {
  const [x0, x1, y0, y1] = state.city!.bbox;
  const viewer = $("viewer");
  const px = Math.min(viewer.clientWidth, viewer.clientHeight);
  return {
    target: [(x0 + x1) / 2, (y0 + y1) / 2, -60 * state.cityExag],
    zoom: Math.log2((px * 0.95) / Math.max(x1 - x0, y1 - y0)),
    rotationX: 32,
    rotationOrbit: -20,
    transitionDuration: 800,
  } as OrbitViewState;
}

// --- Data loading ----------------------------------------------------------------------------

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}data/${path}`);
  if (!res.ok) throw new Error(`Couldn't load ${path} (${res.status})`);
  return (await res.json()) as T;
}

async function ensureDetail(site: Site): Promise<SiteDetail> {
  let d = state.details.get(site.id);
  if (!d) {
    d = await getJson<SiteDetail>(`sites/${site.id}.json`);
    state.details.set(site.id, d);
  }
  return d;
}

async function ensureCity(): Promise<void> {
  if (state.city) return;
  const [city, basemap] = await Promise.all([
    getJson<CityData>("city-wells.json"),
    getJson<Basemap>("city-basemap.json").catch(() => null),
  ]);
  state.city = city;
  state.basemap = basemap;
  $("city-count").textContent = city.wells.length.toLocaleString();
}

// --- Liquefaction summary and trace card -----------------------------------------------------

const SITE_NOTES: Record<string, string> = {
  meadows:
    "Meadows didn't liquefy in 2011, yet this method predicts liquefaction in its looser sands below about 5 m. " +
    "Those sands sit under a 2.5–5 m clay layer, which likely kept them from reaching the surface. " +
    "Simplified methods and LPI don't account for a capping layer like that, so they over-predict here.",
};

function updateLiquefactionSummary(): void {
  const el = $("liq-summary");
  const site = state.site;
  const detail = site && state.details.get(site.id);
  if (state.colourBy !== "liquefaction" || !site || !detail) {
    el.innerHTML = "";
    return;
  }
  const values = Object.values(detail.holes).map((rows) => lpi(rows, state.pga)).sort((a, b) => a - b);
  const median = values[Math.floor(values.length / 2)];
  el.innerHTML =
    `<p>Median LPI across ${values.length} CPTs: <strong>${median.toFixed(1)}</strong> (${lpiLabel(median)}); ` +
    `range ${values[0].toFixed(1)}–${values[values.length - 1].toFixed(1)}.</p>` +
    (SITE_NOTES[site.id] ? `<p class="note">${SITE_NOTES[site.id]}</p>` : "");
}

async function openTrace(hole: Hole): Promise<void> {
  const site = state.site;
  if (!site || !state.data) return;
  state.traceHole = hole;
  const card = $("trace");
  card.hidden = false;
  const detail = await ensureDetail(site);
  card.innerHTML = traceChart(hole, detail.holes[hole.id] ?? [], state.data, state.pga);
  card.querySelector<HTMLButtonElement>(".close")!.onclick = closeTrace;
}

function closeTrace(): void {
  state.traceHole = null;
  $("trace").hidden = true;
}

// --- Mode and site selection -----------------------------------------------------------------

async function setMode(mode: Mode, moveCamera = true): Promise<void> {
  state.mode = mode;
  document.body.dataset.mode = mode;
  document.querySelectorAll<HTMLButtonElement>("#mode-tabs button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.mode === mode)));
  closeTrace();
  if (mode === "city") {
    await ensureCity();
    if (location.hash !== "#city") history.replaceState(null, "", "#city");
    render();
    if (moveCamera) setView(cityView());
  } else {
    selectSite(state.site?.id ?? "", moveCamera);
  }
}

function selectSite(id: string, moveCamera = true): void {
  const site = state.data?.sites.find((s) => s.id === id) ?? state.data?.sites[0];
  if (!site) return;
  if (state.mode !== "sites") {
    state.mode = "sites";
    document.body.dataset.mode = "sites";
    document.querySelectorAll<HTMLButtonElement>("#mode-tabs button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.mode === "sites")));
  }
  if (state.site?.id !== site.id) closeTrace();
  state.site = site;
  $("site-caption").textContent = site.caption;
  document.querySelectorAll<HTMLButtonElement>("#site-buttons button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.site === site.id)));
  if (location.hash !== `#${site.id}`) history.replaceState(null, "", `#${site.id}`);
  render();
  if (state.colourBy === "liquefaction") void ensureDetail(site).then(render);
  if (moveCamera) setView(siteView(site));
}

// --- Tour --------------------------------------------------------------------------------------

const ORBIT = new LinearInterpolator({ transitionProps: ["rotationOrbit"] });

function tourStep(): void {
  if (!state.touring || !state.view) return;
  setView({
    ...state.view,
    rotationOrbit: (state.view.rotationOrbit ?? 0) + 360,
    transitionDuration: state.mode === "city" ? 30000 : 18000,
    transitionInterpolator: ORBIT,
    onTransitionEnd: () => {
      if (!state.touring) return;
      if (state.mode === "sites" && state.data && state.site) {
        // Move on to the next site, then keep turning.
        const sites = state.data.sites;
        const next = sites[(sites.indexOf(state.site) + 1) % sites.length];
        selectSite(next.id);
        setTimeout(tourStep, 900);
      } else {
        tourStep();
      }
    },
  });
}

function startTour(): void {
  state.touring = true;
  $("tour").textContent = "■ Stop tour";
  tourStep();
}

function stopTour(): void {
  if (!state.touring) return;
  state.touring = false;
  $("tour").textContent = "▶ Tour";
  if (state.view) setView({ ...state.view, transitionDuration: 0 });
}

// --- Panel -------------------------------------------------------------------------------------

function segmented(id: string, onChange: (value: string) => void): void {
  const group = $(id);
  group.querySelectorAll<HTMLButtonElement>("button").forEach((b) => {
    b.onclick = () => {
      group.querySelectorAll("button").forEach((o) => o.setAttribute("aria-pressed", String(o === b)));
      onChange(b.dataset.value!);
    };
  });
}

function buildLegends(data: SitesData): void {
  $("legend-soil").innerHTML = Object.values(data.zones)
    .map((z) => `<li><span class="swatch" style="background:${z.colour}"></span>${z.label}</li>`)
    .join("");
  $("legend-liq").innerHTML = Object.values(FS_CLASSES)
    .map((c) => `<li><span class="swatch" style="background:${c.colour}"></span>${c.label}</li>`)
    .join("");
  $("legend-depth").innerHTML = DEPTH_BANDS.map((b) => `<li><span class="swatch round" style="background:${b.css}"></span>${b.label}</li>`).join("");
}

function buildPanel(data: SitesData): void {
  const buttons = $("site-buttons");
  for (const s of data.sites) {
    const b = document.createElement("button");
    b.textContent = s.name.replace(" Intermediate School", "");
    b.dataset.site = s.id;
    b.onclick = () => selectSite(s.id);
    buttons.append(b);
  }
  buildLegends(data);

  document.querySelectorAll<HTMLButtonElement>("#mode-tabs button").forEach((b) => {
    b.onclick = () => void setMode(b.dataset.mode as Mode);
  });

  segmented("shape", (v) => {
    state.shape = v as Shape;
    render();
  });
  segmented("colour-by", (v) => {
    state.colourBy = v as ColourBy;
    document.body.dataset.colour = v;
    if (v === "liquefaction" && state.site) void ensureDetail(state.site).then(render);
    render();
  });

  const pga = $<HTMLInputElement>("pga");
  pga.value = String(data.liquefaction.default_pga);
  state.pga = data.liquefaction.default_pga;
  $("pga-value").textContent = `${state.pga} g`;
  $("mw").textContent = String(data.liquefaction.mw);
  pga.oninput = () => {
    state.pga = Number(pga.value);
    $("pga-value").textContent = `${state.pga} g`;
    render();
  };

  const exag = $<HTMLInputElement>("exag");
  const exagOut = $("exag-value");
  const syncExag = () => {
    const v = state.mode === "city" ? state.cityExag : state.siteExag;
    exag.min = state.mode === "city" ? "1" : "1";
    exag.max = state.mode === "city" ? "30" : "5";
    exag.step = state.mode === "city" ? "1" : "0.5";
    exag.value = String(v);
    exagOut.textContent = `${v}×`;
  };
  exag.oninput = () => {
    if (state.mode === "city") state.cityExag = Number(exag.value);
    else state.siteExag = Number(exag.value);
    exagOut.textContent = `${exag.value}×`;
    render();
  };
  exag.onchange = () => setView(state.mode === "city" ? cityView() : siteView(state.site!));
  new MutationObserver(syncExag).observe(document.body, { attributes: true, attributeFilter: ["data-mode"] });
  syncExag();

  const water = $<HTMLInputElement>("show-water");
  water.onchange = () => {
    state.showWater = water.checked;
    render();
  };
  const nzgd = $<HTMLInputElement>("show-nzgd");
  nzgd.onchange = () => {
    state.showNzgd = nzgd.checked;
    render();
  };
  const logged = $<HTMLInputElement>("only-logged");
  logged.onchange = () => {
    state.onlyLogged = logged.checked;
    render();
  };

  $("tour").onclick = () => (state.touring ? stopTour() : startTour());
}

// --- Start -------------------------------------------------------------------------------------

function route(): void {
  const hash = location.hash.slice(1);
  if (hash === "city") void setMode("city");
  else selectSite(hash);
}

async function main(): Promise<void> {
  state.data = await getJson<SitesData>("osu-sites.json");
  buildPanel(state.data);
  document.body.dataset.mode = "sites";
  document.body.dataset.colour = "soil";
  route();
  window.addEventListener("hashchange", route);
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", render);

  // Small hook for scripted screenshots (the README GIF): set the camera directly.
  (window as unknown as { chch: unknown }).chch = {
    setView: (v: Partial<OrbitViewState>) => setView({ ...(state.view ?? {}), ...v, transitionDuration: 0 }),
    view: () => state.view,
  };
}

main().catch((err) => {
  $("site-caption").textContent = String(err);
});
