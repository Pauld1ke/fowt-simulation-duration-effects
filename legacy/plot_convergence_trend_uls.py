"""
Duration-convergence trend plot for Ultimate Limit State (ULS) channels --
replacement for the Fig 9/10 (and 11/12, 13/14, 15/16) family of
line+bar-combo plus 4x8 heatmap figures.

For a single response channel, this produces ONE panel: x = simulation
duration (log scale), y = normalised extreme load (relative to the 21600 s
reference), with one line per wind speed and a shaded +/-10% acceptance
band. This carries the same information as a heatmap row (the normalised
ratio) plus the trend shape (monotonic approach vs. overshoot-then-settle)
that a heatmap cannot show, and replaces two figures (line+bar AND heatmap)
with one.

"Extreme" is defined per IEC/DEL convention used elsewhere in the
manuscript: whichever of the max or min statistic has the larger absolute
magnitude (keeping its sign), matching how Fig 9-16's heatmaps were
evidently constructed (values normalise to 1.00 at 21600 s and follow the
same sign convention as the reported ratios).

Data source: the pre-computed Statistics_Maximum.csv / Statistics_Minimum.csv
in each duration folder (one row per wind speed) -- no raw .OUT parsing
needed for this figure family.
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

# ----------------------------- CONFIG --------------------------------
BASE_DIR = str(RUN_DIR)
OUTDIR = os.path.join(BASE_DIR, "Plots")

CHANNEL = "RootMxc1"                      # column name in Statistics_*.csv
Blade_Channels = ["RootFxc1","RootFyc1","RootFzc1","RootMyc1","RootMzc1","RootMxc1"]
CHANNEL_LABEL = r"$\mathrm{RootM}_{xc1}$"  # for axis/title
CHANNEL_UNITS = "kN-m"

WIND_SPEEDS = [4.0, 10.0, 16.0, 22.0]
DURATIONS = [600, 1200, 3600, 7200, 10800, 14400, 18000, 21600]
REFERENCE_DURATION = 21600

ACCEPTANCE_BAND = (0.925, 1.075)  # +/-1%

WIND_SPEED_COLORS = {
    4.0: "#3b4cc0",
    10.0: "#4dac26",
    16.0: "#e08214",
    22.0: "#b2182b",
}
# -----------------------------------------------------------------------
# -----------------------------------------------------------------------
Legend_FontSize = 7
Axis_FontSize = 9.5
Ticks_FontSize = 8
SubPlot_Fontsize = 6
reduct = 1

def load_extreme(duration: int) -> pd.Series:
    """Return the signed extreme (larger-magnitude of max/min) for CHANNEL,
    indexed by wind speed, for one duration folder."""
    folder = os.path.join(BASE_DIR, f"{duration}s")
    max_df = pd.read_csv(os.path.join(folder, "Statistics_Maximum.csv"), skiprows=[1])
    min_df = pd.read_csv(os.path.join(folder, "Statistics_Minimum.csv"), skiprows=[1])

    max_df = max_df.set_index("Wind Speed")[CHANNEL]
    min_df = min_df.set_index("Wind Speed")[CHANNEL]

    extreme = np.where(max_df.abs() >= min_df.abs(), max_df, min_df)
    return pd.Series(extreme, index=max_df.index)


def main():
    os.makedirs(OUTDIR, exist_ok=True)

    extremes_by_duration = {d: load_extreme(d) for d in DURATIONS}
    reference = extremes_by_duration[REFERENCE_DURATION]

    fig, ax = plt.subplots(figsize=(4.5, 1.5), dpi=150)

    band_pct = (ACCEPTANCE_BAND[1] - 1) * 100
    ax.axhspan(*ACCEPTANCE_BAND, color="0.85", zorder=0, label=f"±Convergence band")
    # ax.axhspan(*ACCEPTANCE_BAND, color="0.85", zorder=0, label=f"±{band_pct:.0f}% band ({ACCEPTANCE_BAND[0]:.2f}–{ACCEPTANCE_BAND[1]:.2f})")
    ax.axhline(1.0, color="0.4", lw=1, ls="--", zorder=1)

    for ws in WIND_SPEEDS:
        norm_ratios = [extremes_by_duration[d][ws] / reference[ws] for d in DURATIONS]
        ax.plot(DURATIONS, norm_ratios, marker="o", ms=5, lw=1.5,
                color=WIND_SPEED_COLORS[ws], label=f"{ws:g} m/s", zorder=3)

    ax.set_xscale("log")
    ax.set_xticks(DURATIONS)
    ax.set_xticklabels([str(d) for d in DURATIONS], rotation=90, fontsize=Ticks_FontSize)
    ax.tick_params(axis='both', labelsize=Ticks_FontSize-reduct, direction='in')
    ax.yaxis.get_offset_text().set_fontsize(Ticks_FontSize-reduct)
    ax.set_xlabel("Simulation duration (s)", fontsize=Axis_FontSize-reduct)
    # ax.set_ylabel(f"Normalised extreme {CHANNEL_LABEL}\n(relative to {REFERENCE_DURATION} s)", fontsize=Axis_FontSize)
    ax.set_ylabel(f"Normalised extreme  (relative to {REFERENCE_DURATION} s)", fontsize=Axis_FontSize-reduct)
    # ax.set_title(f"Convergence of {CHANNEL} ultimate load with simulation duration", fontsize=12)
    ax.grid(True, which="both", alpha=0.3)
    # ax.legend(loc="best", fontsize=Legend_FontSize, ncol=5, framealpha=0.9, handlelength = 2, frameon=True, edgecolor='black', fancybox=False, shadow=False)

    fig.tight_layout()
    plt.show()

    # image_format = 'svg' # e.g .png, .svg, eps, etc.
    # image_name = os.path.join(str(OUTPUT_DIR), f'{CHANNEL}.svg')
    # plt.savefig(image_name, format=image_format, dpi=1200)
    # plt.close(fig)
    # print("Saved:", image_name)

    # stem = f"Fig_ConvergenceTrend_ULS_{CHANNEL}"
    # png_path = os.path.join(OUTDIR, stem + ".png")
    # pdf_path = os.path.join(OUTDIR, stem + ".pdf")
    # fig.savefig(png_path, dpi=300)
    # fig.savefig(pdf_path)
    # print("Saved:", png_path)
    # print("Saved:", pdf_path)


if __name__ == "__main__":
    main()
