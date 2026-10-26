import glob #to work through files in a folder
import xlsxwriter #to write to Excel
from xlsxwriter.utility import xl_rowcol_to_cell
import inspect #to allow identification of Python file in Excel footer
import os #to allow Python to open MS Excel once the results are complete
import yaml #to allow access to config file for user inputs
import math
import numpy as np
import pandas as pd
import sys
from openpyxl.styles.borders import Border, Side
from openpyxl import Workbook
import time
from .plot_settings import *
from .config import OUTPUT_DIR, SEED_NUMBERS as SeedNoList, SEED_LABELS as seeds, SIM_TIMES as SimTimeList
import matplotlib.pyplot as plt
import subprocess
import shutil
import matplotlib.gridspec as gridspec
from matplotlib.ticker import FormatStrFormatter
from matplotlib.transforms import ScaledTranslation
from scipy.special import gamma
from mpl_toolkits.mplot3d import Axes3D
import seaborn as sns
from matplotlib import cm
from scipy.stats import weibull_min, weibull_max, lognorm
import re
from matplotlib import lines
from openfast_toolbox.io import FASTOutputFile
from openfast_toolbox.postpro import equivalent_load


#--------------------------------------------------------------------------------------------------------------
# Function that takes a list of floats and converts each to whole "p" decimal for text and titles
#--------------------------------------------------------------------------------------------------------------
def OutPutMod(Variable, Ind):
    wholePart = int(math.modf(Variable[Ind])[1])
    decimPart =int(round(math.modf(Variable[Ind])[0]*10,1))

    OutPutID = f'{wholePart}p{decimPart}'

    return OutPutID

def OutPutModV2(Variable):
    wholePart = int(math.modf(Variable)[1])
    decimPart =int(round(math.modf(Variable)[0]*10,1))

    OutPutID = f'{wholePart}p{decimPart}'

    return OutPutID

def OutPutMod_Mod(Variable):
    wholePart = int(math.modf(Variable)[1])
    decimPart =int(round(math.modf(Variable)[0]*10,1))

    OutPutID = f'{wholePart}p{decimPart}'

    return OutPutID

#------------------------------------------------------------------------------------------------------------------
# Function that reads all files of the same extension type in a folder
#------------------------------------------------------------------------------------------------------------------
def READALLFILES(ExtensionString):

    AnalysisPath = os.getcwd()+r'\*.'+ExtensionString
    AnalysisFile = glob.glob(AnalysisPath)

    AnalysisOutputFileList = []
    for i in range(len(AnalysisFile)):
        AnalysisOutputFileList.append(str(AnalysisFile[i].split('\\')[-1]))
    
    return AnalysisOutputFileList

#------------------------------------------------------------------------------------------------------------------
# A function that gives a dictionary 'key; when given the output value
#------------------------------------------------------------------------------------------------------------------
def get_keys_from_value(dictionary, value):
    KeyVal = [k for k, v in dictionary.items() if v == value]
    return KeyVal[0]

#------------------------------------------------------------------------------------------------------------------
# A function that reads all output files in a folder excluding those with 'Seed' and 'MD' in the file name
#------------------------------------------------------------------------------------------------------------------
def get_output_files(folder_path):
    import glob
    output_files = [f for f in glob.glob(folder_path + "*.OUT") if 'Seed' not in f and 'MD' not in f]
    return output_files

#------------------------------------------------------------------------------------------------------------------
# A function that converts string decimal to float decimal
#------------------------------------------------------------------------------------------------------------------
def convert_string_decimal(file_path):
    wind_speed_str = (file_path.split("\\")[2]).split("_")[4].replace("mps","")
    FloatDecimal = float(wind_speed_str.replace("p", "."))
    return FloatDecimal

#------------------------------------------------------------------------------------------------------------------
# A function that gets the simulation length from the file path
#------------------------------------------------------------------------------------------------------------------
def get_simulation_length(file_path):
    duration_str = (file_path.split("\\")[1])
    return duration_str
# Seed numbers, seed labels and durations are defined in fowt_duration/config.py
SeedNoDict = dict(zip(seeds, SeedNoList))

#------------------------------------------------------------------------------------------------------------------
# Edit the TurbSim input file and generate .bts file for the wind files
#------------------------------------------------------------------------------------------------------------------
def COPY_FILES_EXCLUDING_OUT(src_folder, dst_folder):
    # Create destination folder if it doesn't exist
    os.makedirs(dst_folder, exist_ok=True)
    # Copy all files except .out and .chkp files
    for file in os.listdir(src_folder):
        src_path = os.path.join(src_folder, file)
        if os.path.isfile(src_path) and not file.endswith(('.out', '.chkp')):
            shutil.copy2(src_path, os.path.join(dst_folder, file))

    return
#------------------------------------------------------------------------------------------------------------------
# Edit the TurbSim input file and generate .bts file for the wind files
#------------------------------------------------------------------------------------------------------------------
def RUN_TURBSIM_ANALYSIS(VarInput, TurbSimFile):

    # Read a text file contanbing all the environmental variables
    wind_speeds = []
    wave_heights = []
    wave_periods = []
    with open(VarInput, 'r', encoding="utf8") as file:
        lines = file.readlines()
        for line in lines[2:]:  # Skip the header line and units
            wind_speed = float(line.split()[0])  # Convert to float
            wind_speeds.append(wind_speed)

            # wave_height = float(line.split()[1])
            # wave_heights.append(wave_height)

            # wave_period = float(line.split()[2])
            # wave_periods.append(wave_period)

    # Write the path of the files or location using turbsim input file location
    PathSplit = TurbSimFile.split('\\')
    FilePath = '\\'.join(PathSplit[0:-1])

    # Read the TurbSim input file content
    with open(TurbSimFile, 'r') as file:
        turb_sim_lines = file.readlines()

    for j in range(len(SeedNoList)):
        for sim in SimTimeList:
            
            for i in range(len(wind_speeds)):

                # Update the TurbSim input file content with new environmental variables
                turb_sim_lines[4]  = f'{SeedNoList[j]}        RandSeed1       - First random seed  (-2147483648 to 2147483647)\n'
                turb_sim_lines[21] = f'{sim}      AnalysisTime    - Length of analysis time series [seconds] (program will add time if necessary: AnalysisTime = MAX(AnalysisTime, UsableTime+GridWidth/MeanHHWS) )\n'
                turb_sim_lines[39] = f'{wind_speeds[i]}      URef            - Mean (total) velocity at the reference height [m/s] (or "default" for JET velocity profile) [must be 1-hr mean for API model; otherwise is the mean over AnalysisTime seconds]\n'

                # Write the modified content back to the TurbSim input file
                with open(TurbSimFile, 'w') as file:
                    file.writelines(turb_sim_lines)

                # Run the TurbSim file to generate .bts
                os.system(f'"{FilePath}\\Run_TurbSim.bat"')
                # os.system( str(FilePath) + "\\Run_TurbSim.bat")

                # Rename the output files to the wind file analysis
                os.rename(FilePath + '\\TurbSim.bts', FilePath + '\\TurbSim_' + str(OutPutMod(wind_speeds,i))+'mps_'+str(sim)+'s_'+str(get_keys_from_value(SeedNoDict, SeedNoList[j]))+'.bts')
                os.rename(FilePath + '\\TurbSim.dat', FilePath + '\\TurbSim_' + str(OutPutMod(wind_speeds,i))+'mps_'+str(sim)+'s_'+str(get_keys_from_value(SeedNoDict, SeedNoList[j]))+'.dat')
                os.rename(FilePath + '\\TurbSim.sum', FilePath + '\\TurbSim_' + str(OutPutMod(wind_speeds,i))+'mps_'+str(sim)+'s_'+str(get_keys_from_value(SeedNoDict, SeedNoList[j]))+'.sum')


    return


#------------------------------------------------------------------------------------------------------------------
# A function that reads a Basecase models and writes case models with .dat extension for wave only
#------------------------------------------------------------------------------------------------------------------
def RUN_OPENFAST_ANALYSIS(VarInput, FastFile, InfloFile, SeaStateFile, BaseFolder):
 
    # Read a text file contanbing all the environmental variables for modifying basecase model
    wind_speeds = []
    wave_heights = []
    wave_periods = []
    with open(VarInput, 'r', encoding="utf8") as file:
        lines = file.readlines()
        for line in lines[2:]:  # Skip the header line and units
            wind_speed = float(line.split()[0])  # Convert to float
            wind_speeds.append(wind_speed)

            wave_height = float(line.split()[1])
            wave_heights.append(wave_height)

            wave_period = float(line.split()[2])
            wave_periods.append(wave_period)

    
    src_folder = BaseFolder
 
    for sim in SimTimeList:

            # dst_folder = src_folder.replace('00BaseFolder', f'{sim}s')

            # Write the path of the files or location
            PathSplit = BaseFolder.split('\\')
            dst_folder = '\\'.join(PathSplit[0:-1])+'\\'+str(sim)+'s'

            COPY_FILES_EXCLUDING_OUT(src_folder, dst_folder)

            start_time = time.time()
            # Read the Fast input file content
            with open(dst_folder + '\\' + FastFile, 'r') as file:
                fast_lines = file.readlines()

            fast_lines[5]  = f'         {sim}   TMax            - Total run time (s)\n'

            # Write the modified content back to the Fast input file
            with open(dst_folder + '\\' + FastFile, 'w') as file:
                file.writelines(fast_lines)
