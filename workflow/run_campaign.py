"""Driver for the simulation-duration campaign.

Typical use (from the repository root):

    python workflow/run_campaign.py --turbsim                 # generate the TurbSim wind fields
    python workflow/run_campaign.py --openfast                # run OpenFAST for all durations/winds/seeds
    python workflow/run_campaign.py --openfast --durations 14400 18000 21600
    python workflow/run_campaign.py --seed-stats              # per-seed extremes/DELs, aggregated across seeds
    python workflow/run_campaign.py --legacy-stats            # statistics/DELs of the seed-averaged records

Every step is optional and can be combined.  OpenFAST.exe and TurbSim_x64.exe must be on PATH (the
Run_*.bat files call them by name).
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fowt_duration import config
from fowt_duration import openfast_functions as of


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--turbsim", action="store_true", help="generate TurbSim .bts wind fields for all seeds/durations")
    ap.add_argument("--openfast", action="store_true", help="run OpenFAST for every duration, wind speed and seed")
    ap.add_argument("--average", action="store_true", help="write seed-averaged .OUT files (legacy; not used for loads)")
    ap.add_argument("--seed-stats", action="store_true", help="per-seed extremes and DELs, then aggregate over seeds")
    ap.add_argument("--legacy-stats", action="store_true", help="statistics and DELs from the seed-averaged records")
    ap.add_argument("--durations", type=int, nargs="+", help="override the durations in fowt_duration/config.py")
    ap.add_argument("--skip", type=int, default=config.RUN_IN_S, help="run-in period removed before statistics (s)")
    args = ap.parse_args()

    os.chdir(config.PROJECT_DIR)                       # the helper functions use project-relative paths
    durations = args.durations or config.SIM_TIMES
    of.SimTimeList[:] = durations                      # RUN_*_ANALYSIS iterate over this list

    if args.turbsim:
        of.RUN_TURBSIM_ANALYSIS(str(config.ENVIRON_FILE), str(config.TURBSIM_FILE))
    if args.openfast:
        of.RUN_OPENFAST_ANALYSIS(str(config.ENVIRON_FILE), "5MW_OC4Semi_WSt_WavesWN.fst",
                                 "NRELOffshrBsline5MW_OC4DeepCwindSemi_InflowWind.dat", "SeaState.dat",
                                 str(config.BASE_FOLDER))
    if args.average:
        for t in durations:
            for u in config.WIND_SPEEDS:
                of.average_openfast_outputs(t, u, SeedNo=len(config.SEED_NUMBERS))
    folders = [str(config.RUN_DIR / f"{t}s") + os.sep for t in durations]
    if args.seed_stats:
        for f in folders:
            of.write_seed_aggregated_statistics(f, skip=args.skip)
    if args.legacy_stats:
        for f in folders:
            of.write_output_statistics(f, skip=args.skip)
            of.write_damage_equivalent_load(f, skip=args.skip)


if __name__ == "__main__":
    main()
