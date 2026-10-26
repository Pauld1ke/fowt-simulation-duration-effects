"""
3x3 scatterplot matrix (SPLOM) of blade-root MOMENT channel convergence
(RootMxc1, RootMyc1, RootMzc1). Same construction as
plot_splom_convergence_uls.py (blade-root forces) -- see that file for the
full design rationale.

Layout:
  - Diagonal panels (i, i): single-channel convergence trend -- normalised
    extreme vs. duration (log-x), one line per wind speed, dashed reference
    at 1.0. Shares the global uniform y-range.
  - Off-diagonal panels (i, j): dense pairwise scatter (PCHIP-interpolated
    along duration per wind speed) of channel_j's ratio (x) vs channel_i's
    ratio (y), coloured by duration.

Data source: pre-computed Statistics_Maximum.csv / Statistics_Minimum.csv
in each duration folder (one row per wind speed) -- no raw .OUT parsing.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repository root
from fowt_duration.config import PROJECT_DIR, RUN_DIR, OUTPUT_DIR

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors

Legend_FontSize = 7
Axis_FontSize = 8
Ticks_FontSize = 8
SubPlot_Fontsize = 6
reduct = 2

# ----------------------------- CONFIG --------------------------------
BASE_DIR = str(RUN_DIR)
OUTDIR = os.path.join(BASE_DIR, "Plots")

CHANNELS = ["RootMxc1", "RootMyc1", "RootMzc1"]
CHANNEL_SHORT = {
    "RootMxc1": r"$ \rm \mathrm{R}_{Mxc1}$",
    "RootMyc1": r"$ \rm \mathrm{R}_{Myc1}$",
    "RootMzc1": r"$ \rm \mathrm{R}_{Mzc1}$",
}

WIND_SPEEDS = [4.0, 10.0, 16.0, 22.0]
WIND_SPEED_COLORS = {4.0: "#3b4cc0", 10.0: "#4dac26", 16.0: "#e08214", 22.0: "#b2182b"}

DURATIONS = [600, 1200, 3600, 7200, 10800, 14400, 18000, 21600]
REFERENCE_DURATION = 21600
# -----------------------------------------------------------------------


def load_extreme(duration: int, channel: str) -> pd.Series:
    """Signed extreme (larger-magnitude of max/min) for `channel`, indexed by wind speed."""
    folder = os.path.join(BASE_DIR, f"{duration}s")
    max_df = pd.read_csv(os.path.join(folder, "Statistics_Maximum.csv"), skiprows=[1])
    min_df = pd.read_csv(os.path.join(folder, "Statistics_Minimum.csv"), skiprows=[1])

    max_df = max_df.set_index("Wind Speed")[channel]
    min_df = min_df.set_index("Wind Speed")[channel]

    extreme = np.where(max_df.abs() >= min_df.abs(), max_df, min_df)
    return pd.Series(extreme, index=max_df.index)


def ratio_table(channel: str) -> pd.DataFrame:
    """Rows = durations, columns = wind speeds, values = normalised ratio."""
    reference = load_extreme(REFERENCE_DURATION, channel)
    rows = {}
    for d in DURATIONS:
        extreme_d = load_extreme(d, channel)
        rows[d] = {ws: extreme_d[ws] / reference[ws] for ws in WIND_SPEEDS}
    return pd.DataFrame(rows).T  # index=duration, columns=wind speed


def main():
    os.makedirs(OUTDIR, exist_ok=True)

    ratios = {c: ratio_table(c) for c in CHANNELS}

    norm = mcolors.LogNorm(vmin=min(DURATIONS), vmax=max(DURATIONS))
    cmap = plt.get_cmap("viridis")

    # Uniform y-axis per ROW (see plot_splom_convergence_uls.py for rationale).
    row_y_lim = {}
    for c in CHANNELS:
        vals = ratios[c].values.ravel()
        pad = 0.03 * (vals.max() - vals.min())
        row_y_lim[c] = (vals.min() - pad, vals.max() + pad)

    fig, axes = plt.subplots(3, 3, figsize=(3.25, 1.75), dpi=200)

    for i, ci in enumerate(CHANNELS):
        for j, cj in enumerate(CHANNELS):
            ax = axes[i, j]

            if i == j:
                # Diagonal: single-channel convergence trend.
                for ws in WIND_SPEEDS:
                    ax.plot(DURATIONS, ratios[ci][ws], marker="o", ms=2, lw=1.0, color=WIND_SPEED_COLORS[ws], label=f"{ws:g} m/s")
                ax.axhline(1.0, color="0.4", lw=1, ls="--", zorder=1)
                ax.set_xscale("log")
            else:
                # Off-diagonal: pairwise scatter of the 8 real simulated durations
                # per wind speed (32 points total), coloured by duration.
                for d in DURATIONS:
                    x = ratios[cj].loc[d].values
                    y = ratios[ci].loc[d].values
                    ax.scatter(x, y, color=cmap(norm(d)), s=14, zorder=3,
                               edgecolor="white", linewidth=0.4)
                ax.axhline(1.0, color="0.6", lw=0.8, ls="--", zorder=1)
                ax.axvline(1.0, color="0.6", lw=0.8, ls="--", zorder=1)

            ax.set_ylim(row_y_lim[ci])
            ax.grid(True, alpha=0.25)
            if i == 2:
                ax.set_xlabel(CHANNEL_SHORT[cj] if i != j else "Duration (s)", fontsize=Axis_FontSize-reduct-0.5)
            if j == 0:
                ax.set_ylabel(CHANNEL_SHORT[ci] if i != j else "Normalised ratio", fontsize=Axis_FontSize-reduct-0.5)
            ax.tick_params(labelsize=7)
            ax.tick_params(axis='both', labelsize=Ticks_FontSize-reduct-1, direction='in')
            ax.yaxis.get_offset_text().set_fontsize(Ticks_FontSize-reduct-1)

            # Only show y tick labels on the left column, x tick labels on the bottom row.
            if j != 0:
                ax.tick_params(labelleft=False)
            if i != 2:
                ax.tick_params(labelbottom=False)

    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    # cbar = fig.colorbar(sm, ax=axes, pad=0.02, shrink=0.8)
    # cbar.set_label("Simulation duration (s)", fontsize=10)

    stem = "02BRM-SPLOM"

    image_format = 'svg'
    image_name = os.path.join(str(OUTPUT_DIR), f'{stem}.svg')
    fig.savefig(image_name, format=image_format, dpi=1200)
    plt.close(fig)
    print("Saved:", image_name)


if __name__ == "__main__":
    main()