#-------------------------------------------------------------------------------------------------------------------------------------------------

            for i in range(len(SeedNoList)):

                for j in range(len(wind_speeds)):

                    # Read the Fast input file content
                    with open(dst_folder + '\\' + InfloFile, 'r') as file:
                        InflowData_Lines = file.readlines()
                    # Replace the value of HWindSpeed on line 14 with the wind speed value in the Inflow file, set analysis type to turbulent i.e 3 and set location to TurbSim bts turbulent file
                    InflowData_Lines[13] = f'       {wind_speeds[j]}   HWindSpeed     - Horizontal wind speed                   (m/s)\n'
                    # InflowData_Lines[4]  = f'          3   WindType       - switch for wind file type (1=steady; 2=uniform; 3=binary TurbSim FF; 4=binary Bladed-style FF; 5=HAWC format; 6=User defined; 7=native Bladed FF)\n'
                    InflowData_Lines[21] = f'"..\\..\\01EnviroData\\TurbSim_{str(OutPutMod(wind_speeds,j))}mps_{str(sim)}s_{str(get_keys_from_value(SeedNoDict, SeedNoList[i]))}.bts"  FileName_BTS      - Name of the Full field wind file to use (.bts)\n'
                    
                    # Write the modified content back to the Inflow input data file
                    with open(dst_folder + '\\' + InfloFile, 'w') as file:
                        file.writelines(InflowData_Lines)
#-------------------------------------------------------------------------------------------------------------------------------------------------
                    
                    # Read the Fast input file content
                    with open(dst_folder + '\\' + SeaStateFile, 'r') as file:
                        seastate_lines = file.readlines()

                    seastate_lines[18] = f'           {sim}   WaveTMax       - Analysis time for incident wave calculations (sec) [unused when WaveMod=0; determines WaveDOmega=2Pi/WaveTMax in the IFFT]\n'
                    seastate_lines[20] = f'         {wave_heights[j]}   WaveHs         - Significant wave height of incident waves (meters) [used only when WaveMod=1, 2, or 3]\n'
                    seastate_lines[21] = f'         {wave_periods[j]}   WaveTp         - Peak-spectral period of incident waves       (sec) [used only when WaveMod=1 or 2]\n'
                    seastate_lines[30] = f'       {SeedNoList[i]}   WaveSeed(1)    - First  random seed of incident waves [-2147483648 to 2147483647]    (-)       [unused when WaveMod=0, 5, or 6]\n'

                    if sim >= 3600 and sim <10800:
                        seastate_lines[19] = f'           0.1   WaveDT         - Time step for incident wave calculations     (sec) [unused when WaveMod=0 or 7; 0.1<=WaveDT<=1.0 recommended; determines WaveOmegaMax=Pi/WaveDT in the IFFT]\n'
                    elif sim >= 10800 and sim <18000:
                        seastate_lines[19] = f'          0.15   WaveDT         - Time step for incident wave calculations     (sec) [unused when WaveMod=0 or 7; 0.1<=WaveDT<=1.0 recommended; determines WaveOmegaMax=Pi/WaveDT in the IFFT]\n'
                    else:
                        seastate_lines[19] = f'          0.25   WaveDT         - Time step for incident wave calculations     (sec) [unused when WaveMod=0 or 7; 0.1<=WaveDT<=1.0 recommended; determines WaveOmegaMax=Pi/WaveDT in the IFFT]\n'

                    # Write the modified content back to the Inflow input data file
                    with open(dst_folder + '\\' + SeaStateFile, 'w') as file:
                        file.writelines(seastate_lines)

                    # Run the OpenFast file to generate .out and .chkp files
                    os.system(f'"{dst_folder}\\Run_OpenFast.bat"')
                    # os.system( str(dst_folder) + "\\Run_OpenFast.bat")

                    # Rename the output files to the wind file analysis
                    os.rename(dst_folder + '\\5MW_OC4Semi_WSt_WavesWN.out', dst_folder + '\\5MW_OC4Semi_WSt_WavesWN_' + str(OutPutMod(wind_speeds,j))+'mps_'+str(sim)+'s_'+str(get_keys_from_value(SeedNoDict, SeedNoList[i]))+'.OUT')
                    end_time = time.time()
                    print(f"Simulation for {sim}s and wind speed of {wind_speeds[j]} completed in {round((end_time - start_time)/60/60, 3)} hours.")

    return


def average_openfast_outputs(SimTime, WindSpeed, SeedNo=5):
    """
    Point-by-point (time-synchronous) average of OpenFAST .out files from different seeds.

    NOTE: the seeds are statistically independent realisations with random wind/wave phases,
    so averaging at the same time instant cancels the stochastic part of the response
    (variance drops by roughly 1/nSeeds). Extremes and DELs taken from this averaged series
    are therefore non-conservative. Use write_seed_aggregated_statistics() for loads.

    Parameters
    ----------
    SimTime : int
        Simulation length (s), e.g. 600
    WindSpeed : float
        Mean hub-height wind speed (m/s)
    SeedNo : int
        Number of seeds to average
    """

    file_list = []


    for j in range(SeedNo):
        # file_list.append(os.getcwd() + f'\\{SimTime}s\\5MW_OC4Semi_WSt_WavesWN_' + str(OutPutModV2(WindSpeed))+'mps_'+str(SimTime)+'s_Seed'+str(j+1)+'.OUT')
        file_list.append(f'DLC1p1\\{SimTime}s\\5MW_OC4Semi_WSt_WavesWN_{str(OutPutModV2(WindSpeed))}mps_{SimTime}s_Seed{j+1}.OUT')
        #file_list.append(f'{file[:-4]}{str(OutPutMod(wind_speeds,SimTIme))}_Seed{j+1}.OUT')


    headers = []
    units = []
    data_all = []

    for i, fname in enumerate(file_list):
        with open(fname, 'r', encoding="utf8") as f:
            lines = f.readlines()

        # OpenFAST ASCII format:
        # - Header line with channel names
        # - Units line
        # - Numerical data starts after that
        header_line = None
        unit_line = None
        data_start = None

        for idx, line in enumerate(lines):
            if 'Time' in line and header_line is None:
                header_line = idx
                unit_line = idx + 1
                data_start = idx + 2
                break

        if header_line is None:
            raise RuntimeError(f"Could not find header in {fname}")

        if i == 0:
            headers = lines[header_line]
            units = lines[unit_line]

        data = np.loadtxt(lines[data_start:])
        data_all.append(data)

    # Stack and average across seeds
    data_all = np.stack(data_all, axis=0)  # shape: (nSeeds, nSteps, nChannels)
    data_avg = np.mean(data_all, axis=0)

    output_file = f'DLC1p1\\{SimTime}s\\5MW_OC4Semi_WSt_WavesWN_{str(OutPutModV2(WindSpeed))}mps_{SimTime}s.OUT'

    # Write averaged output
    with open(output_file, 'w') as f:
        f.write(headers)
        f.write(units)
        np.savetxt(f, data_avg, fmt='%14.6e')

    print(f"Averaged file written to: {output_file}")


#------------------------------------------------------------------------------------------------------------------
# Helpers for seed-wise post-processing
#------------------------------------------------------------------------------------------------------------------
def get_seed_files(folder_path, wind_speed=None):
    """Return {(wind_speed, seed): file} for all '*_Seed*.OUT' files in a folder (MoorDyn files excluded)."""
    pattern = '*Seed*.OUT' if wind_speed is None else f'*_{OutPutModV2(wind_speed)}mps_*Seed*.OUT'
    seed_files = {}
    for f in glob.glob(os.path.join(folder_path, pattern)):
        match = re.search(r'_(\d+p\d+)mps_\d+s_Seed(\d+)\.OUT$', os.path.basename(f), re.IGNORECASE)
        if match is None or 'MD' in os.path.basename(f):
            continue
        ws = float(match.group(1).replace('p', '.'))
        seed_files[(ws, int(match.group(2)))] = f
    return dict(sorted(seed_files.items()))

def split_channel_name(column):
    """'RootFxc1_[kN]' -> ('RootFxc1', '(kN)')"""
    match = re.match(r'^(.*)_\[(.*)\]$', column)
    if match is None:
        return column, 'N/A'
    return match.group(1), f'({match.group(2)})'

def gumbel_pooled_extreme(seed_extremes):
    """
    Fit a Gumbel distribution (method of moments) to the per-seed maxima and return the
    expected maximum over the pooled exposure of all seeds (nSeeds x simulation length):
        beta = s*sqrt(6)/pi,  E[max over n periods] = mean + beta*ln(n)
    """
    x = np.asarray(seed_extremes, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) < 2:
        return np.nan
    beta = np.std(x, ddof=1) * np.sqrt(6) / np.pi
    return np.mean(x) + beta * np.log(len(x))


