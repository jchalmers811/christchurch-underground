// deck.gl layers for the city view: every ECan well with a known depth, hanging below a
// light OpenStreetMap image of Christchurch, plus markers for the four OSU sites.

import { COORDINATE_SYSTEM, type Layer } from "@deck.gl/core";
import { BitmapLayer, ColumnLayer, TextLayer } from "@deck.gl/layers";
import type { Basemap, CityData, P3, RGBA, WellRow } from "./types";

export interface CityOptions {
  exag: number;
  onlyLogged: boolean;
  dark: boolean;
}

export const DEPTH_BANDS: { max: number; label: string; rgba: RGBA; css: string }[] = [
  { max: 10, label: "under 10 m", rgba: [168, 219, 208, 255], css: "#a8dbd0" },
  { max: 30, label: "10–30 m", rgba: [79, 163, 165, 255], css: "#4fa3a5" },
  { max: 100, label: "30–100 m", rgba: [43, 111, 138, 255], css: "#2b6f8a" },
  { max: Infinity, label: "100 m or more", rgba: [27, 58, 92, 255], css: "#1b3a5c" },
];
const depthRgba = (d: number) => DEPTH_BANDS.find((b) => d < b.max)!.rgba;
const SITE_RGBA: RGBA = [194, 86, 44, 255];
const CARTESIAN = { coordinateSystem: COORDINATE_SYSTEM.CARTESIAN };

export function cityLayers(city: CityData, basemap: Basemap | null, basemapUrl: string, opts: CityOptions): Layer[] {
  const { exag } = opts;
  const wells = opts.onlyLogged ? city.wells.filter((w) => w[3] > 0) : city.wells;
  const [ox, oy] = city.origin;
  const ink: RGBA = opts.dark ? [236, 232, 225, 255] : [31, 29, 26, 255];

  const layers: Layer[] = [
    new ColumnLayer<WellRow>({
      ...CARTESIAN,
      id: "wells",
      data: wells,
      diskResolution: 6,
      radius: 32,
      extruded: true,
      pickable: true,
      autoHighlight: true,
      highlightColor: [255, 255, 255, 120],
      getPosition: (w) => [w[0], w[1], -w[2] * exag],
      getElevation: (w) => w[2] * exag,
      getFillColor: (w) => depthRgba(w[2]),
      updateTriggers: { getPosition: exag, getElevation: exag },
    }),
    new ColumnLayer<CityData["sites"][number]>({
      ...CARTESIAN,
      id: "city-sites",
      data: city.sites,
      diskResolution: 16,
      radius: 90,
      extruded: true,
      pickable: true,
      getPosition: (s) => [s.x, s.y, -20 * exag],
      getElevation: 20 * exag + 120,
      getFillColor: SITE_RGBA,
      updateTriggers: { getPosition: exag, getElevation: exag },
    }),
    new TextLayer<CityData["sites"][number]>({
      ...CARTESIAN,
      id: "city-site-labels",
      data: city.sites,
      getPosition: (s): P3 => [s.x, s.y, 160],
      getText: (s) => s.name.replace(" Intermediate School", ""),
      getSize: 13,
      getColor: ink,
      fontWeight: 600,
      fontFamily: "system-ui, sans-serif",
      getAlignmentBaseline: "bottom",
      background: true,
      getBackgroundColor: opts.dark ? [30, 28, 25, 220] : [255, 255, 255, 220],
      backgroundPadding: [4, 2],
      updateTriggers: { getColor: opts.dark },
    }),
  ];

  if (basemap) {
    const corners = basemap.corners_nztm.map(([e, n]) => [e - ox, n - oy, 0]) as P3[];
    layers.unshift(
      new BitmapLayer({
        ...CARTESIAN,
        id: "basemap",
        image: basemapUrl,
        bounds: corners as unknown as [P3, P3, P3, P3],
        opacity: opts.dark ? 0.7 : 0.9,
        // Drawn first and without depth testing, so the wells (drawn after it) always
        // show on top: an X-ray view through the ground rather than a lid over them.
        parameters: { depthWriteEnabled: false, depthCompare: "always" },
      }),
    );
  }
  return layers;
}
