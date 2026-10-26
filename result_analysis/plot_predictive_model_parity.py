"""
Parity (predicted vs. actual) + residual plots for the revised ULS/DEL
wind-speed predictive model -- replacement for the manuscript's Fig 22-26
(a smooth curve fit through only 4 points, in-sample R^2 displayed with
no uncertainty and no out-of-sample validation).

For each channel and response type (ULS extreme, DEL where applicable):
  - Parity panel: x = actual (21600 s reference) value, y = leave-one-out
    cross-validated (LOOCV) prediction -- i.e. genuinely out-of-sample,
    not the in-sample fitted curve. Error bars are the per-point LOOCV
    prediction interval (95%). A 1:1 dashed line marks perfect prediction.
    Both in-sample R^2 and LOOCV R^2 are annotated so the gap between
    them -- the actual point of this figure -- is visible directly.
  - Residual panel: (LOOCV prediction - actual) vs. wind speed, to check
    whether the chosen functional form leaves a systematic pattern in U
    (would indicate the wrong functional form) or looks like noise (good).

ULS uses whichever of {linear, quadratic} has the better LOOCV R^2 per
channel (see predictive_model_lib.select_uls_model); DEL uses the
power-law form (see predictive_model_lib.fit_del_model).

One figure is generated per channel "family", matching the grouping
already used for the SPLOM convergence figures: Blade Root Forces,
Blade Root Moments, Tower Base Forces, Tower Base Moments, Platform
Motions (ULS only -- no fatigue DEL for rigid-body motions), and
Mooring + Generator.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repository root
from fowt_duration.config import PROJECT_DIR, RUN_DIR, OUTPUT_DIR

import os
import numpy as np
import matplotlib.pyplot as plt

import predictive_model_lib as lib

OUTDIR = os.path.join(lib.BASE_DIR, "Plots")

WIND_SPEED_COLORS = {4.0: "#3b4cc0", 10.0: "#4dac26", 16.0: "#e08214", 22.0: "#b2182b"}

FAMILIES = {
    "Blade-Root-Forces": {
        "channels": ["RootFxc1", "RootFyc1", "RootFzc1"],
        "labels": {"RootFxc1": r"$\mathrm{RootF}_{xc1}$", "RootFyc1": r"$\mathrm{RootF}_{yc1}$", "RootFzc1": r"$\mathrm{RootF}_{zc1}$"},
        "has_del": True,
    },
    "Blade-Root-Moments": {
        "channels": ["RootMxc1", "RootMyc1", "RootMzc1"],
        "labels": {"RootMxc1": r"$\mathrm{RootM}_{xc1}$", "RootMyc1": r"$\mathrm{RootM}_{yc1}$", "RootMzc1": r"$\mathrm{RootM}_{zc1}$"},
        "has_del": True,
    },
    "Tower-Base-Forces": {
        "channels": ["TwrBsFxt", "TwrBsFyt", "TwrBsFzt"],
        "labels": {"TwrBsFxt": r"$\mathrm{TwrBsF}_{xt}$", "TwrBsFyt": r"$\mathrm{TwrBsF}_{yt}$", "TwrBsFzt": r"$\mathrm{TwrBsF}_{zt}$"},
        "has_del": True,
    },
    "Tower-Base-Moments": {
        "channels": ["TwrBsMxt", "TwrBsMyt", "TwrBsMzt"],
        "labels": {"TwrBsMxt": r"$\mathrm{TwrBsM}_{xt}$", "TwrBsMyt": r"$\mathrm{TwrBsM}_{yt}$", "TwrBsMzt": r"$\mathrm{TwrBsM}_{zt}$"},
        "has_del": True,
    },
    "Platform-Motions": {
        "channels": ["PtfmSurge", "PtfmHeave", "PtfmPitch"],
        "labels": {"PtfmSurge": r"$\mathrm{Surge}$", "PtfmHeave": r"$\mathrm{Heave}$", "PtfmPitch": r"$\mathrm{Pitch}$"},
        "has_del": False,
    },
    "Mooring-Generator": {
        "channels": ["ANCHTEN1", "FAIRTEN1", "LSSGagMya"],
        "labels": {"ANCHTEN1": r"$\mathrm{AnchTen}_1$", "FAIRTEN1": r"$\mathrm{FairTen}_1$", "LSSGagMya": r"$\mathrm{LSSGagM}_{ya}$"},
        "has_del": True,
    },
}

R2_GOOD = 0.8
R2_POOR = 0.0


def _r2_color(r2):
    if r2 >= R2_GOOD:
        return "#1a9850"
    if r2 >= R2_POOR:
        return "#e08214"
    return "#b2182b"


def _plot_parity_residual(ax_parity, ax_resid, U, y_actual, loo_pred, loo_lo, loo_hi,
                           r2_insample, r2_loocv, title):
    colors = [WIND_SPEED_COLORS[u] for u in U]

    # Axis range is set from the point estimates only (actual + LOOCV predicted),
    # NOT the prediction-interval bounds -- a single wildly uncertain LOOCV fold
    # (a real, honest result for some channels) would otherwise blow out the
    # whole plot and make every other point unreadable. Interval bars are
    # clipped to a generous multiple of that range and any clipped bar is
    # marked with an open arrow so the reader knows it's cut off, not zero.
    core_vals = np.concatenate([y_actual, loo_pred])
    core_lo, core_hi = core_vals.min(), core_vals.max()
    pad = 0.15 * (core_hi - core_lo) if core_hi > core_lo else 0.15 * abs(core_hi)
    lims = [core_lo - pad, core_hi + pad]
    cap = (lims[1] - lims[0]) * 0.6  # max error-bar extent beyond the point, in axis units

    lo_err = np.clip(loo_pred - loo_lo, 0, cap)
    hi_err = np.clip(loo_hi - loo_pred, 0, cap)
    clipped = (loo_pred - loo_lo > cap) | (loo_hi - loo_pred > cap)

    ax_parity.errorbar(y_actual, loo_pred, yerr=[lo_err, hi_err], fmt="none",
                        ecolor="0.6", elinewidth=1, capsize=3, zorder=2)
    ax_parity.scatter(y_actual, loo_pred, c=colors, s=55, zorder=3, edgecolor="white", linewidth=0.6)
    for xi, yi, is_clipped, hi_e in zip(y_actual, loo_pred, clipped, hi_err):
        if is_clipped:
            ax_parity.annotate("", xy=(xi, yi + hi_e), xytext=(xi, yi + hi_e * 0.85),
                                arrowprops=dict(arrowstyle="-|>", color="0.5", lw=1))

    ax_parity.plot(lims, lims, ls="--", color="0.4", lw=1, zorder=1)
    ax_parity.set_xlim(lims)
    ax_parity.set_ylim(lims)

    box_color = _r2_color(r2_loocv)
    ax_parity.text(0.05, 0.95, f"$R^2_{{in}}$={r2_insample:.2f}\n$R^2_{{LOOCV}}$={r2_loocv:.2f}",
                    transform=ax_parity.transAxes, fontsize=7.5, va="top", ha="left",
                    bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=box_color, lw=1.2))
    ax_parity.set_title(title, fontsize=9)
    ax_parity.set_xlabel("Actual", fontsize=7.5)
    ax_parity.set_ylabel("LOOCV predicted", fontsize=7.5)
    ax_parity.tick_params(labelsize=6.5)
    ax_parity.grid(True, alpha=0.25)

    resid_pct = (loo_pred - y_actual) / np.abs(y_actual) * 100
    ax_resid.axhline(0, color="0.4", lw=1, ls="--", zorder=1)
    ax_resid.scatter(U, resid_pct, c=colors, s=45, zorder=3, edgecolor="white", linewidth=0.6)
    ax_resid.set_xlabel("Wind speed (m/s)", fontsize=7.5)
    ax_resid.set_ylabel("LOOCV residual (%)", fontsize=7.5)
    ax_resid.tick_params(labelsize=6.5)
    ax_resid.grid(True, alpha=0.25)


def make_family_figure(family_name, spec):
    channels = spec["channels"]
    labels = spec["labels"]
    has_del = spec["has_del"]

    n_rows = len(channels) * (2 if has_del else 1)
    fig, axes = plt.subplots(n_rows, 2, figsize=(6.5, 2.3 * n_rows), dpi=150)
    if n_rows == 1:
        axes = axes.reshape(1, 2)

    row = 0
    for channel in channels:
        y_uls = lib.load_extreme(channel)
        model = lib.select_uls_model(lib.WIND_SPEEDS, y_uls)
        _plot_parity_residual(
            axes[row, 0], axes[row, 1], lib.WIND_SPEEDS, y_uls,
            model.loo_preds_pi, model.loo_lo, model.loo_hi,
            model.r2_insample, model.r2_loocv,
            f"{labels[channel]} -- ULS ({model.name})",
        )
        row += 1

        if has_del:
            y_del = lib.load_del(channel)
            del_model = lib.fit_del_model(lib.WIND_SPEEDS, y_del)
            _plot_parity_residual(
                axes[row, 0], axes[row, 1], lib.WIND_SPEEDS, del_model.y_real,
                del_model.loo_preds_real, del_model.loo_lo_real, del_model.loo_hi_real,
                _r2_insample_real(del_model), del_model.r2_loocv_real,
                f"{labels[channel]} -- DEL (power-law, m={lib.del_m_for_channel(channel)})",
            )
            row += 1

    fig.tight_layout()
    plt.show()
    return fig


def _r2_insample_real(del_model):
    """In-sample R^2 in real (non-log) DEL units, for consistent display with LOOCV R^2 real."""
    from predictive_model_lib import _r2
    return _r2(del_model.y_real, np.exp(del_model.yhat_insample))


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    for family_name, spec in FAMILIES.items():
        fig = make_family_figure(family_name, spec)
        stem = f"Fig_PredictiveModel_Parity_{family_name}"
        png_path = os.path.join(OUTDIR, stem + ".png")
        pdf_path = os.path.join(OUTDIR, stem + ".pdf")
        fig.savefig(png_path, dpi=300)
        fig.savefig(pdf_path)
        plt.close(fig)
        print("Saved:", png_path)


if __name__ == "__main__":
    main()
