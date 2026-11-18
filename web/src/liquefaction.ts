// Turns the pipeline's liquefaction terms into factors of safety for a chosen PGA.
// The soil-side calculation lives in pipeline/src/chch_pipeline/liquefaction.py
// (tested there); here it's only FS = crr_m / (csr_per_g × PGA).

import type { DetailRow, RGBA } from "./types";

export interface FsClass {
  key: string;
  label: string;
  colour: string;
  rgba: RGBA;
}

const cls = (key: string, label: string, colour: string): FsClass => ({
  key,
  label,
  colour,
  rgba: [parseInt(colour.slice(1, 3), 16), parseInt(colour.slice(3, 5), 16), parseInt(colour.slice(5, 7), 16), 255],
});

export const FS_CLASSES = {
  liquefies: cls("liquefies", "Liquefies (FS < 1)", "#d7301f"),
  marginal: cls("marginal", "Marginal (FS 1–1.25)", "#f4a259"),
  safe: cls("safe", "Resists (FS ≥ 1.25)", "#8fc1a0"),
  na: cls("na", "Not susceptible (above water, clay-like or dense)", "#cfcac2"),
} as const;

export function factorOfSafety(row: DetailRow, pga: number): number | null {
  const crr = row[5];
  const csr = row[6];
  if (crr === null || csr === null || csr <= 0) return null;
  return crr / (csr * pga);
}

export function fsClass(fs: number | null): FsClass {
  if (fs === null) return FS_CLASSES.na;
  if (fs < 1) return FS_CLASSES.liquefies;
  if (fs < 1.25) return FS_CLASSES.marginal;
  return FS_CLASSES.safe;
}

/** Liquefaction potential index (Iwasaki et al. 1978) over the top 20 m. */
export function lpi(rows: DetailRow[], pga: number): number {
  let total = 0;
  let prev = 0;
  for (const row of rows) {
    const z = row[0];
    const fs = factorOfSafety(row, pga);
    if (fs !== null && fs < 1 && z <= 20) total += (1 - fs) * (10 - 0.5 * z) * (z - prev);
    prev = z;
  }
  return total;
}

export function lpiLabel(v: number): string {
  if (v === 0) return "very low";
  if (v < 5) return "low";
  if (v < 15) return "high";
  return "very high";
}
