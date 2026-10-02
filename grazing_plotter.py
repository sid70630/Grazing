"""
GRAZING plot maker.

This script reads the CSV files produced by grazing_builder.py and makes plots for one YAML case.

Usage:
----------
    python3 grazing_plotter.py run-case --config <case>.yaml

Example:
    python3 grazing_plotter.py run-case --config xe_pt_195Os.yaml

Should save following
-------------
<case_name>_tlf_map.png
    Post-evaporation target-like-fragment map in the Z-N plane.
<case_name>_<element>_overlay.png
    Post-evaporation isotope-chain cross-section plot.
<case_name>_reconstructed.png
    Recoil-property plots.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle
import yaml

ELEMENT_Z = {
    "Hf": 72, "W": 74, "Ta": 73, "Os": 76, "Re": 75,
    "Pt": 78, "Ir": 77, "Xe": 54, "Au": 79, "Hg": 80,
    "Ba": 56,
}


def load_cfg(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def get_weight_col(df: pd.DataFrame) -> str:
    for c in ["weight_natw", "weight", "weight_combined", "weight_hdr_edist", "weight_dsiglab"]:
        if c in df.columns:
            return c
    raise RuntimeError("No known weight column found.")


def znmap_from_csv(input_csv: Path, out_prefix: Path, highlights: list[str], zmin=None, zmax=None, nmin=None, nmax=None) -> None:
    df = pd.read_csv(input_csv)
    df = df[np.isfinite(df["Z"]) & np.isfinite(df["N"]) & np.isfinite(df["sigma_weighted_mb"])]
    df = df[df["sigma_weighted_mb"] > 0].copy()
    df["Z"] = df["Z"].astype(int)
    df["N"] = df["N"].astype(int)

    bounds = [1e-7, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1, 10, 100, 1000, 10000]
    colors = ["#0b0080", "#0010ff", "#1fa3dc", "#39e0c0", "#72e66a", "#c8f51a", "#ffc800", "#ff7a00", "#ff1400", "#c00000", "#a00000"]

    def pick_color(val):
        for i in range(len(bounds) - 1):
            if bounds[i] <= val < bounds[i + 1]:
                return colors[i]
        if val >= bounds[-1]:
            return colors[-1]
        return None

    fig, ax = plt.subplots(figsize=(11, 8), dpi=180)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # This makes one square per populated isotope cell.
    for _, r in df.iterrows():
        z = int(r["Z"])
        n = int(r["N"])
        s = float(r["sigma_weighted_mb"])
        c = pick_color(s)
        if c is None:
            continue
        ax.add_patch(Rectangle((n - 0.5, z - 0.5), 1, 1, facecolor=c, edgecolor="black", linewidth=0.35))

    # Highlighting isotopes of interest from the YAML.
    for iso in highlights or []:
        A = int("".join(ch for ch in iso if ch.isdigit()))
        sym = "".join(ch for ch in iso if ch.isalpha())
        if sym not in ELEMENT_Z:
            continue
        z = ELEMENT_Z[sym]
        n = A - z
        ax.add_patch(Rectangle((n - 0.5, z - 0.5), 1, 1, facecolor="none", edgecolor="white", linewidth=2.0))
        ax.text(n + 0.6, z + 0.1, iso, color="black", fontsize=14, weight="bold")

    # If the YAML does not specify display limits, infer them from the data.
    zmin = int(df["Z"].min()) - 1 if zmin is None else zmin
    zmax = int(df["Z"].max()) + 1 if zmax is None else zmax
    nmin = int(df["N"].min()) - 1 if nmin is None else nmin
    nmax = int(df["N"].max()) + 1 if nmax is None else nmax
    ax.set_xlim(nmin - 0.5, nmax + 0.5)
    ax.set_ylim(zmin - 0.5, zmax + 0.5)
    ax.set_xlabel("Neutron number", fontsize=18, weight="bold")
    ax.set_ylabel("Proton number", fontsize=18, weight="bold")
    ax.tick_params(axis="both", labelsize=14, width=1.2)
    ax.set_aspect("equal")
    plt.savefig(out_prefix.with_suffix(".png"), dpi=300)
    plt.close(fig)


def overlay_from_csv(input_csv: Path, element: str, out_prefix: Path) -> None:
    df = pd.read_csv(input_csv)
    Z = ELEMENT_Z[element]
    sub = df[df["Z"] == Z].copy().sort_values("A")
    fig, ax = plt.subplots(figsize=(10, 6), dpi=220)

    # If a target column exists, this draws one line per target isotope; otherwise draws one summed line.
    if "target" in sub.columns:
        for target, dft in sub.groupby("target"):
            dfg = dft.groupby("A", as_index=False)["sigma_after_mb"].sum().sort_values("A")
            ax.plot(dfg["A"], dfg["sigma_after_mb"], marker="o", linewidth=2, label=str(target))
        ax.legend(fontsize=11)
    else:
        dfg = sub.groupby("A", as_index=False)["sigma_after_mb"].sum().sort_values("A")
        ax.plot(dfg["A"], dfg["sigma_after_mb"], marker="o", linewidth=2)

    ax.set_yscale("log")
    ax.set_xlabel("Mass number A", fontsize=15, weight="bold")
    ax.set_ylabel("Post-evaporation cross section (mb)", fontsize=15, weight="bold")
    ax.grid(alpha=0.25, which="both")
    plt.tight_layout()
    plt.savefig(out_prefix.with_suffix(".png"), dpi=300)
    plt.close(fig)


def recoil_triptych_from_csv(input_csv: Path, out_prefix: Path, angle_range=None, energy_range=None,
                             smear_display: bool = True,
                             smear_angle_sigma_deg: float = 0.20,
                             smear_energy_sigma_mevu: float = 0.015,
                             smear_mc_per_row: int = 6,
                             random_seed: int = 12345) -> None:
    df = pd.read_csv(input_csv)
    wcol = get_weight_col(df)
    x = df["theta_recoil_deg"].to_numpy(float)
    y = df["e_recoil_mevu"].to_numpy(float)
    w = df[wcol].to_numpy(float)

    # Displaying-only smearing to avoid a binned / striped appearance in the figure.
    if smear_display:
        rng = np.random.default_rng(random_seed)
        xs, ys, ws = [], [], []
        nrep = max(int(smear_mc_per_row), 1)
        ang_sig = max(float(smear_angle_sigma_deg), 0.0)
        ene_sig = max(float(smear_energy_sigma_mevu), 0.0)

        for xi, yi, wi in zip(x, y, w):
            if wi <= 0:
                continue
            xx = rng.normal(xi, ang_sig, nrep) if ang_sig > 0 else np.full(nrep, xi)
            yy = rng.normal(yi, ene_sig, nrep) if ene_sig > 0 else np.full(nrep, yi)
            ww = np.full(nrep, wi / nrep)
            xs.append(xx)
            ys.append(yy)
            ws.append(ww)

        if xs:
            x = np.concatenate(xs)
            y = np.concatenate(ys)
            w = np.concatenate(ws)

    # If limits are not given, this chooses percentile-based ranges from the data.
    if angle_range is None:
        angle_range = (float(np.percentile(x, 0.5)), float(np.percentile(x, 99.5)))
    if energy_range is None:
        energy_range = (max(0.0, float(np.percentile(y, 0.5))), float(np.percentile(y, 99.5)))

    fig = plt.figure(figsize=(15.5, 4.8), dpi=180)
    ax1 = fig.add_axes([0.06, 0.15, 0.27, 0.75])
    ax2 = fig.add_axes([0.39, 0.15, 0.27, 0.75])
    ax3 = fig.add_axes([0.72, 0.15, 0.23, 0.75])
    cax = fig.add_axes([0.96, 0.18, 0.015, 0.68])

    # Panel 1: angular distribution.
    bins_ang = np.linspace(angle_range[0], angle_range[1], 180)
    h, e = np.histogram(x, bins=bins_ang, weights=w)
    if h.max() > 0:
        h = h / h.max()
    ax1.step(0.5 * (e[:-1] + e[1:]), h, where="mid", linewidth=1.8)
    ax1.set_xlabel("Angle (degree)")
    ax1.set_ylabel("Intensity (arb. unit)")
    ax1.set_xlim(*angle_range)

    # Panel 2: recoil energy-per-nucleon distribution.
    bins_e = np.linspace(energy_range[0], energy_range[1], 180)
    h, e = np.histogram(y, bins=bins_e, weights=w)
    if h.max() > 0:
        h = h / h.max()
    ax2.step(0.5 * (e[:-1] + e[1:]), h, where="mid", linewidth=1.8)
    ax2.set_xlabel(r"$E$ (MeV/A)")
    ax2.set_ylabel("Intensity (arb. unit)")
    ax2.set_xlim(*energy_range)

    # Panel 3: recoil angle-energy correlation.
    H, xe, ye = np.histogram2d(x, y, bins=[bins_ang, bins_e], weights=w)
    H = H.T
    if H.max() > 0:
        H = 100.0 * H / H.max()
    Hm = np.ma.masked_less_equal(H, 0.0)

    cmap = plt.colormaps["jet"].copy()
    cmap.set_bad("white")

    pcm = ax3.pcolormesh(xe, ye, Hm, shading="auto", vmin=0, vmax=100, cmap=cmap)
    ax3.set_xlabel("Angle (degree)")
    ax3.set_ylabel(r"$E$ (MeV/A)")
    ax3.set_xlim(*angle_range)
    ax3.set_ylim(*energy_range)

    cb = fig.colorbar(pcm, cax=cax)
    cb.set_label("Intensity (arb. unit)")

    plt.savefig(out_prefix.with_suffix(".png"), dpi=300)
    plt.close(fig)


def command_run_case(args: argparse.Namespace) -> None:
    cfg = load_cfg(args.config)
    outdir = Path(cfg["paths"]["output_folder"]).expanduser()
    ensure_dir(outdir)
    interest = cfg["interest"]
    plot_cfg = cfg.get("plot", {})

    # The naming convention should match the outputs of the builder scripts.
    summed = outdir / f"{cfg['case_name']}_tlf_summed.csv"
    rows = outdir / f"{cfg['case_name']}_tlf_all_rows.csv"
    reco = outdir / f"{cfg['case_name']}_reconstructed.csv"

    if summed.exists():
        znmap_from_csv(
            summed,
            outdir / f"{cfg['case_name']}_tlf_map",
            plot_cfg.get("znmap_highlight", [f"{interest['isotopes'][0]}{interest['symbol']}" ]),
            plot_cfg.get("znmap_zmin"),
            plot_cfg.get("znmap_zmax"),
            plot_cfg.get("znmap_nmin"),
            plot_cfg.get("znmap_nmax"),
        )
    if rows.exists():
        overlay_from_csv(rows, interest["symbol"], outdir / f"{cfg['case_name']}_{interest['symbol']}_overlay")
    if reco.exists():
        recoil_triptych_from_csv(
            reco,
            outdir / f"{cfg['case_name']}_reconstructed",
            plot_cfg.get("recoil_angle_range"),
            plot_cfg.get("recoil_energy_range"),
            plot_cfg.get("smear_display", True),
            plot_cfg.get("smear_angle_sigma_deg", 0.20),
            plot_cfg.get("smear_energy_sigma_mevu", 0.015),
            plot_cfg.get("smear_mc_per_row", 6),
            cfg.get("random_seed", 12345),
        )


def main() -> int:
    ap = argparse.ArgumentParser(description="GRAZING plot maker")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run-case")
    p.add_argument("--config", required=True)
    args = ap.parse_args()
    if args.cmd == "run-case":
        command_run_case(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
