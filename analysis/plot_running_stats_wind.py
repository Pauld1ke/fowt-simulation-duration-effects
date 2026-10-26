"""
Running mean +/- std convergence plot vs. simulation duration -- Wind1VelX variant.

Same pipeline as plot_running_stats.py, reconfigured to plot the along-wind
inflow velocity channel (Wind1VelX) instead of a structural/mooring load
channel. Useful as a sanity-check / companion figure: it shows whether the
*input* turbulent wind statistics (mean speed, turbulence intensity) have
converged over a given duration, which is a natural baseline to compare
against convergence of the *output* load channels.

Requirements: numpy, matplotlib. Uses the system `awk` (Git Bash / WSL /
Linux) to cheaply extract two columns from large OpenFAST .OUT files
before loading them into Python -- the raw files can be multiple GB, and
extracting only the needed columns first is far faster than parsing the
whole file with pandas/numpy.

Usage:
    python plot_running_stats_wind.py
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
import math

# ----------------------------- CONFIG --------------------------------
BASE_DIR = str(RUN_DIR)
CACHE_DIR = os.path.join(str(OUTPUT_DIR), "_extracted_cache")
OUTDIR = os.path.join(BASE_DIR, "Plots")

WIND_SPEEDS = [
    ("4p0mps", "4"),
    ("10p0mps", "10"),
    ("16p0mps", "16"),
    ("22p0mps", "22"),
]  # (file-name token, display value) pairs -- one figure generated per entry
CHANNEL = "Wind1VelX"          # any column name present in the .OUT header
CHANNEL_UNITS = "m/s"
CHANNEL_LABEL = r"$\mathrm{U}_X$"

DURATIONS = [600, 1200, 3600, 7200, 10800, 14400, 18000, 21600]  # seconds

FILE_TEMPLATE = "5MW_OC4Semi_WSt_WavesWN_{ws}_{dur}s.OUT"  # seed-averaged file, not _Seed1/_Seed2

PLOT_STRIDE = 200   # subsample factor for plotting only (running stats computed on full data)
# -----------------------------------------------------------------------
Legend_FontSize = 10
Axis_FontSize = 9.5
Ticks_FontSize = 8
SubPlot_Fontsize = 6

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
    skipping the two header lines (name row + units row). Writes to a temp file
    first and only renames it into place once awk has finished successfully, so
    an interrupted/failed run can never leave a poisoned (empty or partial)
    cache entry behind that looks "already extracted" on the next run."""
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 0:
        return
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    tmp_path = cache_path + ".tmp"
    awk_cmd = f"NR>2{{print ${time_col}, ${data_col}}}"
    with open(tmp_path, "w") as out_f:
        subprocess.run(["awk", awk_cmd, src_file], stdout=out_f, check=True)
    os.replace(tmp_path, cache_path)


def running_mean_std(x: np.ndarray):
    """Vectorized running mean/std via cumulative sums (O(n), no python loop)."""
    n = np.arange(1, len(x) + 1)
    csum = np.cumsum(x)
    csum2 = np.cumsum(x * x)
    mean = csum / n
    var = np.clip(csum2 / n - mean ** 2, 0, None)
    return mean, np.sqrt(var)


def make_plot(wind_speed_label: str, wind_speed_display: str):
    # Determine column index once from the shortest (fastest to open) file.
    sample_file = os.path.join(
        BASE_DIR, f"{DURATIONS[0]}s",
        FILE_TEMPLATE.format(ws=wind_speed_label, dur=DURATIONS[0]),
    )
    time_col = get_column_index(sample_file, "Time")
    data_col = get_column_index(sample_file, CHANNEL)

    # Extract (cached) columns for every duration.
    extracted = {}
    for d in DURATIONS:
        src = os.path.join(
            BASE_DIR, f"{d}s",
            FILE_TEMPLATE.format(ws=wind_speed_label, dur=d),
        )
        cache_path = os.path.join(CACHE_DIR, f"{CHANNEL}_{wind_speed_label}_{d}s.txt")
        extract_columns(src, time_col, data_col, cache_path)
        extracted[d] = cache_path

    # Plot.
    norm = mcolors.LogNorm(vmin=min(DURATIONS), vmax=max(DURATIONS))
    cmap = plt.get_cmap("viridis")

    fig, ax = plt.subplots(figsize=(4.5, 1.25), dpi=150)

    for d in DURATIONS:
        data = np.loadtxt(extracted[d])
        t, x = data[:, 0], data[:, 1]

        mean, std = running_mean_std(x)

        idx = slice(0, None, PLOT_STRIDE)
        color = cmap(norm(d))

        ax.plot(t[idx], mean[idx], color=color, lw=1.0,
                label=f"{d/60:g} min ({d} s)", zorder=3)
        ax.fill_between(t[idx], mean[idx] - std[idx], mean[idx] + std[idx],
                         color=color, alpha=0.12, linewidth=0, zorder=1)
        # integer_ticks = range(math.floor(min(mean[idx])), math.ceil(max(mean[idx])) + 1)

    reduct = 2
    ax.set_xlabel("Elapsed simulation time, $t$ (s)", fontsize=Axis_FontSize-reduct-1)
    ax.set_ylabel(f"Statistics of {CHANNEL_LABEL} ({CHANNEL_UNITS})", fontsize=Axis_FontSize-reduct-1)

    
    ax.set_ylim([math.floor(min(mean[idx])), math.ceil(max(mean[idx]))+2])
    # ax.set_yticks(integer_ticks)
    ax.set_xscale("log")
    ax.set_xlim(1, max(DURATIONS) * 1.02)
    ax.grid(True, which="both", alpha=0.3)
    # ax.grid(False, which="both")

    ax.tick_params(axis='both', labelsize=Ticks_FontSize-reduct, direction='in')
    # ax.yaxis.set_major_formatter(plt.ScalarFormatter(useMathText=True))
    # ax.ticklabel_format(axis='y', style='sci', scilimits=(0,0))
    ax.yaxis.get_offset_text().set_fontsize(Ticks_FontSize-reduct)

    # sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    # sm.set_array([])
    # cbar = fig.colorbar(sm, ax=ax, pad=0.02)
    # # cbar.set_label("Total run duration (s)", fontsize=8)
    # cbar.ax.tick_params(labelsize=Ticks_FontSize-reduct)

    # leg = ax.legend(loc='upper center', ncol=int(len(DURATIONS)/2), 
    #            fontsize = Legend_FontSize, handlelength = 3, frameon=True, edgecolor='black',
    #            fancybox=False, shadow=False)
    # leg.get_title().set_fontsize(9)
    # leg = ax.legend(loc="lower right", fontsize=6.5, ncol=4, framealpha=0.9, handlelength = 1.5, frameon=True, edgecolor='black', fancybox=False, shadow=False)
    # leg.get_title().set_fontsize(6.)
    
    fig.tight_layout()
    plt.show()

    stem = f"Stat_{CHANNEL}_{wind_speed_label}"

    # image_format = 'svg' # e.g .png, .svg, eps, etc.
    # image_name = os.path.join(str(OUTPUT_DIR), f'{stem}.svg')
    # plt.savefig(image_name, format=image_format, dpi=1200)


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    for wind_speed_label, wind_speed_display in WIND_SPEEDS:
        make_plot(wind_speed_label, wind_speed_display)


if __name__ == "__main__":
    main()