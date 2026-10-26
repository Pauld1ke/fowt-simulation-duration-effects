"""
Running mean +/- std convergence plot vs. simulation duration.

Replaces multi-panel raw time-history figures (e.g. manuscript Fig 3, 5)
with a single overlaid plot showing, for each simulation duration, the
running (cumulative) mean and std of a chosen output channel as a
function of elapsed time. Convergence of the curves indicates the
duration at which the statistic has stabilized.

Requirements: numpy, matplotlib. Uses the system `awk` (Git Bash / WSL /
Linux) to cheaply extract two columns from large OpenFAST .OUT files
before loading them into Python -- the raw files can be multiple GB, and
extracting only the needed columns first is far faster than parsing the
whole file with pandas/numpy.

Usage:
    python plot_running_stats.py
(edit the CONFIG block below to change base dir, wind speed, channel,
or duration list)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repository root
from fowt_duration.config import PROJECT_DIR, RUN_DIR, OUTPUT_DIR

import os
import subprocess
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# ----------------------------- CONFIG --------------------------------
BASE_DIR = str(RUN_DIR)
CACHE_DIR = os.path.join(str(OUTPUT_DIR), "_extracted_cache")
OUTDIR = os.path.join(BASE_DIR, "Plots")

WIND_SPEED_LABEL = "16p0mps"   # matches the file-name token, e.g. 4p0mps, 10p0mps, 16p0mps, 22p0mps
WIND_SPEED_DISPLAY = "16"      # for the title, e.g. "16"
CHANNEL = "TwrBsMyt"           # any column name present in the .OUT header
CHANNEL_UNITS = "kN$\\cdot$m"
CHANNEL_LABEL = r"$\mathrm{TwrBs}M_{yt}$"

DURATIONS = [600, 1200, 3600, 7200, 10800, 14400, 18000, 21600]  # seconds

FILE_TEMPLATE = "5MW_OC4Semi_WSt_WavesWN_{ws}_{dur}s.OUT"  # seed-averaged file, not _Seed1/_Seed2

PLOT_STRIDE = 200   # subsample factor for plotting only (running stats computed on full data)
# -----------------------------------------------------------------------


def get_column_index(sample_file: str, column_name: str) -> int:
    """Return 1-based column index of `column_name` from an OpenFAST .OUT header line."""
    with open(sample_file, "r") as f:
        header = f.readline().split()
    if column_name not in header:
        raise ValueError(f"Column '{column_name}' not found in {sample_file}. "
                          f"Available: {header}")
    return header.index(column_name) + 1  # awk fields are 1-indexed


def extract_columns(src_file: str, time_col: int, data_col: int, cache_path: str) -> None:
    """Use awk to pull just [time_col, data_col] out of a large OpenFAST .OUT file,
    skipping the two header lines (name row + units row)."""
    if os.path.exists(cache_path):
        return
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    awk_cmd = f"NR>2{{print ${time_col}, ${data_col}}}"
    with open(cache_path, "w") as out_f:
        subprocess.run(["awk", awk_cmd, src_file], stdout=out_f, check=True)


def running_mean_std(x: np.ndarray):
    """Vectorized running mean/std via cumulative sums (O(n), no python loop)."""
    n = np.arange(1, len(x) + 1)
    csum = np.cumsum(x)
    csum2 = np.cumsum(x * x)
    mean = csum / n
    var = np.clip(csum2 / n - mean ** 2, 0, None)
    return mean, np.sqrt(var)


def main():
    os.makedirs(OUTDIR, exist_ok=True)

    # Determine column index once from the shortest (fastest to open) file.
    sample_file = os.path.join(
        BASE_DIR, f"{DURATIONS[0]}s",
        FILE_TEMPLATE.format(ws=WIND_SPEED_LABEL, dur=DURATIONS[0]),
    )
    time_col = get_column_index(sample_file, "Time")
    data_col = get_column_index(sample_file, CHANNEL)

    # Extract (cached) columns for every duration.
    extracted = {}
    for d in DURATIONS:
        src = os.path.join(
            BASE_DIR, f"{d}s",
            FILE_TEMPLATE.format(ws=WIND_SPEED_LABEL, dur=d),
        )
        cache_path = os.path.join(CACHE_DIR, f"{CHANNEL}_{WIND_SPEED_LABEL}_{d}s.txt")
        extract_columns(src, time_col, data_col, cache_path)
        extracted[d] = cache_path

    # Plot.
    norm = mcolors.LogNorm(vmin=min(DURATIONS), vmax=max(DURATIONS))
    cmap = plt.get_cmap("viridis")

    fig, ax = plt.subplots(figsize=(9, 6), dpi=150)

    for d in DURATIONS:
        data = np.loadtxt(extracted[d])
        t, x = data[:, 0], data[:, 1]

        mean, std = running_mean_std(x)

        idx = slice(0, None, PLOT_STRIDE)
        color = cmap(norm(d))

        ax.plot(t[idx], mean[idx], color=color, lw=1.8,
                label=f"{d/60:g} min ({d} s)", zorder=3)
        ax.fill_between(t[idx], mean[idx] - std[idx], mean[idx] + std[idx],
                         color=color, alpha=0.12, linewidth=0, zorder=1)

    ax.set_xlabel("Elapsed simulation time, $t$ (s)", fontsize=11)
    ax.set_ylabel(f"Running statistics of {CHANNEL_LABEL} ({CHANNEL_UNITS})\n"
                  r"mean $\pm$ 1 std.", fontsize=11)
    ax.set_title(f"Convergence of {CHANNEL} statistics with simulation duration\n"
                 f"(V = {WIND_SPEED_DISPLAY} m/s, seed-averaged)", fontsize=12)
    ax.set_xscale("log")
    ax.set_xlim(1, max(DURATIONS) * 1.02)
    ax.grid(True, which="both", alpha=0.3)

    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, pad=0.02)
    cbar.set_label("Total run duration (s)", fontsize=10)

    leg = ax.legend(loc="lower right", fontsize=8, ncol=2, framealpha=0.9, title="Duration")
    leg.get_title().set_fontsize(9)

    fig.tight_layout()
    plt.show()

    # stem = f"Fig_RunningStats_{CHANNEL}_{WIND_SPEED_LABEL}"
    # png_path = os.path.join(OUTDIR, stem + ".png")
    # pdf_path = os.path.join(OUTDIR, stem + ".pdf")
    # fig.savefig(png_path, dpi=300)
    # fig.savefig(pdf_path)
    # print("Saved:", png_path)
    # print("Saved:", pdf_path)


if __name__ == "__main__":
    main()