#------------------------------------------------------------------------------------------------------------------
# Seed aggregation of ultimate and fatigue loads (phase-independent)
#------------------------------------------------------------------------------------------------------------------
def write_seed_aggregated_statistics(folder_path, skip=200, m_values=(3, 4, 8, 10), extreme_method='mean'):
    """
    Compute extremes and DELs on each seed separately, then aggregate across seeds.
    This replaces post-processing of the time-synchronous seed-averaged file, which
    removes the random-phase content of the response.

    Ultimate loads (per wind speed, per channel):
        'mean'   : mean of the seed maxima/minima (IEC 61400-1 / 61400-3 practice)
        'max'    : largest seed maximum (smallest seed minimum)
        'gumbel' : Gumbel fit to the seed extremes, expected extreme over the pooled exposure
    Fatigue loads (per wind speed, per channel, per m):
        DEL_comb = ( sum_i DEL_i^m * T_i / sum_i T_i )^(1/m)
        i.e. damage summed over all seeds, equivalent to rainflow counting the seeds together.

    Files written to folder_path:
        Statistics_Maximum.csv, Statistics_Minimum.csv, DEL_m{m}.csv   (same layout as before,
            so plot_extreme_statistics / plot_normalised_DEL_barchart work unchanged)
        SeedSummary_Maximum.csv, SeedSummary_Minimum.csv, SeedSummary_DEL_m{m}.csv
            (per-seed values, mean, std, CoV, 95% CI of the mean, absolute extreme, Gumbel estimate)

    Parameters:
    - folder_path: str, path to folder containing the *_Seed*.OUT files
    - skip: int, number of seconds to skip from the beginning (default 200s)
    - m_values: Wöhler exponents for the DEL
    - extreme_method: 'mean', 'max' or 'gumbel' (value written to Statistics_*.csv)
    """
    from scipy.stats import t as student_t

    seed_files = get_seed_files(folder_path)
    if not seed_files:
        raise RuntimeError(f"No *_Seed*.OUT files found in {folder_path}")

    wind_speeds = sorted(set(ws for ws, _ in seed_files))
    seeds = sorted(set(seed for _, seed in seed_files))

    # Per-seed results: {quantity: {(ws, seed): {channel: value}}}, quantity = 'max', 'min', 'T', ('DEL', m)
    per_seed = {'max': {}, 'min': {}, 'T': {}}
    for m in m_values:
        per_seed[('DEL', m)] = {}
    channel_units = {}
    channels = []

    for (ws, seed), file in seed_files.items():
        print(f"Processing {os.path.basename(file)}")
        df = FASTOutputFile(file).toDataFrame()
        df = df[df['Time_[s]'] >= skip].reset_index(drop=True)
        time_series = df['Time_[s]'].values

        channels = [col for col in df.columns if col != 'Time_[s]']
        for col in channels:
            channel_units[col] = split_channel_name(col)[1]

        per_seed['max'][(ws, seed)] = df[channels].max().to_dict()
        per_seed['min'][(ws, seed)] = df[channels].min().to_dict()
        per_seed['T'][(ws, seed)] = time_series[-1] - time_series[0]

        for m in m_values:
            per_seed[('DEL', m)][(ws, seed)] = {}
            for col in channels:
                try:
                    Leq = equivalent_load(time_series, df[col].values, m=m, outputMore=False)
                except Exception as e:
                    print(f"Error calculating DEL for {col} at Ws={ws}mps, Seed{seed}, m={m}: {e}")
                    Leq = np.nan
                per_seed[('DEL', m)][(ws, seed)][col] = Leq

    def seed_values(quantity, ws, col):
        return np.array([per_seed[quantity].get((ws, s), {}).get(col, np.nan) for s in seeds], dtype=float)

    def summary_row(ws, col, values, sign):
        valid = values[~np.isnan(values)]
        n = len(valid)
        mean = np.mean(valid) if n > 0 else np.nan
        std = np.std(valid, ddof=1) if n > 1 else np.nan
        ci95 = student_t.ppf(0.975, n - 1) * std / np.sqrt(n) if n > 1 else np.nan
        row = {'Wind Speed': ws, 'Channel': col, 'Unit': channel_units.get(col, 'N/A'), 'nSeeds': n}
        row.update({f'Seed{s}': v for s, v in zip(seeds, values)})
        row.update({'Mean': mean, 'Std': std,
                    'CoV': abs(std / mean) if n > 1 and mean != 0 else np.nan,
                    'CI95_HalfWidth': ci95,
                    'AbsExtreme': sign * np.max(sign * valid) if n > 0 else np.nan,
                    'Gumbel_Pooled': sign * gumbel_pooled_extreme(sign * valid)})
        return row

    method_column = {'mean': 'Mean', 'max': 'AbsExtreme', 'gumbel': 'Gumbel_Pooled'}[extreme_method]

    # ---------------- Ultimate loads ----------------
    for quantity, sign, label in [('max', 1, 'Maximum'), ('min', -1, 'Minimum')]:
        rows = [summary_row(ws, col, seed_values(quantity, ws, col), sign) for ws in wind_speeds for col in channels]
        summary_df = pd.DataFrame(rows)
        summary_file = os.path.join(folder_path, f'SeedSummary_{label}.csv')
        summary_df.to_csv(summary_file, index=False)
        print(f"Seed summary ({label.lower()}) written to: {summary_file}")

        # Same layout as write_output_statistics (plain channel names + units row)
        plain_names = [split_channel_name(col)[0] for col in channels]
        stats_data = {'Wind Speed': wind_speeds}
        for col, name in zip(channels, plain_names):
            stats_data[name] = [summary_df.loc[(summary_df['Wind Speed'] == ws) & (summary_df['Channel'] == col), method_column].iloc[0]
                                for ws in wind_speeds]
        stats_df = pd.DataFrame(stats_data)
        units_row = ['(m/s)'] + [channel_units[col] for col in channels]
        stats_df = pd.concat([pd.DataFrame([units_row], columns=stats_df.columns), stats_df], ignore_index=True)

        stats_file = os.path.join(folder_path, f'Statistics_{label}.csv')
        stats_df.to_csv(stats_file, index=False)
        print(f"{label} values ({extreme_method} of {len(seeds)} seeds) written to: {stats_file}")

    # ---------------- Fatigue loads ----------------
    for m in m_values:
        rows = []
        del_data = {'Wind Speed': wind_speeds}
        for col in channels:
            del_data[col] = []
        for ws in wind_speeds:
            T = np.array([per_seed['T'].get((ws, s), np.nan) for s in seeds], dtype=float)
            for col in channels:
                dels = seed_values(('DEL', m), ws, col)
                valid = ~np.isnan(dels) & ~np.isnan(T)
                del_comb = (np.sum(dels[valid]**m * T[valid]) / np.sum(T[valid]))**(1 / m) if valid.any() else np.nan
                del_data[col].append(del_comb)

                row = summary_row(ws, col, dels, 1)
                row.pop('AbsExtreme'); row.pop('Gumbel_Pooled')
                row['DEL_Combined'] = del_comb
                rows.append(row)

        summary_file = os.path.join(folder_path, f'SeedSummary_DEL_m{m}.csv')
        pd.DataFrame(rows).to_csv(summary_file, index=False)

        del_df = pd.DataFrame(del_data)
        units_row = ['(m/s)'] + [channel_units[col] for col in channels]
        del_df = pd.concat([pd.DataFrame([units_row], columns=del_df.columns), del_df], ignore_index=True)

        output_file = os.path.join(folder_path, f'DEL_m{m}.csv')
        del_df.to_csv(output_file, index=False)
        print(f"Combined DEL (m={m}, {len(seeds)} seeds) written to: {output_file}")

    return


