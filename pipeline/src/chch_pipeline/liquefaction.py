"""Simplified CPT liquefaction triggering (Robertson & Wride 1998 / Robertson 2009).

This is a *screening* calculation for a portfolio visualisation, not a design check.
Assumptions are recorded in docs/decisions.md D-005; the main ones:

- qt ≈ qc (the cone's area ratio isn't in the OSU files).
- Unit weight from the Robertson & Cabal (2010) CPT correlation, clamped to 14–22 kN/m³.
- Hydrostatic pore pressure below the CPT-derived groundwater depth.
- No K_sigma or K_alpha corrections; no thin-layer correction.

The output separates what depends on the soil from what depends on the earthquake:

    FS = crr_m / (csr_per_g × PGA)

- crr_m      : cyclic resistance ratio for Mw 7.5, multiplied by the magnitude scaling
               factor for the chosen Mw. NaN where the soil isn't liquefiable
               (above groundwater, clay-like with Ic > 2.6, or too dense).
- csr_per_g  : 0.65 × (σv / σ'v) × rd, i.e. the cyclic stress ratio per 1 g of PGA.

so the viewer can recompute FS for any PGA without redoing the soil calculation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

PA_KPA = 101.325  # atmospheric pressure, kPa
GAMMA_W = 9.81  # unit weight of water, kN/m³
DEFAULT_GAMMA = 18.0  # kN/m³, where the correlation is undefined
IC_CLAY_LIKE = 2.6  # above this, treat as clay-like: not susceptible to liquefaction
QTN_CS_MAX = 160  # Robertson & Wride CRR is valid below this; denser soil won't liquefy


def unit_weight(qt_kpa: np.ndarray, fs_kpa: np.ndarray) -> np.ndarray:
    """Robertson & Cabal (2010): γ/γw = 0.27 log Rf + 0.36 log(qt/pa) + 1.236 (Rf in %)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        rf = fs_kpa / qt_kpa * 100
        gamma = GAMMA_W * (0.27 * np.log10(rf) + 0.36 * np.log10(qt_kpa / PA_KPA) + 1.236)
    gamma = np.where(np.isfinite(gamma), gamma, DEFAULT_GAMMA)
    return np.clip(gamma, 14.0, 22.0)


def stress_reduction(depth: np.ndarray) -> np.ndarray:
    """rd from Liao & Whitman (1986), as recommended by Youd et al. (2001)."""
    return np.where(depth <= 9.15, 1.0 - 0.00765 * depth, 1.174 - 0.0267 * depth)


def magnitude_scaling(mw: float) -> float:
    """MSF = 10^2.24 / Mw^2.56 (Idriss, in Youd et al. 2001). About 1 at Mw 7.5."""
    return 10**2.24 / mw**2.56


def kc(ic: np.ndarray) -> np.ndarray:
    """Robertson & Wride (1998) fines correction factor."""
    with np.errstate(invalid="ignore"):  # NaN Ic (no data) stays NaN
        poly = -0.403 * ic**4 + 5.581 * ic**3 - 21.63 * ic**2 + 33.75 * ic - 17.88
    return np.where(ic <= 1.64, 1.0, poly)


def crr75(qtn_cs: np.ndarray) -> np.ndarray:
    """Cyclic resistance ratio for Mw 7.5 (Robertson & Wride 1998)."""
    q = qtn_cs / 1000
    return np.where(qtn_cs < 50, 0.833 * q + 0.05, 93 * q**3 + 0.08)


def normalised(qt_kpa, fs_kpa, sv, sv_eff, iterations: int = 20):
    """Iterate Robertson (2009) Qtn, F and Ic with the stress exponent n."""
    with np.errstate(divide="ignore", invalid="ignore"):
        net = qt_kpa - sv
        f = fs_kpa / net * 100
        n = np.ones_like(qt_kpa)
        for _ in range(iterations):
            qtn = (net / PA_KPA) * (PA_KPA / sv_eff) ** n
            ic = np.sqrt((3.47 - np.log10(qtn)) ** 2 + (np.log10(f) + 1.22) ** 2)
            n = np.minimum(0.381 * ic + 0.05 * (sv_eff / PA_KPA) - 0.15, 1.0)
    return qtn, f, ic


def triggering(cpt: pd.DataFrame, gw_depth: float, mw: float = 6.2) -> pd.DataFrame:
    """Per-reading liquefaction terms for a clean CPT table (from cpt.read_osu_cpt).

    Returns the input's depth plus: gamma (kN/m³), sv, sv_eff (kPa), ic, qtn_cs,
    crr_m and csr_per_g (see the module docstring). Default Mw 6.2 is the
    22 February 2011 Christchurch earthquake.
    """
    depth = cpt["depth"].to_numpy(dtype=float)
    qt = cpt["qc"].to_numpy(dtype=float) * 1000  # MPa -> kPa (qt ≈ qc)
    fs = cpt["fs"].to_numpy(dtype=float) * 1000
    in_soil = cpt["in_soil"].to_numpy(dtype=bool)

    gamma = unit_weight(qt, fs)
    dz = np.diff(depth, prepend=0.0)
    sv = np.cumsum(gamma * dz)
    u0 = GAMMA_W * np.clip(depth - gw_depth, 0, None)
    sv_eff = sv - u0

    qtn, _, ic = normalised(qt, fs, sv, sv_eff)
    qtn_cs = kc(ic) * qtn

    liquefiable = (
        in_soil
        & (depth > gw_depth)
        & np.isfinite(ic)
        & (ic <= IC_CLAY_LIKE)
        & np.isfinite(qtn_cs)
        & (qtn_cs > 0)
        & (qtn_cs < QTN_CS_MAX)
    )
    crr_m = np.where(liquefiable, crr75(qtn_cs) * magnitude_scaling(mw), np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        csr_per_g = 0.65 * (sv / sv_eff) * stress_reduction(depth)

    return pd.DataFrame(
        {
            "depth": depth,
            "gamma": gamma,
            "sv": sv,
            "sv_eff": sv_eff,
            "ic": ic,
            "qtn_cs": qtn_cs,
            "crr_m": crr_m,
            "csr_per_g": csr_per_g,
        }
    )


def factor_of_safety(liq: pd.DataFrame, pga: float) -> pd.Series:
    """FS = crr_m / (csr_per_g × PGA). NaN where not liquefiable."""
    return liq["crr_m"] / (liq["csr_per_g"] * pga)


def lpi(liq: pd.DataFrame, pga: float) -> float:
    """Liquefaction potential index (Iwasaki et al. 1978) over the top 20 m.

    LPI = ∫ F(z) w(z) dz, with F = 1 − FS where FS < 1, and w = 10 − 0.5 z.
    Rough guide: 0 very low, 0–5 low, 5–15 high, over 15 very high.
    """
    fs = factor_of_safety(liq, pga).to_numpy()
    z = liq["depth"].to_numpy()
    f = np.where(np.isfinite(fs) & (fs < 1), 1 - fs, 0.0)
    w = np.clip(10 - 0.5 * z, 0, None)
    dz = np.diff(z, prepend=0.0)
    return float(np.sum(f * w * dz))
