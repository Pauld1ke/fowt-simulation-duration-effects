"""
Shared library for the revised ULS/DEL wind-speed predictive model.

Replaces the manuscript's fixed-form approach (always quadratic for ULS,
always power-law for DEL, validated only by in-sample R^2) with:

  1. Per-channel model selection between candidate functional forms,
     chosen by LEAVE-ONE-OUT CROSS-VALIDATION (LOOCV) R^2 rather than
     in-sample R^2. With only 4 wind-speed data points and a 3-parameter
     quadratic, in-sample R^2 is close to meaningless -- LOOCV R^2 (fit
     on 3 points, predict the held-out 4th, repeat) is the honest metric.

  2. Prediction intervals via standard linear-regression theory, using
     the covariance formulas the manuscript already derives (Eq. 6.8,
     6.15) but never actually computes.

ULS candidates: linear and quadratic (both in U).
DEL candidates: power-law (log-log linear) -- already the minimal
    physically-motivated form; kept as the sole candidate since a
    2-parameter model already leaves 2 residual degrees of freedom
    with n=4, unlike the ULS quadratic's 1 d.o.f.

Data source: pre-computed Statistics_Maximum.csv / Statistics_Minimum.csv
and DEL_m*.csv in the 21600s (reference) duration folder -- these are
the highest-fidelity available estimates and match what the manuscript's
own Section 6 model is trained on.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repository root
from fowt_duration.config import PROJECT_DIR, RUN_DIR, OUTPUT_DIR

import os
import numpy as np
import pandas as pd
from scipy import stats

BASE_DIR = str(RUN_DIR)
REFERENCE_DURATION = 21600
EXTREME_STATISTIC = "magnitude"   # "magnitude" = max(|max|,|min|) (used in the paper); "signed" = legacy
WIND_SPEEDS = np.array([4.0, 10.0, 16.0, 22.0])

# S-N slope convention matching the manuscript: m=10 for composite blade
# channels, m=4 for welded-steel tower / mooring chain / forged-steel shaft.
BLADE_CHANNELS = {"RootFxc1", "RootFyc1", "RootFzc1", "RootMxc1", "RootMyc1", "RootMzc1"}


def del_m_for_channel(channel: str) -> int:
    return 10 if channel in BLADE_CHANNELS else 4


# --------------------------- data loading ---------------------------

def load_extreme(channel: str, duration: int = REFERENCE_DURATION) -> np.ndarray:
    """Signed extreme (larger-magnitude of max/min) for `channel` at each wind speed."""
    folder = os.path.join(BASE_DIR, f"{duration}s")
    max_df = pd.read_csv(os.path.join(folder, "Statistics_Maximum.csv"), skiprows=[1]).set_index("Wind Speed")[channel]
    min_df = pd.read_csv(os.path.join(folder, "Statistics_Minimum.csv"), skiprows=[1]).set_index("Wind Speed")[channel]
    if EXTREME_STATISTIC == "magnitude":
        extreme = pd.Series(np.maximum(max_df.abs(), min_df.abs()), index=max_df.index)
    else:  # "signed": larger-magnitude of max/min with its sign retained
        extreme = pd.Series(np.where(max_df.abs() >= min_df.abs(), max_df, min_df), index=max_df.index)
    return np.array([extreme[ws] for ws in WIND_SPEEDS], dtype=float)


def _find_del_column(df: pd.DataFrame, channel: str) -> str:
    matches = [c for c in df.columns if c.split("_[")[0] == channel]
    if not matches:
        raise KeyError(f"No DEL column found for '{channel}' in {list(df.columns)[:5]}...")
    return matches[0]


def load_del(channel: str, duration: int = REFERENCE_DURATION) -> np.ndarray:
    """DEL for `channel` at each wind speed, using the appropriate S-N slope m."""
    m = del_m_for_channel(channel)
    folder = os.path.join(BASE_DIR, f"{duration}s")
    df = pd.read_csv(os.path.join(folder, f"DEL_m{m}.csv"), skiprows=[1]).set_index("Wind Speed")
    col = _find_del_column(df.reset_index(), channel)
    series = df[col]
    return np.array([series[ws] for ws in WIND_SPEEDS], dtype=float)


# --------------------------- candidate models ---------------------------

def _design_linear(U):
    return np.column_stack([np.ones_like(U), U])


def _design_quadratic(U):
    return np.column_stack([np.ones_like(U), U, U ** 2])


def _fit_ols(X, y):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return beta


def _r2(y, yhat):
    ss_res = np.sum((y - yhat) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    return 1 - ss_res / ss_tot if ss_tot > 0 else np.nan


def _loocv(U, y, design_fn):
    """Leave-one-out predictions and R^2 for a linear-in-parameters model."""
    n = len(y)
    preds = np.empty(n)
    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        X_train = design_fn(U[mask])
        beta = _fit_ols(X_train, y[mask])
        X_i = design_fn(U[[i]])
        preds[i] = X_i @ beta
    return preds, _r2(y, preds)


def _loocv_with_intervals(U, y, design_fn, confidence=0.95):
    """Leave-one-out predictions with a genuine out-of-sample prediction
    interval for each held-out point (interval computed from the 3-point
    training fit, evaluated at the held-out point's design row)."""
    n = len(y)
    preds = np.empty(n)
    los = np.empty(n)
    his = np.empty(n)
    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        X_train = design_fn(U[mask])
        y_train = y[mask]
        beta = _fit_ols(X_train, y_train)
        X_i = design_fn(U[[i]])[0]
        yhat, lo, hi = _prediction_interval(X_train, y_train, beta, X_i, confidence)
        preds[i], los[i], his[i] = yhat, lo, hi
    return preds, los, his


def _prediction_interval(X, y, beta, x_new_row, confidence=0.95):
    """Standard OLS prediction interval at a new design row, using the
    manuscript's own Cov(beta_hat) = sigma^2 (X^T X)^-1 (Eq. 6.8/6.15)."""
    n, p = X.shape
    dof = max(n - p, 1)
    resid = y - X @ beta
    sigma2 = np.sum(resid ** 2) / dof
    XtX_inv = np.linalg.pinv(X.T @ X)
    leverage = x_new_row @ XtX_inv @ x_new_row
    se_pred = np.sqrt(sigma2 * (1 + leverage))
    tval = stats.t.ppf(1 - (1 - confidence) / 2, dof)
    yhat = x_new_row @ beta
    return yhat, yhat - tval * se_pred, yhat + tval * se_pred


class FittedModel:
    def __init__(self, name, design_fn, U, y):
        self.name = name
        self.design_fn = design_fn
        X = design_fn(U)
        self.beta = _fit_ols(X, y)
        self.yhat_insample = X @ self.beta
        self.r2_insample = _r2(y, self.yhat_insample)
        self.loo_preds, self.r2_loocv = _loocv(U, y, design_fn)
        self.loo_preds_pi, self.loo_lo, self.loo_hi = _loocv_with_intervals(U, y, design_fn)
        self.U = U
        self.y = y
        self.X = X

    def predict_with_interval(self, U_new, confidence=0.95):
        X_new = self.design_fn(np.atleast_1d(U_new))
        out = [_prediction_interval(self.X, self.y, self.beta, row, confidence) for row in X_new]
        yhat, lo, hi = zip(*out)
        return np.array(yhat), np.array(lo), np.array(hi)


def select_uls_model(U, y):
    """Fit linear and quadratic candidates, select by LOOCV R^2 (ties -> simpler/linear)."""
    linear = FittedModel("linear", _design_linear, U, y)
    quadratic = FittedModel("quadratic", _design_quadratic, U, y)
    if quadratic.r2_loocv > linear.r2_loocv + 1e-9:
        return quadratic
    return linear


def fit_del_model(U, y):
    """Power-law fit via log-log OLS (single candidate -- see module docstring).
    Internally trained on (ln U, ln y); use predict_del_with_interval() below
    to get back-transformed predictions in real DEL units, not log_uls_model's
    raw predict_with_interval (which assumes the design_fn's input domain
    matches U directly)."""
    logU = np.log(U)
    logy = np.log(y)
    model = FittedModel("power-law", _design_linear, logU, logy)
    model.log_space = True
    # LOOCV predictions/actuals/intervals in real (non-log) DEL units, for parity plots.
    model.loo_preds_real = np.exp(model.loo_preds)
    model.loo_lo_real = np.exp(model.loo_lo)
    model.loo_hi_real = np.exp(model.loo_hi)
    model.y_real = y
    model.r2_loocv_real = _r2(y, model.loo_preds_real)
    return model


def predict_del_with_interval(model, U_new, confidence=0.95):
    """Back-transformed prediction + interval in real DEL units for a
    power-law model fit by fit_del_model()."""
    logU_new = np.log(np.atleast_1d(U_new))
    yhat_log, lo_log, hi_log = model.predict_with_interval(logU_new, confidence)
    return np.exp(yhat_log), np.exp(lo_log), np.exp(hi_log)
