"""Central configuration: folder layout and campaign settings.

All scripts take their paths from here.  By default the project folder is ``<repo>/project``;
set the environment variable ``FOWT_PROJECT_DIR`` to use a different location (for example a
large disk, since the OpenFAST output of the full campaign is far larger than 1 TB).
"""
import os
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = Path(os.environ.get("FOWT_PROJECT_DIR", REPO_DIR / "project"))

ENVIRON_DIR = PROJECT_DIR / "01EnviroData"            # TurbSim input and wind/sea-state table
ENVIRON_FILE = ENVIRON_DIR / "EnvironInput.inp"       # wind speed, Hs, Tp for the four conditions
TURBSIM_FILE = ENVIRON_DIR / "TurbSim.inp"
RUN_DIR = PROJECT_DIR / "DLC1p1"                      # one sub-folder per duration, e.g. 600s/
BASE_FOLDER = RUN_DIR / "00BaseFolder"                # OpenFAST input files copied into every run folder
OUTPUT_DIR = RUN_DIR / "Plots"                        # figures and tables written by the scripts
OUTPUT_DIR.mkdir(parents=True, exist_ok=True) if PROJECT_DIR.exists() else None

# --- campaign settings -------------------------------------------------------------------------
WIND_SPEEDS = [4, 10, 16, 22]                                        # m/s (see EnvironInput.inp)
SIM_TIMES = [600, 1200, 3600, 7200, 10800, 14400, 18000, 21600]      # s, OpenFAST TMax
RUN_IN_S = 200                                                       # s discarded before statistics

# Wind (TurbSim RandSeed1) and wave (SeaState WaveSeed(1)) seed numbers and the labels used in the
# output file names (<...>_<duration>s_<label>.OUT).  CONFIRM THE FINAL SEED TABLE BEFORE RELEASE.
SEED_NUMBERS = [2318573, 3318574, 4318575, 4319572, 4319573]
SEED_LABELS = ["Seed1", "Seed2", "Seed3", "Seed4", "Seed5"]
SeedNoDict = dict(zip(seeds, SeedNoList))