#------------------------------------------------------------------------------------------------------------------
# Phase-independent ensemble average in the frequency domain
#------------------------------------------------------------------------------------------------------------------
def plot_seed_ensemble_psd(folder_path, wind_speed, channel_name, skip=200, segment_length=600, f_max=0.5):
    """
    Welch PSD of each seed, averaged across seeds. Averaging the spectra (not the time series)
    keeps the energy of every realisation regardless of phase. If the time-synchronous averaged
    file exists, its PSD is overlaid to show the energy lost by averaging in the time domain.

    Parameters:
    - folder_path: str, e.g. 'DLC1p1\\3600s\\'
    - wind_speed: float, m/s
    - channel_name: str, e.g. 'TwrBsMyt'
    - skip: int, transient to remove (s)
    - segment_length: float, Welch segment length (s), sets frequency resolution 1/segment_length
    - f_max: float, upper frequency of the plot (Hz)
    """
    from scipy.signal import welch

    seed_files = get_seed_files(folder_path, wind_speed)
    if not seed_files:
        raise RuntimeError(f"No seed files for {wind_speed} m/s in {folder_path}")

    def channel_psd(file):
        df = FASTOutputFile(file).toDataFrame()
        df = df[df['Time_[s]'] >= skip].reset_index(drop=True)
        col = next(c for c in df.columns if split_channel_name(c)[0] == channel_name)
        dt = df['Time_[s]'].iloc[1] - df['Time_[s]'].iloc[0]
        nperseg = min(int(segment_length / dt), len(df))
        f, Pxx = welch(df[col].values - df[col].mean(), fs=1 / dt, nperseg=nperseg)
        return f, Pxx, split_channel_name(col)[1]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    psds = []
    for (ws, seed), file in seed_files.items():
        f, Pxx, unit = channel_psd(file)
        psds.append(Pxx)
        ax.semilogy(f, Pxx, color='0.7', lw=0.6, label='Individual seeds' if len(psds) == 1 else None)

    psd_mean = np.mean(psds, axis=0)
    ax.semilogy(f, psd_mean, color='C0', lw=1.8, label=f'Ensemble-averaged PSD ({len(psds)} seeds)')

    sim_time = re.search(r'(\d+)s', os.path.normpath(folder_path).split(os.sep)[-1]).group(1)
    averaged_file = os.path.join(folder_path, f'5MW_OC4Semi_WSt_WavesWN_{OutPutModV2(wind_speed)}mps_{sim_time}s.OUT')
    if os.path.exists(averaged_file):
        f_avg, Pxx_avg, _ = channel_psd(averaged_file)
        ax.semilogy(f_avg, Pxx_avg, color='C3', lw=1.2, ls='--', label='PSD of time-averaged series')
        print(f"{channel_name} @ {wind_speed} m/s: variance of time-averaged series = "
              f"{100 * np.trapz(Pxx_avg, f_avg) / np.trapz(psd_mean, f):.1f}% of ensemble variance")

    ax.set_xlim(0, f_max)
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel(f'PSD {unit[:-1]}$^2$/Hz)')
    ax.set_title(f'{channel_name}, {wind_speed} m/s, {sim_time}s')
    ax.grid(True, which='both', alpha=0.3)
    ax.legend()
    plt.tight_layout()
    plt.show()

    return f, psd_mean


#------------------------------------------------------------------------------------------------------------------
# Phase-locked (rotor azimuth) ensemble average
#------------------------------------------------------------------------------------------------------------------
def azimuth_binned_average(folder_path, wind_speed, channel_name, skip=200, n_bins=72, plot=True):
    """
    Phase-locked average of a rotating-frame channel: samples from all seeds are binned by rotor
    azimuth and averaged per bin. Because the azimuth is a common phase reference across seeds,
    this isolates the deterministic 1P/nP content (gravity, shear, tower shadow) without the
    random-phase cancellation of time-synchronous averaging. The per-bin std gives the stochastic part.

    Returns a DataFrame with Azimuth bin centre, mean, std and per-seed bin means.
    """
    seed_files = get_seed_files(folder_path, wind_speed)
    if not seed_files:
        raise RuntimeError(f"No seed files for {wind_speed} m/s in {folder_path}")

    edges = np.linspace(0, 360, n_bins + 1)
    centres = 0.5 * (edges[:-1] + edges[1:])
    result = pd.DataFrame({'Azimuth (deg)': centres})
    all_values, all_bins = [], []

    for (ws, seed), file in seed_files.items():
        df = FASTOutputFile(file).toDataFrame()
        df = df[df['Time_[s]'] >= skip].reset_index(drop=True)
        col = next(c for c in df.columns if split_channel_name(c)[0] == channel_name)
        unit = split_channel_name(col)[1]

        bins = np.clip(np.digitize(np.mod(df['Azimuth_[deg]'].values, 360), edges) - 1, 0, n_bins - 1)
        values = df[col].values
        result[f'Seed{seed}'] = [values[bins == b].mean() if np.any(bins == b) else np.nan for b in range(n_bins)]
        all_values.append(values)
        all_bins.append(bins)

    all_values = np.concatenate(all_values)
    all_bins = np.concatenate(all_bins)
    result['Mean'] = [all_values[all_bins == b].mean() for b in range(n_bins)]
    result['Std'] = [all_values[all_bins == b].std() for b in range(n_bins)]

    if plot:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        for col in [c for c in result.columns if c.startswith('Seed')]:
            ax.plot(centres, result[col], color='0.7', lw=0.8)
        ax.fill_between(centres, result['Mean'] - result['Std'], result['Mean'] + result['Std'],
                        color='C0', alpha=0.2, label='±1 std (all seeds)')
        ax.plot(centres, result['Mean'], color='C0', lw=1.8, label=f'Azimuth-binned mean ({len(seed_files)} seeds)')
        ax.set_xlim(0, 360)
        ax.set_xlabel('Rotor azimuth (deg)')
        ax.set_ylabel(f'{channel_name} {unit}')
        ax.set_title(f'{channel_name}, {wind_speed} m/s')
        ax.grid(True, alpha=0.3)
        ax.legend()
        plt.tight_layout()
        plt.show()

    return result


def write_output_statistics(folder_path, skip=200):
    """
    Read all OpenFAST output files in a folder and write statistics.
    
    Parameters:
    - folder_path: str, path to folder containing .OUT files
    - skip: int, number of seconds to skip from the beginning (default 200s)
    """
    
    output_folder = folder_path
    
    output_files = get_output_files(folder_path)
    
    # Extract unique wind speeds from files
    wind_speeds = sorted(list(set([convert_string_decimal(file) for file in output_files])))
    
    # Dictionary to store statistics: {wind_speed: {channel: {max, min}}}
    stats = {ws: {} for ws in wind_speeds}
    
    # Dictionary to store units from file headers
    channel_units = {}
    
    # Read all files and extract statistics
    for file in output_files:
        wind_speed = convert_string_decimal(file)
        
        df = pd.read_csv(file, comment='#', low_memory=False)
        
        # Extract units from header (second line after columns)
        with open(file, 'r') as f:
            lines = f.readlines()
            # Find header lines with units
            for i, line in enumerate(lines):
                if 'Time' in line and i+1 < len(lines):
                    units_line = lines[i+1]
                    units_list = units_line.split()
                    col_names = df.columns
                    for j, col in enumerate(col_names):
                        if j < len(units_list):
                            channel_units[col] = units_list[j]
                    break
        
        df = df.apply(pd.to_numeric, errors='coerce')
        
        # Skip transient response by filtering based on Time column
        time_col = df.iloc[:, 0]  # First column is Time
        df = df[time_col >= skip].reset_index(drop=True)
        
        # Get all channels except Time (first column)
        channels = df.columns[1:]
        
        for channel in channels:
            data = df[channel].dropna()
            if len(data) > 0:
                stats[wind_speed][channel] = {
                    'max': data.max(),
                    'min': data.min()
                }
    
    # Get all unique channels
    all_channels = set()
    for ws_stats in stats.values():
        all_channels.update(ws_stats.keys())
    all_channels = sorted(list(all_channels))
    
    # Write maximum values file
    max_data = {'Wind Speed': wind_speeds}
    for channel in all_channels:
        max_data[channel] = [stats[ws].get(channel, {}).get('max', np.nan) for ws in wind_speeds]
    
    max_df = pd.DataFrame(max_data)
    
    # Insert channel names and units rows
    units_row = ['(m/s)'] + [channel_units.get(ch, 'N/A') for ch in all_channels]
    
    max_df = pd.concat([
        pd.DataFrame([units_row], columns=max_df.columns),
        max_df
    ], ignore_index=True)
    
    max_file = os.path.join(output_folder, 'Statistics_Maximum.csv')
    max_df.to_csv(max_file, index=False)
    print(f"Maximum values written to: {max_file}")
    
    # Write minimum values file
    min_data = {'Wind Speed': wind_speeds}
    for channel in all_channels:
        min_data[channel] = [stats[ws].get(channel, {}).get('min', np.nan) for ws in wind_speeds]
    
    min_df = pd.DataFrame(min_data)
    
    # Insert channel names and units rows
    min_df = pd.concat([
        pd.DataFrame([units_row], columns=min_df.columns),
        min_df
    ], ignore_index=True)
    
    min_file = os.path.join(output_folder, 'Statistics_Minimum.csv')
    min_df.to_csv(min_file, index=False)
    print(f"Minimum values written to: {min_file}")

    return


