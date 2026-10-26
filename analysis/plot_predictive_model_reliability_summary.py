"""
Model-reliability summary chart for the revised ULS/DEL wind-speed
predictive model -- one figure showing LOOCV R^2 for every channel and
response type at once, replacing the need to page through Fig 22-26 to
work out which channels the surrogate model can actually be trusted for.

In-sample R^2 is shown as a faint marker for comparison, but LOOCV R^2
(the honest, out-of-sample metric) is what the bars/markers are sorted
and coloured by. A shaded band below R^2=0 marks "worse than predicting
the mean" -- i.e. the model provides no useful information at all for
that channel/response.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repository root
from fowt_duration.config import PROJECT_DIR, RUN_DIR, OUTPUT_DIR

import os
import numpy as np
import matplotlib.pyplot as plt

import predictive_model_lib as lib

Legend_FontSize = 7
Axis_FontSize = 8
Ticks_FontSize = 8
SubPlot_Fontsize = 6
reduct = 1

OUTDIR = os.path.join(lib.BASE_DIR, "Plots")

CHANNELS = [
    "RootFxc1", "RootFyc1", "RootFzc1", "RootMxc1", "RootMyc1", "RootMzc1",
    "TwrBsFxt", "TwrBsFyt", "TwrBsFzt", "TwrBsMxt", "TwrBsMyt", "TwrBsMzt",
    "PtfmSurge", "PtfmHeave", "PtfmPitch",
    "ANCHTEN1", "FAIRTEN1", "LSSGagMya",
]
NO_DEL = {"PtfmSurge", "PtfmHeave", "PtfmPitch"}

# CHANNEL_LABELS = {
#     "RootFxc1": r"$\mathrm{RootF}_{xc1}$", "RootFyc1": r"$\mathrm{RootF}_{yc1}$", "RootFzc1": r"$\mathrm{RootF}_{zc1}$",
#     "RootMxc1": r"$\mathrm{RootM}_{xc1}$", "RootMyc1": r"$\mathrm{RootM}_{yc1}$", "RootMzc1": r"$\mathrm{RootM}_{zc1}$",
#     "TwrBsFxt": r"$\mathrm{TwrBsF}_{xt}$", "TwrBsFyt": r"$\mathrm{TwrBsF}_{yt}$", "TwrBsFzt": r"$\mathrm{TwrBsF}_{zt}$",
#     "TwrBsMxt": r"$\mathrm{TwrBsM}_{xt}$", "TwrBsMyt": r"$\mathrm{TwrBsM}_{yt}$", "TwrBsMzt": r"$\mathrm{TwrBsM}_{zt}$",
#     "PtfmSurge": "Surge", "PtfmHeave": "Heave", "PtfmPitch": "Pitch",
#     "ANCHTEN1": r"$\mathrm{AnchTen}_1$", "FAIRTEN1": r"$\mathrm{FairTen}_1$", "LSSGagMya": r"$\mathrm{LSSGagM}_{ya}$",
# }

CHANNEL_LABELS = {
    "RootFxc1": r"$ \rm \mathrm{R}_{Fxc1}$", "RootFyc1": r"$ \rm \mathrm{R}_{Fyc1}$", "RootFzc1": r"$ \rm \mathrm{R}_{Fzc1}$",
    "RootMxc1": r"$ \rm \mathrm{R}_{Mxc1}$", "RootMyc1": r"$ \rm \mathrm{R}_{Myc1}$", "RootMzc1": r"$ \rm \mathrm{R}_{Mzc1}$",
    "TwrBsFxt": r"$ \rm \mathrm{T}_{Fxt}$", "TwrBsFyt": r"$ \rm \mathrm{T}_{Fyt}$", "TwrBsFzt": r"$ \rm \mathrm{T}_{Fzt}$",
    "TwrBsMxt": r"$ \rm \mathrm{T}_{Mxt}$", "TwrBsMyt": r"$ \rm \mathrm{T}_{Myt}$", "TwrBsMzt": r"$ \rm \mathrm{T}_{Mzt}$",
    "PtfmSurge": r"$ \xi_1 $", "PtfmHeave": r"$ \xi_3 $", "PtfmPitch": r"$ \xi_5 $",
    "ANCHTEN1": r"$ \rm \mathrm{A_{Tn1}}$", "FAIRTEN1": r"$ \rm \mathrm{F_{Tn1}}$", "LSSGagMya": r"$ \rm \mathrm{L}_{Mya}$",
}

def collect_results():
    rows = []
    for channel in CHANNELS:
        y_uls = lib.load_extreme(channel)
        model = lib.select_uls_model(lib.WIND_SPEEDS, y_uls)
        rows.append({
            "channel": channel, "response": "ULS",
            "r2_insample": model.r2_insample, "r2_loocv": model.r2_loocv,
            "form": model.name,
        })
        if channel not in NO_DEL:
            y_del = lib.load_del(channel)
            del_model = lib.fit_del_model(lib.WIND_SPEEDS, y_del)
            r2_in_real = 1 - np.sum((del_model.y_real - np.exp(del_model.yhat_insample)) ** 2) / np.sum((del_model.y_real - del_model.y_real.mean()) ** 2)
            rows.append({
                "channel": channel, "response": "DEL",
                "r2_insample": r2_in_real, "r2_loocv": del_model.r2_loocv_real,
                "form": "power-law",
            })
    return rows


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    rows = collect_results()

    labels = [f"{CHANNEL_LABELS[r['channel']]} ({r['response']})" for r in rows]
    r2_loocv = np.array([max(r["r2_loocv"], -1.0) for r in rows])  # clip for display only
    r2_loocv_raw = np.array([r["r2_loocv"] for r in rows])
    r2_insample = np.array([r["r2_insample"] for r in rows])

    order = np.argsort(r2_loocv_raw)[::-1]
    labels = [labels[i] for i in order]
    r2_loocv = r2_loocv[order]
    r2_loocv_raw = r2_loocv_raw[order]
    r2_insample = r2_insample[order]

    colors = []
    for v in r2_loocv_raw:
        if v >= 0.8:
            colors.append("#1a9850")
        elif v >= 0.0:
            colors.append("#e08214")
        else:
            colors.append("#b2182b")

    fig, ax = plt.subplots(figsize=(5.5, 0.1*len(labels)+2.0), dpi=150)
    y_pos = np.arange(len(labels))

    ax.axvspan(-1.05, 0, color="#b2182b", alpha=0.08, zorder=0)
    ax.axvline(0, color="0.3", lw=1, ls="--", zorder=1)
    ax.axvline(0.8, color="0.6", lw=0.8, ls=":", zorder=1)

    ax.barh(y_pos, r2_loocv, color=colors, zorder=3, height=0.6)
    ax.scatter(r2_insample, y_pos, marker="|", s=140, color="0.15", zorder=4, label="in-sample $R^2$ (for comparison)")

    for yi, v_raw in zip(y_pos, r2_loocv_raw):
        if v_raw < -1.0:
            ax.text(-1.02, yi, f"{v_raw:.1f}", va="center", ha="right", fontsize=Legend_FontSize, color="#b2182b")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=Axis_FontSize-reduct)
    ax.set_xlim(-1.1, 1.05)
    ax.set_xlabel("$R^2$ (bars = LOOCV, out-of-sample; ticks = in-sample)", fontsize=Axis_FontSize-reduct)
    # ax.set_title("Predictive-model reliability by channel: LOOCV vs. in-sample $R^2$", fontsize=11)
    ax.legend(loc="lower right", fontsize=Legend_FontSize-reduct, ncol=4, framealpha=0.9, handlelength = 1.5, frameon=True, edgecolor='black', fancybox=False, shadow=False)
    # ax.grid(True, axis="x", alpha=0.25)
    ax.grid(False)
    ax.invert_yaxis()

    ax.tick_params(axis='both', labelsize=Ticks_FontSize-reduct-0.5, direction='in')
    # ax.yaxis.set_major_formatter(plt.ScalarFormatter(useMathText=True))
    # ax.ticklabel_format(axis='y', style='sci', scilimits=(0,0))
    # ax.yaxis.get_offset_text().set_fontsize(Ticks_FontSize-reduct)

    fig.tight_layout()
    # plt.show()

    stem = 'ReliabilityModel'

    image_format = 'svg' # e.g .png, .svg, eps, etc.
    image_name = os.path.join(str(OUTPUT_DIR), f'{stem}.svg')
    plt.savefig(image_name, format=image_format, dpi=1200)


if __name__ == "__main__":
    main()
