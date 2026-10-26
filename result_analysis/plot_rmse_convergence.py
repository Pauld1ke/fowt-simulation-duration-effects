"""RMSE convergence-error plots of the ultimate-load (ULS) response (manuscript Figs. 8, 10, 12, 14).

For each channel c and duration T (T != reference) the extreme L_c(U,T) = max(|max|, |min|) of the
analysed record is normalised by the extreme of the reference duration at every wind speed U, and

    RMSE_c(T) = sqrt( mean_U ( L_c(U,T) / L_c(U,T_ref) - 1 )^2 )

A power law RMSE = a * T^b is fitted by least squares in log-log space; b is reported with its 95 %
t-interval (n = 7 points).  Input: Statistics_Maximum.csv / Statistics_Minimum.csv of every duration
folder (written by workflow/run_campaign.py --seed-stats).  Output: one EPS/SVG/PNG per channel family.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repository root
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
from fowt_duration.config import RUN_DIR, OUTPUT_DIR

EXTREME_STATISTIC = "magnitude"      # "magnitude" or "signed"
WS = [4.0, 10.0, 16.0, 22.0]
DUR = [600, 1200, 3600, 7200, 10800, 14400, 18000, 21600]
REF = 21600
ED = [d for d in DUR if d != REF]
GROUPS = {
 "Blade_RMSE": [("RootFxc1", r"$\mathrm{R}_{Fxc1}$ (flapwise shear)"), ("RootFyc1", r"$\mathrm{R}_{Fyc1}$ (edgewise shear)"),
                ("RootFzc1", r"$\mathrm{R}_{Fzc1}$ (axial force)"), ("RootMyc1", r"$\mathrm{R}_{Myc1}$ (flapwise moment)"),
                ("RootMzc1", r"$\mathrm{R}_{Mzc1}$ (torsional moment)"), ("RootMxc1", r"$\mathrm{R}_{Mxc1}$ (edgewise moment)")],
 "Tower_RMSE": [("TwrBsFxt", r"$\mathrm{T}_{Fxt}$ (fore-aft shear)"), ("TwrBsFyt", r"$\mathrm{T}_{Fyt}$ (side-to-side shear)"),
                ("TwrBsFzt", r"$\mathrm{T}_{Fzt}$ (axial force)"), ("TwrBsMxt", r"$\mathrm{T}_{Mxt}$ (roll moment)"),
                ("TwrBsMyt", r"$\mathrm{T}_{Myt}$ (fore-aft moment)"), ("TwrBsMzt", r"$\mathrm{T}_{Mzt}$ (torsional moment)")],
 "Floater_RMSE": [("PtfmSurge", r"$\xi_1$ (platform surge)"), ("PtfmHeave", r"$\xi_3$ (platform heave)"),
                  ("PtfmPitch", r"$\xi_5$ (platform pitch)"), ("HydroFxi", r"$\mathrm{H}_{Fxi}$ (hydrodynamic surge force)"),
                  ("HydroFyi", r"$\mathrm{H}_{Fyi}$ (hydrodynamic sway force)"), ("HydroMyi", r"$\mathrm{H}_{Myi}$ (hydrodynamic pitch moment)")],
 "MoorGen_RMSE": [("FAIRTEN1", r"$\mathrm{F_{T1}}$ (fairlead tension, line 1)"), ("ANCHTEN1", r"$\mathrm{A_{T1}}$ (anchor tension, line 1)"),
                  ("FAIRTEN2", r"$\mathrm{F_{T2}}$ (fairlead tension, line 2)"), ("ANCHTEN2", r"$\mathrm{A_{T2}}$ (anchor tension, line 2)"),
                  ("LSSGagMya", r"$\mathrm{L}_{Mya}$ (LSS side-to-side moment)"), ("LSSGagMza", r"$\mathrm{L}_{Mza}$ (LSS torsional moment)")],
}


def extreme(duration, channel):
    folder = os.path.join(str(RUN_DIR), f"{duration}s")
    mx = pd.read_csv(os.path.join(folder, "Statistics_Maximum.csv"), skiprows=[1]).set_index("Wind Speed")[channel]
    mn = pd.read_csv(os.path.join(folder, "Statistics_Minimum.csv"), skiprows=[1]).set_index("Wind Speed")[channel]
    if EXTREME_STATISTIC == "magnitude":
        return np.maximum(mx.abs(), mn.abs())
    return pd.Series(np.where(mx.abs() >= mn.abs(), mx, mn), index=mx.index)


def rmse_curve(channel):
    ref = extreme(REF, channel)
    out = []
    for d in ED:
        e = extreme(d, channel)
        r = np.array([e[w] / ref[w] for w in WS])
        out.append(np.sqrt(np.mean((r - 1.0) ** 2)))
    return np.array(out)


def fit_power_law(t, e):
    x, y = np.log(t), np.log(e)
    n = len(x)
    b, la = np.polyfit(x, y, 1)
    res = y - (la + b * x)
    s2 = res @ res / (n - 2)
    se = np.sqrt(s2 / ((x - x.mean()) ** 2).sum())
    ci = stats.t.ppf(0.975, n - 2) * se
    r2 = 1 - res @ res / ((y - y.mean()) ** 2).sum()
    return np.exp(la), b, ci, r2


def main():
    t = np.array(ED, float)
    tf = np.geomspace(t.min(), t.max(), 100)
    cmap = plt.get_cmap("tab10")
    rows = []
    for stem, chs in GROUPS.items():
        fig, ax = plt.subplots(figsize=(5.5, 2.75), dpi=150)
        for i, (ch, lab) in enumerate(chs):
            e = rmse_curve(ch)
            a, b, ci, r2 = fit_power_law(t, e)
            c = cmap(i)
            ax.scatter(t, e, color=c, s=45, zorder=3, edgecolor="white", linewidth=0.6)
            ax.plot(tf, a * tf ** b, color=c, lw=1.8, zorder=2, label=f"{lab}  ($b={b:.2f}\\pm{ci:.2f}$)")
            rows.append(dict(channel=ch, b=b, b_ci95=ci, r2=r2, **{f"rmse_{d}": v for d, v in zip(ED, e)}))
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_xticks(ED); ax.set_xticklabels([str(d) for d in ED], rotation=90)
        ax.tick_params(axis="both", labelsize=7, direction="in")
        ax.set_xlabel("Simulation duration, $T$ (s)", fontsize=8.5)
        ax.set_ylabel("RMSE of normalised ULS response\n(relative to 21600 s simulation)", fontsize=8.5)
        ax.grid(True, which="both", color="#d9d9d9", lw=0.5)
        lo, hi = ax.get_ylim(); ax.set_ylim(lo, hi * 6)
        ax.legend(loc="upper right", fontsize=5.8, ncol=2, handlelength=2.2, frameon=True, edgecolor="black",
                  fancybox=False, columnspacing=0.8)
        fig.tight_layout()
        for ext in ("eps", "svg", "png"):
            fig.savefig(os.path.join(str(OUTPUT_DIR), f"{stem}.{ext}"), dpi=300 if ext == "png" else None)
        plt.close(fig)
    pd.DataFrame(rows).to_csv(os.path.join(str(OUTPUT_DIR), "rmse_power_law_fits.csv"), index=False)
    print("written to", OUTPUT_DIR)


if __name__ == "__main__":
    main()