def plot_extreme_statistics(folder_paths, channel_name):
    """
    Plot extreme statistics vs wind speed for all simulation durations on two subplots:
    1. Line plot with max/min for each duration
    2. Grouped bar chart of maximum values by wind speed and duration
    
    Parameters:
    - folder_paths: dict with duration as key and folder path as value
    - channel_name: str, the channel to extract from statistics CSV files
    """
    Legend_FontSize = 10
    Axis_FontSize = 9.5
    Ticks_FontSize = 8
    
    # Color map for different durations
    colors = cm.viridis(np.linspace(0.15, 0.9, len(folder_paths)))
    
    fig, axes = plt.subplots(1, 2, figsize=(7, 1.65))

    # Storage for grouped bar chart data
    all_data = {}  # {wind_speed: {duration: max_value}}
    durations_list = list(folder_paths.keys())
    
    # Process each simulation duration
    for idx, (duration, folder_path) in enumerate(folder_paths.items()):
        data_wind_speed = []
        data_ymax = []
        data_ymin = []
        
        # Read statistics files
        max_file = os.path.join(folder_path, 'Statistics_Maximum.csv')
        min_file = os.path.join(folder_path, 'Statistics_Minimum.csv')
        
        if not os.path.exists(max_file) or not os.path.exists(min_file):
            print(f"Warning: Statistics files not found in {folder_path}")
            continue
        
        # Read max and min statistics
        max_df = pd.read_csv(max_file)
        min_df = pd.read_csv(min_file)

        # Get channel unit from the first row of max_df
        channel_unit = max_df[channel_name].iloc[0] if channel_name in max_df.columns else "N/A"

        # Skip the units row (first row after header)
        max_df = max_df.iloc[1:].reset_index(drop=True)
        min_df = min_df.iloc[1:].reset_index(drop=True)
        
        # Convert to numeric
        max_df = max_df.apply(pd.to_numeric, errors='coerce')
        min_df = min_df.apply(pd.to_numeric, errors='coerce')
        
        # Extract wind speeds and channel data
        wind_speeds = max_df['Wind Speed'].values
        
        if channel_name not in max_df.columns:
            raise ValueError(f"Channel '{channel_name}' not found in statistics file.")
        
        max_values = max_df[channel_name].dropna().values
        min_values = min_df[channel_name].dropna().values
        
        # Ensure same length
        min_len = min(len(wind_speeds), len(max_values), len(min_values))
        wind_speeds = wind_speeds[:min_len]
        max_values = max_values[:min_len]
        min_values = min_values[:min_len]
        
        data_wind_speed = wind_speeds
        data_ymax = max_values
        data_ymin = min_values
        
        # Sort by wind speed
        sorted_indices = np.argsort(data_wind_speed)
        data_wind_speed_sorted = np.array(data_wind_speed)[sorted_indices]
        data_ymax_sorted = np.array(data_ymax)[sorted_indices]
        data_ymin_sorted = np.array(data_ymin)[sorted_indices]

        max_y = np.max(data_ymax_sorted)
        min_y = np.min(data_ymin_sorted)
        
        # Plot for this duration on first subplot
        label_duration = duration.strip('\\').strip('s')
        axes[0].plot(data_wind_speed_sorted, data_ymax_sorted, marker='o', linewidth=1.5,
                     color=colors[idx], label=f'{label_duration}s', markersize=6)
        axes[0].plot(data_wind_speed_sorted, data_ymin_sorted, marker='s', linewidth=1.5,
                     color=colors[idx], linestyle='--', markersize=6)
        
        # Store for grouped bar chart
        for ws, max_val in zip(data_wind_speed_sorted, data_ymax_sorted):
            if ws not in all_data:
                all_data[ws] = {}
            all_data[ws][duration] = max_val
    
    # Configure first subplot (line plot)
    axes[0].set_xlabel("Wind Speed (m/s)", fontsize=Axis_FontSize)
    axes[0].set_ylabel(channel_name + " " + channel_unit, fontsize=Axis_FontSize)
    
    axes[0].yaxis.get_offset_text().set_fontsize(Ticks_FontSize)
    # axes[0].set_ylim(min_y*1.2, max_y*1.2)
    
    # === SECOND SUBPLOT: Grouped Bar Chart ===
    wind_speeds_sorted = sorted(all_data.keys())
    bar_width = 0.1
    x_positions = np.arange(len(wind_speeds_sorted))
    
    for duration_idx, duration in enumerate(durations_list):
        max_values = []
        for ws in wind_speeds_sorted:
            if duration in all_data.get(ws, {}):
                max_values.append(all_data[ws][duration])
            else:
                max_values.append(0)
        
        x_pos = x_positions + (duration_idx - len(durations_list)/2 + 0.5) * bar_width
        label_duration = duration.strip('\\').strip('s')
        axes[1].bar(x_pos, max_values, width=bar_width, label=f'{label_duration}s', color=colors[duration_idx], edgecolor='black', linewidth=0.5)
    
    # Configure second subplot (grouped bar chart)
    axes[1].set_xlabel("Wind Speed (m/s)", fontsize=Axis_FontSize)
    axes[1].set_ylabel(f"{channel_name} {channel_unit}", fontsize=Axis_FontSize)
    axes[1].set_xticks(x_positions)
    axes[1].set_xticklabels([f'{ws:.1f}' for ws in wind_speeds_sorted], fontsize=Ticks_FontSize)
    axes[1].tick_params(axis='both', labelsize=Ticks_FontSize, direction='in')
    axes[1].yaxis.set_major_formatter(plt.ScalarFormatter(useMathText=True))
    axes[1].ticklabel_format(axis='y', style='sci', scilimits=(0,0))
    axes[1].yaxis.get_offset_text().set_fontsize(Ticks_FontSize)
    # axes[1].set_ylim(0, max_y*1.2)

    # Create custom legend with duration boxes and line styles
    duration_handles = [plt.Rectangle((0, 0), 1, 1, facecolor=colors[i], edgecolor='black', linewidth=1) 
                        for i in range(len(durations_list))]
    duration_labels = [duration.strip('\\').strip('s') + 's' for duration in durations_list]
    
    max_line = lines.Line2D([], [], color='black', linewidth=1.5, marker='o', markersize=6, label='Max')
    min_line = lines.Line2D([], [], color='black', linewidth=1.5, linestyle='--', marker='s', markersize=6, label='Min')
    
    # legend = plt.legend(
    #     duration_handles + [max_line, min_line],
    #     duration_labels + ['Max', 'Min'],
    #     loc='upper center',
    #     bbox_to_anchor=(0.5, -0.05),
    #     ncol=5,
    #     frameon=True,
    #     edgecolor='black',
    #     fancybox=False,
    #     shadow=False,
    #     fontsize=Legend_FontSize)
    # plt.tight_layout(rect=[0, 0.15, 1, 1])
    plt.tight_layout()

    image_format = 'svg' # e.g .png, .svg, eps, etc.
    image_name = os.path.join(str(OUTPUT_DIR), f'{channel_name}.svg')
    plt.savefig(image_name, format=image_format, dpi=1200)
    # plt.show()
    return


def plot_normalised_heatmap(folder_paths, channel_name):
    """
    Plot heatmap of normalized statistics vs wind speed and duration.
    Values are normalized by the 21600s simulation duration.
    
    Parameters:
    - folder_paths: dict with duration as key and folder path as value
    - channel_name: str, the channel to extract from statistics CSV files
    """
    Axis_FontSize = 9.5
    Ticks_FontSize = 8
    Legend_FontSize = 10
    
    # Storage for heatmap data
    all_data = {}  # {wind_speed: {duration: max_value}}
    durations_list = sorted(list(folder_paths.keys()), key=lambda x: int(x.strip('s')))
    
    # Process each simulation duration
    for duration, folder_path in folder_paths.items():
        # Read statistics files
        max_file = os.path.join(folder_path, 'Statistics_Maximum.csv')
        
        if not os.path.exists(max_file):
            print(f"Warning: Statistics file not found in {folder_path}")
            continue
        
        # Read max statistics
        max_df = pd.read_csv(max_file)

        # Get channel unit from the first row of max_df
        channel_unit = max_df[channel_name].iloc[0] if channel_name in max_df.columns else "N/A"

        # Skip the units row (first row after header)
        max_df = max_df.iloc[1:].reset_index(drop=True)
        
        # Convert to numeric
        max_df = max_df.apply(pd.to_numeric, errors='coerce')
        
        # Extract wind speeds and channel data
        wind_speeds = max_df['Wind Speed'].values
        
        if channel_name not in max_df.columns:
            raise ValueError(f"Channel '{channel_name}' not found in statistics file.")
        
        max_values = max_df[channel_name].dropna().values
        
        # Ensure same length
        min_len = min(len(wind_speeds), len(max_values))
        wind_speeds = wind_speeds[:min_len]
        max_values = max_values[:min_len]
        
        # Store for heatmap
        for ws, max_val in zip(wind_speeds, max_values):
            if ws not in all_data:
                all_data[ws] = {}
            all_data[ws][duration] = max_val
    
    # Get reference values from 21600s
    reference_duration = '21600s'
    reference_data = {}
    for ws in all_data.keys():
        if reference_duration in all_data[ws]:
            reference_data[ws] = all_data[ws][reference_duration]
        else:
            reference_data[ws] = np.nan
    
    # Normalize all values by reference and prepare heatmap data
    wind_speeds_sorted = sorted(all_data.keys())
    heatmap_data = np.zeros((len(wind_speeds_sorted), len(durations_list)))
    
    for i, ws in enumerate(wind_speeds_sorted):
        for j, duration in enumerate(durations_list):
            if duration in all_data[ws] and not np.isnan(reference_data[ws]):
                heatmap_data[i, j] = all_data[ws][duration] / reference_data[ws]
            else:
                heatmap_data[i, j] = np.nan
    
    max_val = np.nanmax(heatmap_data)
    min_val = np.nanmin(heatmap_data)    
    # Create heatmap
    fig, ax = plt.subplots(figsize=(3.75, 2.25))
    
    duration_labels = [d.strip('s') for d in durations_list]
    # Convert to scientific notation (divide by 100)
    duration_numeric = [int(d.strip('s')) / 100 for d in durations_list]
    duration_labels_sci = [f'{d:.0f}' for d in duration_numeric]
    
    im = ax.imshow(heatmap_data, cmap='RdYlGn_r', aspect='auto', vmin=min_val*0.98, vmax=max_val*1.01)
    
    # Set ticks and labels
    ax.set_xticks(np.arange(len(durations_list)))
    ax.set_yticks(np.arange(len(wind_speeds_sorted)))
    ax.set_xticklabels(duration_labels_sci, fontsize=Ticks_FontSize)
    ax.set_yticklabels([f'{ws:.1f}' for ws in wind_speeds_sorted], fontsize=Ticks_FontSize)
    
    # Labels and title
    ax.set_xlabel("Simulation Duration (×10² s)", fontsize=Axis_FontSize)
    ax.set_ylabel("Wind Speed (m/s)", fontsize=Axis_FontSize)
    ax.set_title(f"{channel_name}", fontsize=Axis_FontSize)
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax)
    # cbar.set_label(f"Ratio to 21600s", fontsize=Axis_FontSize)
    cbar.ax.tick_params(labelsize=Ticks_FontSize)
    
    # Add text annotations
    for i in range(len(wind_speeds_sorted)):
        for j in range(len(durations_list)):
            if not np.isnan(heatmap_data[i, j]):
                text = ax.text(j, i, f'{heatmap_data[i, j]:.2f}',
                              ha="center", va="center", color="black", fontsize=7.5)
    
    plt.tight_layout()
    
    image_format = 'svg' # e.g .png, .svg, eps, etc.
    image_name = os.path.join(str(OUTPUT_DIR), f'{channel_name}_heatmap.svg')
    plt.savefig(image_name, format=image_format, dpi=1200)
    
    # plt.show()
    return


