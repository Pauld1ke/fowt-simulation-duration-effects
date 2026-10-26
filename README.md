# Simulation duration effects on ultimate and fatigue loads of a semi-submersible floating wind turbine

Code accompanying the manuscript *Simulation Duration Requirements for Floating Wind Turbine Ultimate and
Fatigue Loads* (O. P. Dike, T. Barker, W. Li, V. Vaziri, M. Kapitaniak; under review). It automates a
fully coupled OpenFAST campaign for the OC4-DeepCwind semi-submersible with the NREL 5 MW turbine and
post-processes it into the ultimate-load (ULS) and damage-equivalent-load (DEL) convergence results and the
wind-speed surrogate model of the paper.

> Citation: *to be added on publication.*

## Study design

| Item | Setting |
|---|---|
| Model | NREL 5 MW on the OC4-DeepCwind semi-submersible, 200 m water depth |
| Software | OpenFAST v4.0.2 (ElastoDyn, InflowWind, AeroDyn, ServoDyn, SeaState, HydroDyn, **MoorDyn v2.2.2**), TurbSim |
| Wind / sea states | 4, 10, 16, 22 m/s with (Hs, Tp) = (1.102 m, 8.515 s), (1.537, 7.651), (2.598, 7.643), (4.027, 8.987); table in `project/01EnviroData/EnvironInput.inp` |
| Wind field | IEC Kaimal, normal turbulence model (see `TurbSim.inp`), collinear wind and waves |
| Durations (`TMax`) | 600, 1200, 3600, 7200, 10 800, 14 400, 18 000, 21 600 s; reference = 21 600 s |
| Seeds | wind (`RandSeed1`) and wave (`WaveSeed(1)`) seed numbers in `fowt_duration/config.py` |
| Time step | 0.0125 s; first 200 s of every record discarded (run-in) |
| Fatigue | rainflow DEL (openfast-toolbox), Wöhler exponents m = 3, 4, 8, 10 |

Each duration is generated and simulated separately (TurbSim `AnalysisTime` and SeaState `WaveTMax`
equal the run length), so short records are **not** truncations of long ones.

## Repository layout

```
fowt_duration/          helper package
    config.py             paths and campaign settings (edit seeds/durations here)
    openfast_functions.py core functions: TurbSim/OpenFAST automation, seed averaging, statistics, DELs, plots
    plot_settings.py      shared plot constants
workflow/
    run_campaign.py       command-line driver (TurbSim -> OpenFAST -> per-seed statistics)
    post_processing.py    rose plots, section stresses, wind-speed surrogate helpers (calls listed as examples)
analysis/               scripts that produce the paper figures
    plot_rmse_convergence.py                       RMSE convergence plots (Figs. 8, 10, 12, 14)
    plot_running_stats_wind.py / _wave.py / .py    running-mean and std convergence of the inputs (Figs. 6, 7)
    predictive_model_lib.py                        surrogate model, model selection, LOOCV
    plot_predictive_model_reliability_summary.py   surrogate reliability chart (Fig. 21)
    plot_predictive_model_parity.py                parity and residual plots
legacy/                 superseded scripts (SPLOM convergence figures, signed-extreme RMSE plot)
project/                inputs only; run output is written here and is git-ignored
    01EnviroData/         TurbSim.inp, EnvironInput.inp, Run_TurbSim.bat
    DLC1p1/00BaseFolder/  OpenFAST input files copied into every run folder
```

Heat maps, bar charts and rose plots of the paper are produced by the plotting functions in
`fowt_duration/openfast_functions.py` (`plot_normalised_heatmap`, `plot_normalised_DEL_barchart`,
`plot_channels_force_rose`, `plot_extreme_statistics`); example calls are in `workflow/post_processing.py`.

## Requirements

* Python 3.12 and `pip install -r requirements.txt`
* OpenFAST v4.0.2 (`OpenFAST.exe`) and TurbSim (`TurbSim_x64.exe`) on `PATH` (Windows; the helper
  functions use Windows path separators and `.bat` launchers)
* Model data **not included** (public NREL files): the WAMIT hydrodynamic data
  `5MW_Baseline/HydroData/marin_semi.*` and the controller `Discon_OC3Hywind.dll`, available in the OpenFAST
  [r-test](https://github.com/OpenFAST/r-test) case `5MW_OC4Semi_WSt_WavesWN`. Place them so that the relative
  paths in the `.dat` files (`../../5MW_Baseline/...`) resolve from `project/DLC1p1/<duration>s/`.
* Disk space: the full campaign produces well over 1 TB of text output. Set `FOWT_PROJECT_DIR` to a large
  disk to keep it outside the repository.

## Reproducing the results

```bash
pip install -r requirements.txt
python workflow/run_campaign.py --turbsim                 # wind fields
python workflow/run_campaign.py --openfast                # all durations, wind speeds and seeds (days)
python workflow/run_campaign.py --seed-stats              # Statistics_*.csv and DEL_m*.csv per duration
python analysis/plot_rmse_convergence.py                  # RMSE convergence figures
python analysis/plot_predictive_model_reliability_summary.py
```

Use `--durations 14400 18000 21600` to run only some durations.

## Important notes on the method

1. **Per-seed statistics.** Extremes and DELs are computed for each seed separately and then aggregated
   (`write_seed_aggregated_statistics`). Averaging the seed time histories first (`average_openfast_outputs`,
   `--average`) removes part of the random-phase response and gives non-conservative extremes and DELs; it
   is kept only for the running-statistics plots.
2. **Magnitude-based extreme.** The ULS extreme is `max(|max|, |min|)`. A signed extreme changes sign between
   records for near-zero-mean channels (e.g. tower torsion, shaft bending) and produces spurious RMSE results;
   the signed option is retained as `EXTREME_STATISTIC = "signed"` for comparison.
3. **ServoDyn "never" times.** ServoDyn uses `9999.9` s as a "never" placeholder for `TPitManS(1-3)`,
   `TimGenOf`, `THSSBrDp`, `TYCOn` and `TYawManS`. Any run longer than 9999.9 s therefore pitches the
   blades to feather and switches the generator off at about 10 000 s. These inputs are set to `99999.9` in
   `project/DLC1p1/00BaseFolder`; keep them above the longest run when changing durations.
4. **Seed labels.** Output files are named `<wind>mps_<duration>s_<SeedLabel>.OUT`; labels and numbers are
   defined together in `fowt_duration/config.py` and must stay paired.

## License

MIT (see `LICENSE`). The OpenFAST input files in `project/` derive from the public NREL OC4-DeepCwind and
NREL 5 MW reference definitions.
