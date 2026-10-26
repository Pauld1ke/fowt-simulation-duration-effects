"""
RMSE convergence-error plot for blade-root ULS channels -- a statistically
richer alternative to the per-channel trend-line plot (plot_convergence_trend_uls.py)
when summarising MULTIPLE channels at once.

Rationale: showing 6 channels x 4 wind speeds as individual trend lines
either needs 6 panels (no new information density) or one plot with 24
overlapping lines (unreadable). Instead, for each duration T and channel c,
we collapse across the 4 wind speeds into a single scalar error:

    RMSE_c(T) = sqrt( mean_over_windspeeds[ (L_c(U,T)/L_c(U,21600s) - 1)^2 ] )

i.e. the RMS deviation of the normalised extreme from the converged (1.0)
reference, aggregated over wind speed. This is exactly the "error vs.
resolution" plot used in mesh/time-step convergence studies: log(duration)
on x, log(RMSE) on y. A power-law decay RMSE ~ a * T^b is then fitted per
channel by linear regression in log-log space, giving an actual
quantitative convergence rate (the exponent b) instead of prose like
"converges by roughly 7200 s".

The reference duration (21600 s) is excluded from the error curve itself
since RMSE is trivially zero there by construction.

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

Legend_FontSize = 7
Axis_FontSize = 9.5
Ticks_FontSize = 8
SubPlot_Fontsize = 6
reduct = 1

# ----------------------------- CONFIG --------------------------------
BASE_DIR = str(RUN_DIR)
OUTDIR = os.path.join(BASE_DIR, "Plots")

CHANNELS = [
    # "RootFxc1",
    # "RootFyc1",
    # "RootFzc1",
    # "RootMyc1",
    # "RootMzc1",
    # "RootMxc1",]

    # "TwrBsFxt",
    # "TwrBsFyt",
    # "TwrBsFzt",
    # "TwrBsMxt",
    # "TwrBsMyt",
    # "TwrBsMzt",]
    
    # "PtfmSurge",
    # "PtfmHeave",
    # "PtfmPitch",
    # "HydroFxi",
    # "HydroFyi",
    # "HydroMyi",]

    "FAIRTEN1",
    "ANCHTEN1",
    "FAIRTEN2",
    "ANCHTEN2",
    "LSSGagMya",
    "LSSGagMza"]

CHANNEL_LABELS = {
    # "RootFxc1": r"$\mathrm{R}_{Fxc1}$ (flapwise shear)",
    # "RootFyc1": r"$\mathrm{R}_{Fyc1}$ (edgewise shear)",
    # "RootFzc1": r"$\mathrm{R}_{Fzc1}$ (axial force)",
    # "RootMxc1": r"$\mathrm{R}_{Mxc1}$ (edgewise moment)",
    # "RootMyc1": r"$\mathrm{R}_{Myc1}$ (flapwise moment)",
    # "RootMzc1": r"$\mathrm{R}_{Mzc1}$ (torsional moment)",}

    # "TwrBsFxt": r"$\mathrm{T}_{Fxt}$ (fore-aft shear)",
    # "TwrBsFyt": r"$\mathrm{T}_{Fyt}$ (side-to-side shear)",
    # "TwrBsFzt": r"$\mathrm{T}_{Fzt}$ (axial force)",
    # "TwrBsMxt": r"$\mathrm{T}_{Mxt}$ (fore-aft moment)",
    # "TwrBsMyt": r"$\mathrm{T}_{Myt}$ (side-to-side moment)",
    # "TwrBsMzt": r"$\mathrm{T}_{Mzt}$ (torsional moment)",}

    # "PtfmSurge": r"$\mathrm{\xi_1}$ (platform surge)",
    # "PtfmHeave": r"$\mathrm{\xi_3}$ (platform heave)",
    # "PtfmPitch": r"$\mathrm{\xi_5}$ (platform pitch)",
    # "HydroFxi": r"$\mathrm{H}_{Fxi}$ (hydrodynamic surge force)",
    # "HydroFyi": r"$\mathrm{H}_{Fyi}$ (hydrodynamic sway force)",
    # "HydroMyi": r"$\mathrm{H}_{Myi}$ (hydrodynamic pitch moment)",}

    "FAIRTEN1": r"$\mathrm{F_{T1}}$ (fairlead tension, line 1)",
    "ANCHTEN1": r"$\mathrm{A_{T1}}$ (anchor tension, line 1)",
    "FAIRTEN2": r"$\mathrm{F_{T2}}$ (fairlead tension, line 2)",
    "ANCHTEN2": r"$\mathrm{A_{T2}}$ (anchor tension, line 2)",
    "LSSGagMya": r"$\mathrm{L}_{Mya}$ (LSS gage side-to-side moment)",
    "LSSGagMza": r"$\mathrm{L}_{Mza}$ (LSS gage torsional moment)",}

WIND_SPEEDS = [4.0, 10.0, 16.0, 22.0]
DURATIONS = [600, 1200, 3600, 7200, 10800, 14400, 18000, 21600]
REFERENCE_DURATION = 21600
ERROR_DURATIONS = [d for d in DURATIONS if d != REFERENCE_DURATION]
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


def rmse_curve(channel: str) -> np.ndarray:
    """RMSE (across wind speeds) of the normalised extreme vs. 1.0, per duration."""
    reference = load_extreme(REFERENCE_DURATION, channel)
    rmse = []
    for d in ERROR_DURATIONS:
        extreme_d = load_extreme(d, channel)
        ratios = np.array([extreme_d[ws] / reference[ws] for ws in WIND_SPEEDS])
        rmse.append(np.sqrt(np.mean((ratios - 1.0) ** 2)))
    return np.array(rmse)


def fit_power_law(durations, rmse):
    """log(RMSE) = log(a) + b*log(T) via least squares. Returns (a, b, fitted_rmse)."""
    log_t = np.log(durations)
    log_e = np.log(rmse)
    b, log_a = np.polyfit(log_t, log_e, 1)
    a = np.exp(log_a)
    fitted = a * np.array(durations, dtype=float) ** b
    return a, b, fitted


def main():
    os.makedirs(OUTDIR, exist_ok=True)

    cmap = cm.get_cmap("tab10")
    fig, ax = plt.subplots(figsize=(4.7, 2.25), dpi=150)

    durations_arr = np.array(ERROR_DURATIONS, dtype=float)
    t_fit_range = np.geomspace(durations_arr.min(), durations_arr.max(), 100)

    for i, channel in enumerate(CHANNELS):
        rmse = rmse_curve(channel)
        color = cmap(i)

        ax.scatter(durations_arr, rmse, color=color, s=30, zorder=3, edgecolor="white", linewidth=0.6)

        a, b, _ = fit_power_law(durations_arr, rmse)
        fit_line = a * t_fit_range ** b
        ax.plot(t_fit_range, fit_line, color=color, lw=1.2, zorder=2,
                label=f"{CHANNEL_LABELS[channel]}  ($\\mathrm{{RMSE}} \\propto T^{{{b:.2f}}}$)")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xticks(ERROR_DURATIONS)
    ax.set_xticklabels([str(d) for d in ERROR_DURATIONS], rotation=90)
    ax.tick_params(axis='both', labelsize=Ticks_FontSize-reduct, direction='in')
    ax.set_xlabel("Simulation duration, $T$ (s)", fontsize=Axis_FontSize-reduct)
    # ax.set_ylabel("RMSE of normalised extreme load\n(relative to 21600 s reference, across 4 wind speeds)", fontsize=Axis_FontSize-reduct)
    ax.set_ylabel("RMSE of normalised ULS response\n(relative to 21600 s  simulation)", fontsize=Axis_FontSize-reduct)
    # ax.set_title("Convergence-error decay of blade-root ULS channels", fontsize=12)
    ax.grid(True, which="both", alpha=0.3)
    # ax.grid(False, which="both")
    # ax.legend(loc="upper right", fontsize=Legend_FontSize, ncol=2, handlelength = 3, frameon=True, edgecolor='black', fancybox=False, shadow=False)
    fig.tight_layout()
    plt.show()
    # stem = "Fig_RMSEConvergence_ULS_BladeRoot"
    # png_path = os.path.join(OUTDIR, stem + ".png")
    # pdf_path = os.path.join(OUTDIR, stem + ".pdf")
    # fig.savefig(png_path, dpi=300)
    # fig.savefig(pdf_path)
    # print("Saved:", png_path)
    # print("Saved:", pdf_path)


if __name__ == "__main__":
    main()