def plot_openfast_channel(filename, channel_name):
    import pandas as pd
    import numpy as np
    import os
    import matplotlib.pyplot as plt

    Legend_FontSize = 10
    Axis_FontSize = 9.5
    Ticks_FontSize = 8
    SubPlot_Fontsize = 6
    
    # --- Read file safely ---
    df = pd.read_csv(filename,
                     delim_whitespace=True,
                     comment='#',
                     low_memory=False)

    # Convert all columns to numeric where possible
    df = df.apply(pd.to_numeric, errors='coerce')

    if channel_name not in df.columns:
        raise ValueError(f"Channel '{channel_name}' not found in file.")

    time = df.iloc[:, 0]   # First column is usually Time
    data = df[channel_name].dropna()
    time = time.loc[data.index]

    # --- Statistics ---
    max_val = data.max()
    min_val = data.min()
    mean_val = data.mean()
    std_val = data.std()
    data_range = max_val - min_val

    max_time = time.loc[data.idxmax()]

    xmin = time.min()
    xmax = time.max()

    # --- Print statistics ---
    print(f"\nStatistics for {channel_name}")
    print(f"Maximum : {max_val:.6f}")
    print(f"Minimum : {min_val:.6f}")
    print(f"Range   : {data_range:.6f}")
    print(f"Mean    : {mean_val:.6f}")
    print(f"Std Dev : {std_val:.6f}")

    # --- Plot ---
    plt.figure(figsize=(3.7,1.5))

    # Plot time history
    plt.plot(time, data, label=channel_name, linewidth=1.2, color='green', linestyle='-')

    # Mark mean
    plt.axhline(mean_val, linestyle='--', linewidth=1, color='red', label=f"Mean = {mean_val:.4f}")

    # Mark maximum
    plt.plot(max_time, max_val, 'r*', markersize=8, label=f"Max = {max_val:.4f}")

    # Mark mean
    plt.axvline(max_time, linestyle='--', linewidth=1, color='red', label=f"Max = {max_val:.4f}")

    plt.xlabel("Time (s)", fontsize=Axis_FontSize)
    plt.ylabel(channel_name, fontsize=Axis_FontSize)
    plt.xticks(fontsize=Ticks_FontSize)
    plt.xlim([xmin, xmax])
    plt.tick_params(axis='both', labelsize=Ticks_FontSize, direction='in')
    plt.gca().yaxis.get_offset_text().set_fontsize(Ticks_FontSize)
    # plt.subplots_adjust(left=0.14, right=0.9, top=0.88, bottom=0.35)
    # plt.subplots_adjust(wspace=0.4, hspace=0.4)
    # plt.title(f"OpenFAST Time History: {channel_name}")
    # plt.legend()
    # plt.grid(True)
    plt.tight_layout()

    # filename.split('\\')[1]

    # image_format = 'eps' # e.g .png, .svg, eps, etc.
    # image_name = os.path.join(str(OUTPUT_DIR), f'{channel_name}-{filename.split("\\")[1]}.eps')

    # plt.savefig(image_name, format=image_format, dpi=1200)
    plt.show()

    return max_val, min_val, data_range, mean_val, std_val

def plot_openfast_channel_all_durations(folder_paths, channel_name):
    """
    Plot extreme statistics vs wind speed for all simulation durations on two subplots:
    1. Line plot with max/min for each duration
    2. Grouped bar chart of maximum values by wind speed and duration
    
    Parameters:
    - folder_paths: dict with duration as key and folder path as value
    - channel_name: str, the channel to extract from OpenFAST output
    """
    Legend_FontSize = 10
    Axis_FontSize = 9.5
    Ticks_FontSize = 8
    
    # Color map for different durations
    colors = cm.viridis(np.linspace(0.15, 0.9, len(folder_paths)))
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # Storage for grouped bar chart data
    all_data = {}  # {wind_speed: {duration: max_value}}
    durations_list = list(folder_paths.keys())
    
    # Process each simulation duration
    for idx, (duration, folder_path) in enumerate(folder_paths.items()):
        data_wind_speed = []
        data_ymax = []
        data_ymin = []
        
        output_files = get_output_files(folder_path)
        
        # Collect statistics for all files in this duration
        for file in output_files:
            df = pd.read_csv(file, delim_whitespace=True, comment='#', low_memory=False)
            df = df.apply(pd.to_numeric, errors='coerce')
        
            if channel_name not in df.columns:
                raise ValueError(f"Channel '{channel_name}' not found in file: {file}")
        
            data = df[channel_name].dropna()
            
            # Extract wind speed
            wind_speed = convert_string_decimal(file)
            data_wind_speed.append(wind_speed)
            
            # Statistics
            data_ymax.append(data.max())
            data_ymin.append(data.min())
            
            # Store for grouped bar chart
            if wind_speed not in all_data:
                all_data[wind_speed] = {}
            all_data[wind_speed][duration] = data.max()
        
        # Sort by wind speed
        sorted_indices = np.argsort(data_wind_speed)
        data_wind_speed_sorted = np.array(data_wind_speed)[sorted_indices]
        data_ymax_sorted = np.array(data_ymax)[sorted_indices]
        data_ymin_sorted = np.array(data_ymin)[sorted_indices]
        
        # Plot for this duration on first subplot
        label_duration = duration.replace('s', 's').strip('\\')
        axes[0].plot(data_wind_speed_sorted, data_ymax_sorted, marker='o', linewidth=1.5,
                     color=colors[idx], label=f'Max - {label_duration}', markersize=6)
        axes[0].plot(data_wind_speed_sorted, data_ymin_sorted, marker='s', linewidth=1.5,
                     color=colors[idx], linestyle='--', label=f'Min - {label_duration}', markersize=6)
    
    # Configure first subplot (line plot)
    axes[0].set_xlabel("Wind Speed (m/s)", fontsize=Axis_FontSize)
    axes[0].set_ylabel(channel_name, fontsize=Axis_FontSize)
    axes[0].tick_params(axis='both', labelsize=Ticks_FontSize, direction='in')
    axes[0].legend(fontsize=7.5, loc='best', ncol=2)
    axes[0].grid(True, alpha=0.3)
    axes[0].set_title("Max & Min Values vs Wind Speed", fontsize=Axis_FontSize)
    
    # === SECOND SUBPLOT: Grouped Bar Chart ===
    wind_speeds_sorted = sorted(all_data.keys())
    bar_width = 0.09
    x_positions = np.arange(len(wind_speeds_sorted))
    
    for duration_idx, duration in enumerate(durations_list):
        max_values = []
        for ws in wind_speeds_sorted:
            if duration in all_data[ws]:
                max_values.append(all_data[ws][duration])
            else:
                max_values.append(0)
        
        x_pos = x_positions + (duration_idx - len(durations_list)/2 + 0.5) * bar_width
        axes[1].bar(x_pos, max_values, width=bar_width, label=duration, color=colors[duration_idx])
    
    # Configure second subplot (grouped bar chart)
    axes[1].set_xlabel("Wind Speed (m/s)", fontsize=Axis_FontSize)
    axes[1].set_ylabel(f"Maximum {channel_name}", fontsize=Axis_FontSize)
    axes[1].set_xticks(x_positions)
    axes[1].set_xticklabels([f'{ws:.1f}' for ws in wind_speeds_sorted], fontsize=Ticks_FontSize)
    axes[1].tick_params(axis='both', labelsize=Ticks_FontSize, direction='in')
    axes[1].legend(fontsize=7.5, loc='best', ncol=2, title='Duration')
    axes[1].grid(True, alpha=0.3, axis='y')
    axes[1].set_title("Maximum Values by Wind Speed & Duration", fontsize=Axis_FontSize)
    
    plt.tight_layout()
    plt.show()

    return


