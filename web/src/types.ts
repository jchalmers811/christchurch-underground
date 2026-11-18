// Shapes of the JSON files written by `python -m chch_pipeline.export_web`.

export type Interval = [top: number, bottom: number, zone: number];
export type P3 = [number, number, number];
export type RGBA = [number, number, number, number];

export interface Hole {
  id: string;
  source: "osu" | "nzgd";
  kind: string;
  x: number;
  y: number;
  /** Distance along the line's main axis (m), for the fence diagram. */
  s: number;
  ground: number;
  depth: number | null;
  gw: number | null;
  date: string;
  intervals?: Interval[];
}

export interface Site {
  id: string;
  name: string;
  caption: string;
  origin: [number, number];
  axis: [number, number];
  holes: Hole[];
}

export interface SitesData {
  zones: Record<string, { label: string; colour: string }>;
  liquefaction: { mw: number; default_pga: number };
  sites: Site[];
}

/** [depth, qc, fs, u2, isbt, crr_m, csr_per_g]; nulls where undefined. */
export type DetailRow = [number, number | null, number | null, number | null, number | null, number | null, number | null];

export interface SiteDetail {
  id: string;
  mw: number;
  holes: Record<string, DetailRow[]>;
}

/** [x, y, depth, strata, well_no, year] */
export type WellRow = [number, number, number, number, string, number | null];

export interface CityData {
  origin: [number, number];
  bbox: [number, number, number, number];
  wells: WellRow[];
  sites: { id: string; name: string; x: number; y: number }[];
}

export interface Basemap {
  image: string;
  corners_nztm: [number, number][];
  attribution: string;
}

/** One coloured piece of a CPT column (or fence panel). */
export interface Slice {
  hole: Hole;
  top: number;
  bottom: number;
  rgba: RGBA;
  label: string;
}