def section_properties(diameter, thickness):
    """Calculate cross-sectional area and moment of inertia for a hollow circular section."""
    outer_radius = diameter / 2
    inner_radius = outer_radius - thickness
    area = np.pi * (outer_radius**2 - inner_radius**2)
    moment_of_inertia = (np.pi / 4) * (outer_radius**4 - inner_radius**4)
    return area, moment_of_inertia

linestyles = ['solid','dashed','solid','dashed','solid', 'dashed','solid', 'dashed','solid', 'dashed','solid','dotted','solid']

def plot_channels_force_rose(folder_paths_dict, channel_list, Ax_channel, sect_prop, n_angles, wind_speed):

    Legend_FontSize = 10
    Axis_FontSize = 9.5
    Ticks_FontSize = 8
    SubPlot_Fontsize = 6

    """
    Create radar/rose plots of resultant force vs angle for specified channels.
    
    Parameters:
    - folder_paths_dict: dict, {duration_label: folder_path}
    - channel_list: list of 2 channels [channel1, channel2]
    - n_angles: int, number of angles around the circle
    - wind_speed: float, target wind speed (e.g., 4.0 for 4 m/s)
    """
    Diameter, thickness = sect_prop

    A, Iy = section_properties(Diameter, thickness)
    _, Ix = section_properties(Diameter, thickness)
    if len(channel_list) != 2:
        raise ValueError("channel_list must contain exactly 2 channels")
    
    channel1, channel2 = channel_list
    colors = cm.viridis(np.linspace(0.15, 0.9, len(folder_paths_dict)))
    theta_angles = np.radians(np.arange(0, 360, 360/n_angles))
    
    # Close the loop by appending the first angle at the end
    theta_closed = np.append(theta_angles, theta_angles[0])
    
    fig, axes = plt.subplots(1, 3, figsize=(7, 2), subplot_kw=dict(projection='polar'))
    
    # Second pass: plot with symmetric range
    for duration_idx, (duration, folder_path) in enumerate(folder_paths_dict.items()):
        csv_file = os.path.join(folder_path, f'CorrespondingValues_Ws{wind_speed}mps.csv')
        
        if not os.path.exists(csv_file):
            print(f"File not found: {csv_file}")
            continue
        
        df = pd.read_csv(csv_file, index_col=0)
        loc = 'center'
        rootname = channel1[0:4]

        scale = 0.60  # Adjust this scale factor as needed for better visualization

            # Axial Case: Only Axial stress
        if channel1 in df.index and channel2 in df.index:
            channel_Ax_corr = max (abs(float(df.loc[Ax_channel, channel1])) , abs(float(df.loc[Ax_channel, channel2])))

            Sig1 = channel_Ax_corr/A/1000 + (0/Iy/1000 * np.cos(theta_angles)) + (0/Ix/1000 * np.sin(theta_angles))
            Sig1_closed = np.append(Sig1, Sig1[0])

            axes[0].plot(theta_closed, [abs(scale*val) for val in Sig1_closed], linewidth=1.5, linestyle=linestyles[duration_idx], color=colors[duration_idx], label=duration.strip('\\').strip('s') + 's')
            axes[0].set_title(f'{rootname}$\\sigma_{{AX}}$ (MPa) at {int(wind_speed)}m/s', loc =loc, fontsize=Axis_FontSize)
            axes[0].set_theta_zero_location('E')
            axes[0].set_theta_direction(1)
            axes[0].set_ylim(-max(Sig1), max(Sig1))
            axes[0].set_yticks([-max(Sig1), 0, max(Sig1)])
            axes[0].set_yticklabels([f'{int(-max(Sig1))}', '0', f'{int(max(Sig1))}'], fontsize=Axis_FontSize-1.5)
            axes[0].set_yticklabels([f'{round(-max(Sig1), 1)}', '0', f'{round(max(Sig1), 1)}'], fontsize=Axis_FontSize-1.5)
            axes[0].set_xticks(np.radians(np.arange(0, 360, 30)))  # Set x-ticks at 30-degree increments
            axes[0].set_xticklabels([f"{int(angle)}°" for angle in np.arange(0, 360, 30)], fontsize=Axis_FontSize-1.5)
            axes[0].grid(True, alpha=0.3)

            # Case 1: channel1 as leading value
        if channel1 in df.index and channel2 in df.index:
            channel1_max  = float(df.loc[channel1,  channel1])
            channel2_corr = float(df.loc[channel2,  channel1])
            channel_Ax_corr = float(df.loc[Ax_channel, channel1])

            Sig1 = channel_Ax_corr/A/1000 + (channel2_corr/Iy/1000 * np.cos(theta_angles)) + (channel1_max/Ix/1000 * np.sin(theta_angles))
            Sig1_closed = np.append(Sig1, Sig1[0])

            axes[1].plot(theta_closed, [abs(scale*val) for val in Sig1_closed], linewidth=1.5, linestyle=linestyles[duration_idx], color=colors[duration_idx], label=duration.strip('\\').strip('s') + 's')
            axes[1].set_title(f'{rootname}$\\sigma_{{N1}}$ (MPa) at {int(wind_speed)}m/s', loc =loc, fontsize=Axis_FontSize)
            axes[1].set_theta_zero_location('E')
            axes[1].set_theta_direction(1)
            # axes[1].set_ylim(-max(Sig1), max(Sig1))
            # axes[1].set_yticks([-max(Sig1), 0, max(Sig1)])
            # axes[1].set_yticklabels([f'{int(-(max(Sig1)))}', '0', f'{int(max(Sig1))}'], fontsize=Axis_FontSize-1.5)
            # axes[1].set_yticklabels([f'{round(-max(Sig1), 1)}', '0', f'{round(max(Sig1), 1)}'], fontsize=Axis_FontSize-1.5)
            axes[1].set_xticks(np.radians(np.arange(0, 360, 30)))  # Set x-ticks at 30-degree increments
            axes[1].set_xticklabels([f"{int(angle)}°" for angle in np.arange(0, 360, 30)], fontsize=Axis_FontSize-1.5)
            axes[1].grid(True, alpha=0.3)
        
        # Case 2: channel2 as leading value
        if channel2 in df.index and channel1 in df.index:
            channel2_max = float(df.loc[channel2, channel2])
            channel1_corr = float(df.loc[channel1, channel2])
            channel_Ax_corr = float(df.loc[Ax_channel, channel2])

            Sig2 = channel_Ax_corr/A/1000  + (channel2_max/Ix/1000 * np.cos(theta_angles)) + (channel1_corr/Iy/1000 * np.sin(theta_angles))
            Sig2_closed = np.append(Sig2, Sig2[0])

            axes[2].plot(theta_closed, [abs(scale*val) for val in Sig2_closed], linewidth=1.5, linestyle=linestyles[duration_idx], color=colors[duration_idx], label=duration.strip('\\').strip('s') + 's')
            axes[2].set_title(f'{rootname}$\\sigma_{{N2}}$ (MPa) at {int(wind_speed)}m/s', loc =loc, fontsize=Axis_FontSize)
            axes[2].set_theta_zero_location('E')
            axes[2].set_theta_direction(1)
            # axes[2].set_ylim(-max(Sig2), max(Sig2))
            # axes[2].set_yticks([-max(Sig2), 0, max(Sig2)])
            # axes[2].set_yticklabels([f'{int(-(max(Sig2)))}', '0', f'{int(max(Sig2))}'], fontsize=Axis_FontSize-1.5)
            # axes[2].set_yticklabels([f'{round(-max(Sig2), 1)}', '0', f'{round(max(Sig2), 1)}'], fontsize=Axis_FontSize-1.5)
            axes[2].set_xticks(np.radians(np.arange(0, 360, 30)))  # Set x-ticks at 30-degree increments
            axes[2].set_xticklabels([f"{int(angle)}°" for angle in np.arange(0, 360, 30)], fontsize=Axis_FontSize-1.5)
            axes[2].grid(True, alpha=0.3)

    # Create legend labels
    labels = [duration.split('\\')[-1].strip('\\').strip('s') + 's' for duration in folder_paths_dict.keys()]
    handles = [plt.Line2D([0], [0], marker='s', color='w', markerfacecolor=colors[i], 
                         markersize=8, linewidth=2) for i in range(len(folder_paths_dict))]
    
    # fig.legend(folder_paths_all_dict, loc='upper center', ncol=len(folder_paths_all_dict)/2, 
    #            fontsize = Legend_FontSize, handlelength = 3, frameon=True, edgecolor='black',
    #            fancybox=False, shadow=False)
    
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.15)
    image_format = 'svg' # e.g .png, .svg, eps, etc.
    image_name = os.path.join(str(OUTPUT_DIR), f'{rootname}_{int(wind_speed)}mps.svg')
    plt.savefig(image_name, format=image_format, dpi=1200)
    # plt.show()


def write_damage_equivalent_load(folder_path, skip=200):
    """
    Read all OpenFAST output files in a folder and calculate Damage Equivalent Load (DEL)
    for all channels across different Wöhler exponents (m=3, 4, 8, 10).
    
    Parameters:
    - folder_path: str, path to folder containing .OUT files
    - skip: int, number of seconds to skip from the beginning (default 200s)
    """
    
    output_files = get_output_files(folder_path)
    
    # Extract unique wind speeds from files
    wind_speeds = sorted(list(set([convert_string_decimal(file) for file in output_files])))
    
    # Wöhler exponents to calculate
    m_values = [3, 4, 8, 10]
    
    # Dictionary to store DEL values: {m: {wind_speed: {channel: Leq_value}}}
    del_data = {m: {ws: {} for ws in wind_speeds} for m in m_values}
    
    # Dictionary to store units from file headers
    channel_units = {}
    
    # Read all files and calculate DEL
    for file in output_files:
        wind_speed = convert_string_decimal(file)
        
        # Read OpenFAST output file
        df = FASTOutputFile(file).toDataFrame()
        
        # Extract units from original file header
        with open(file, 'r') as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                if 'Time' in line and i+1 < len(lines):
                    units_line = lines[i+1]
                    units_list = units_line.split()
                    col_names = lines[0].split()
                    for j, col in enumerate(col_names):
                        if j < len(units_list):
                            channel_units[col] = units_list[j]
                    break
        
        # Skip transient response
        time_col = df['Time_[s]']
        df_filtered = df[time_col >= skip].reset_index(drop=True)
        
        # Get all channels except Time
        channels = [col for col in df_filtered.columns if col != 'Time_[s]']
        
        # Calculate DEL for each channel and each m value
        for channel in channels:
            load_series = df_filtered[channel].dropna()
            time_series = df_filtered['Time_[s]'].iloc[:len(load_series)].reset_index(drop=True)
            
            if len(load_series) > 0:
                for m in m_values:
                    try:
                        Leq = equivalent_load(time_series.values, load_series.values, m=m, outputMore=False)
                        del_data[m][wind_speed][channel] = Leq
                    except Exception as e:
                        print(f"Error calculating DEL for {channel} at Ws={wind_speed}mps, m={m}: {e}")
                        del_data[m][wind_speed][channel] = np.nan
    
    # Get all unique channels
    all_channels = set()
    for ws_dels in del_data[m_values[0]].values():
        all_channels.update(ws_dels.keys())
    all_channels = sorted(list(all_channels))
    
    # Write output files for each m value
    for m in m_values:
        del_output_data = {'Wind Speed': wind_speeds}
        
        for channel in all_channels:
            del_output_data[channel] = [del_data[m][ws].get(channel, np.nan) for ws in wind_speeds]
        
        del_df = pd.DataFrame(del_output_data)
        
        # Insert units row
        units_row = ['(m/s)'] + [channel_units.get(ch.split('_[')[0], 'N/A') for ch in all_channels]
        
        del_df = pd.concat([
            pd.DataFrame([units_row], columns=del_df.columns),
            del_df
        ], ignore_index=True)
        
        output_file = os.path.join(folder_path, f'DEL_m{m}.csv')
        del_df.to_csv(output_file, index=False)
        print(f"DEL (m={m}) written to: {output_file}")
    
    return


def plot_normalised_DEL_barchart(folder_paths_dict, channel_name, m_slope):
    """
    Plot grouped bar chart of normalized DEL values vs wind speed for different simulation durations.
    Values are normalized by the 21600s simulation duration for each wind speed.

    Parameters:
    - folder_paths_dict: dict with duration as key and folder path as value
    - channel_name: str, the channel to extract (e.g., 'RootFxc1')
    - m_slope: int, the slope of the SN curve (e.g., 3, 4, 5)
    """
    import matplotlib.pyplot as plt

    Legend_FontSize = 10
    Axis_FontSize = 9.5
    Ticks_FontSize = 8

    # Color map for different durations
    durations_list = sorted(list(folder_paths_dict.keys()), key=lambda x: int(x.strip('s')))
    colors = cm.viridis(np.linspace(0.15, 0.9, len(durations_list)))
    # colors = cm.Reds(np.linspace(0.15, 0.9, len(durations_list)))

    # Storage for data
    all_data = {}  # {wind_speed: {duration: del_value}}

    # Process each simulation duration
    for duration in durations_list:
        folder_path = folder_paths_dict[duration]
        del_file = os.path.join(folder_path, f'DEL_m{m_slope}.csv')
        if not os.path.exists(del_file):
            print(f"Warning: DEL file not found in {folder_path}")
            continue

        # Read DEL data
        del_df = pd.read_csv(del_file)
        # Find the column that matches the channel_name (may have units in header)
        channel_col = None
        for col in del_df.columns:
            if channel_name in col:
                channel_col = col
                break
        if channel_col is None:
            raise ValueError(f"Channel '{channel_name}' not found in DEL file {del_file}.")

        # Extract wind speeds and DEL values
        wind_speeds = del_df.iloc[:, 0].values
        del_values = del_df[channel_col].values

        # Store for processing
        for ws, del_val in zip(wind_speeds, del_values):
            if ws not in all_data:
                all_data[ws] = {}
            try:
                del_val_float = float(del_val)
            except (ValueError, TypeError):
                del_val_float = np.nan
            all_data[ws][duration] = del_val_float if not np.isnan(del_val_float) else 0

    # Get reference values from 21600s
    reference_duration = '21600s'
    reference_data = {}
    for ws in all_data.keys():
        if reference_duration in all_data[ws]:
            reference_data[ws] = all_data[ws][reference_duration]
        else:
            reference_data[ws] = np.nan

    # Filter out non-numeric wind speed keys
    def is_number(s):
        try:
            float(s)
            return True
        except Exception:
            return False

    numeric_ws_keys = [ws for ws in all_data.keys() if is_number(ws)]

    # Normalize all values by reference
    wind_speeds_sorted = sorted(numeric_ws_keys, key=lambda x: float(x))
    normalized_data = {}
    for ws in wind_speeds_sorted:
        normalized_data[ws] = {}
        for duration in durations_list:
            if duration in all_data[ws] and isinstance(reference_data[ws], (int, float)) and not np.isnan(reference_data[ws]) and reference_data[ws] != 0:
                normalized_data[ws][duration] = all_data[ws][duration] / reference_data[ws]
            else:
                normalized_data[ws][duration] = np.nan

    # Prepare bar chart data
    fig, ax = plt.subplots(figsize=(3.25, 1.6))
    n_durations = len(durations_list)
    n_wind_speeds = len(wind_speeds_sorted)
    bar_width = 0.8 / n_durations
    x_positions = np.arange(n_wind_speeds)

    # Plot bars for each duration
    for j, duration in enumerate(durations_list):
        duration_label = duration.strip('s')
        values = [normalized_data[ws][duration] for ws in wind_speeds_sorted]
        x_offset = x_positions + (j - n_durations/2 + 0.5) * bar_width
        ax.bar(x_offset, values, bar_width, label=f'{duration_label}s',
               color=colors[j], edgecolor='black', linewidth=0.8)

    # Formatting
    ax.set_xlabel("Wind Speed (m/s)", fontsize=Axis_FontSize)
    # ax.set_ylabel(f"Normalized DEL ({channel_name}, m={m_slope})", fontsize=Axis_FontSize, fontweight='bold')
    ax.set_ylabel(f"{channel_name.split('_')[0]} (-)", fontsize=Axis_FontSize)
    # ax.set_title(f"Damage Equivalent Load - {channel_name} (m={m_slope})", fontsize=Axis_FontSize, fontweight='bold')
    ax.set_xticks(x_positions)
    ax.set_xticklabels([f'{float(ws):.1f}' for ws in wind_speeds_sorted], fontsize=Ticks_FontSize)
    ax.tick_params(axis='y', labelsize=Ticks_FontSize)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    ax.set_ylim(0, max([max([v for v in normalized_data[ws].values() if not np.isnan(v)]) for ws in wind_speeds_sorted]) * 1.2)
    # ax.legend(loc='upper left', fontsize=Legend_FontSize, frameon=True,
    #           edgecolor='black', fancybox=False, shadow=False, ncol=2)

    # legend = plt.legend(
    #     # duration_handles + [max_line, min_line],
    #     # duration_labels + ['Max', 'Min'],
    #     loc='upper center',
    #     bbox_to_anchor=(0.5, -0.05),
    #     ncol=4,
    #     frameon=True,
    #     edgecolor='black',
    #     fancybox=False,
    #     shadow=False,
    #     fontsize=Legend_FontSize)
    # plt.tight_layout(rect=[0, 0.15, 1, 1])

    plt.tight_layout()
    image_format = 'svg'
    image_name = os.path.join(str(OUTPUT_DIR), f'{channel_name.split("_")[0]}_DEL_m={m_slope}.svg')
    # plt.savefig(image_name, format=image_format, dpi=1200, bbox_inches='tight')
    plt.show()

    return normalized_data, fig