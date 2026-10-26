"""Post-processing driver and helper functions (statistics, DEL, rose plots, wind-speed surrogate).

Run from anywhere; the working directory is set to the project folder because the helper functions
use paths relative to it (e.g. DLC1p1/600s/).  The calls that generate the paper results are listed
as commented examples; enable the ones you need.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repository root
from fowt_duration.config import PROJECT_DIR, RUN_DIR, OUTPUT_DIR
os.chdir(PROJECT_DIR)
from fileinput import filename
import sys
import numpy as np
from xlsxwriter.utility import xl_rowcol_to_cell
import os
import math
from openpyxl.formatting.rule import CellIsRule, ColorScaleRule, FormulaRule
from openpyxl.styles.borders import Border, Side
from openpyxl import Workbook, load_workbook
import matplotlib.pyplot as plt
from matplotlib import lines
from fowt_duration.plot_settings import *
import matplotlib.gridspec as gridspec
import matplotlib.animation as animation
import glob
import re
import pandas as pd
import matplotlib.gridspec as gridspec
from matplotlib.ticker import FormatStrFormatter
from matplotlib.transforms import ScaledTranslation
from scipy.special import gamma
from mpl_toolkits.mplot3d import Axes3D
import seaborn as sns
from matplotlib import cm
from scipy.stats import weibull_min, weibull_max, lognorm
import re
from fowt_duration.openfast_functions import *
import subprocess
import sys
from openfast_toolbox.io import FASTOutputFile
from openfast_toolbox.postpro import equivalent_load
import numpy as np
import pandas as pd
import os
from matplotlib import cm

# path = os.getcwd()
# file = glob.glob(path)
# IntialPos = str(file[0].split('\\')[-1])[3:]
# print(file)

# Folder Paths
sim600s =   'DLC1p1\\600s\\'
sim1200s =  'DLC1p1\\1200s\\'
sim3600s =  'DLC1p1\\3600s\\'
sim7200s =  'DLC1p1\\7200s\\'
sim10800s = 'DLC1p1\\10800s\\'
sim14400s = 'DLC1p1\\14400s\\'
sim18000s = 'DLC1p1\\18000s\\'
sim21600s = 'DLC1p1\\21600s\\'

# Define folder paths for all durations
folder_paths_all = [sim600s, sim1200s, sim3600s, sim7200s, sim10800s, sim14400s, sim18000s, sim21600s]

# Define folder paths for all durations
folder_paths_all_dict = {'600s': sim600s,
                        '1200s': sim1200s,
                        '3600s': sim3600s,
                        '7200s': sim7200s,
                        '10800s': sim10800s,
                        '14400s': sim14400s,
                        '18000s': sim18000s,
                        '21600s': sim21600s}


# make plots for wave elevation channel
# channel_name_List = ['Wave1Elev', 'Wind1VelX']
Channel_Outputs = [
    "RootFxc1",
    "RootFyc1",
    "RootFzc1",
    "RootMyc1",
    "RootMzc1",
    "RootMxc1",
    "TwrBsFxt",
    "TwrBsFyt",
    "TwrBsFzt",
    "TwrBsMxt",
    "TwrBsMyt",
    "TwrBsMzt",
    "FAIRTEN1",
    "ANCHTEN1",
    "FAIRTEN2",
    "ANCHTEN2",
    "HydroFxi",
    "HydroFyi",
    "HydroFzi",
    "HydroMxi",
    "HydroMyi",
    "HydroMzi",
    "PtfmSurge",
    "PtfmSway",
    "PtfmHeave",
    "PtfmRoll",
    "PtfmPitch",
    "PtfmYaw",
    "LSSGagMya",
    "LSSGagMza"]


# # Usage example:
# for file in folder_paths_all:
#     write_output_statistics(file, skip=200)

# for channel in Channel_Outputs:
#     plot_extreme_statistics(folder_paths_all_dict, channel)

# for channel in Channel_Outputs:
    # plot_normalised_heatmap(folder_paths_all_dict, channel)

TowerBaseDia = 6.000   # meters
TowerBaseThk = 0.027  # meters

BladeRootDia = 3.386    # meters
BladeRootThk = 0.010    # meters

def section_properties(diameter, thickness):
    """Calculate cross-sectional area and moment of inertia for a hollow circular section."""
    outer_radius = diameter / 2
    inner_radius = outer_radius - thickness
    area = np.pi * (outer_radius**2 - inner_radius**2)
    moment_of_inertia = (np.pi / 4) * (outer_radius**4 - inner_radius**4)
    return area, moment_of_inertia

def F_rose(Fx, Fy, theta):
        """Calculate at different angles around the diameter of a cross-section."""
        return (Fy * np.cos(theta)) + (Fx * np.sin(theta))

def sigma_N(Fz, My, Mx, A, Iy, Ix, theta):
    """Calculate normal stress at a point in a cross-section."""
    return (Fz / A) + (My * np.cos(theta) / Iy) + (Mx * np.sin(theta) / Ix)

angles = np.radians(np.arange(0, 360, 20))



def read_channel(filename, channel, skip=200, as_array=True):
    # Read file: skip units row (row index 1)
    df = pd.read_csv(filename, sep=r"\s+", skiprows=[1], engine="python")

    if channel not in df.columns:
        raise ValueError(f"Channel '{channel}' not found.\nAvailable channels:\n{df.columns.tolist()}")

    # Skip rows where Time < skip value
    data = df[df['Time'] >= skip][channel]

    return data.to_numpy() if as_array else data.tolist()


OutputFile = os.path.join(sim600s, '5MW_OC4Semi_WSt_WavesWN_4p0mps_600s.OUT')

# time_values = read_channel(OutputFile, 'Time')
channel_values = read_channel(OutputFile, 'RootFxc1')




A, Iy = section_properties(BladeRootDia, BladeRootThk)
_, Ix = section_properties(BladeRootDia, BladeRootThk)

# Calculate normal stress time series
Fz = read_channel(OutputFile, 'RootFzc1')
My = read_channel(OutputFile, 'RootMyc1')
Mx = read_channel(OutputFile, 'RootMxc1')

normal_stress = sigma_N(Fz, My, Mx, A, Iy, Ix, 0)


#Update this code such that for a specified channels, FX, the maximum of FX and the corresponding value of FY in the timehistory file is extracted and for the defined angles in the code, theta is calculated and FR (resultant force) is computed, now a radar or rose plot of FR vs theta is then made. The radar plot should be done for the wind speeds 4, 10, 16 and 22 and let the color pallet be consistent with those from previous code  

# def get_output_files(folder_path):
#     """Get all .OUT files from a folder."""
#     return glob.glob(os.path.join(folder_path, '*.OUT'))

# def convert_string_decimal(filename):
#     """Extract wind speed from filename (e.g., '4p0mps' -> 4.0)."""
#     match = re.search(r'(\d+)p(\d+)mps', filename)
#     if match:
#         return float(f"{match.group(1)}.{match.group(2)}")
#     return None

BladeTower_Channels = ["RootFxc1","RootFyc1","RootFzc1","RootMyc1","RootMzc1","RootMxc1",
                       "TwrBsFxt","TwrBsFyt","TwrBsFzt","TwrBsMxt","TwrBsMyt","TwrBsMzt"]



def plot_channel_radar_rose(folder_paths_dict, FX_channel, FY_channel, n_angles=18, wind_speed=4.0, skip=200):
    """
    Create radar/rose plots of resultant force vs angle for multiple simulation durations.
    Parameters:
    - folder_paths_dict: dict, {duration_label: folder_path}
    - FX_channel: str, channel name for FX (e.g., 'RootFxc1')
    - FY_channel: str, channel name for FY (e.g., 'RootFyc1')
    - n_angles: int, number of angles around the circle
    - wind_speed: float, target wind speed (e.g., 4.0 for 4 m/s)
    - skip: int, seconds to skip from beginning
    """
    # Define color palette consistent with previous plots
    colors = cm.tab10(np.linspace(0, 1, len(folder_paths_dict)))
    
    # Define angles
    theta = np.radians(np.arange(0, 360, 360/n_angles))
    
    # Create figure with subplots for each duration
    fig, axes = plt.subplots(2, 4, figsize=(16, 10), subplot_kw=dict(projection='polar'))
    axes = axes.flatten()
    
    for idx, (duration, folder_path) in enumerate(folder_paths_dict.items()):
        output_files = get_output_files(folder_path)
        
        # Find file matching the target wind speed
        target_file = None
        for file in output_files:
            ws = convert_string_decimal(file)
            if ws == wind_speed:
                target_file = file
                break
        
        if target_file is None:
            print(f"No file found for {wind_speed} m/s in {duration}")
            axes[idx].set_title(f"{duration} - No Data")
            continue
        
        # Read the output file
        df = pd.read_csv(target_file, sep=r"\s+", skiprows=[1], engine="python")
        
        if FX_channel not in df.columns or FY_channel not in df.columns:
            print(f"Channels not found in {target_file}")
            continue
        
        # Skip transient response
        df = df[df['Time'] >= skip].reset_index(drop=True)
        
        # Extract FX and FY time series
        FX = df[FX_channel].values
        FY = df[FY_channel].values
        
        # Get max of FX and corresponding FY value
        max_idx = np.argmax(np.abs(FX))
        FX_max = FX[max_idx]
        FY_corr = FY[max_idx]
        
        # Calculate resultant force at each angle
        FR = (FY_corr * np.cos(theta)) + (FX_max * np.sin(theta))
        
        # Plot on polar axes
        ax = axes[idx]
        bars = ax.bar(theta, FR, width=0.35, alpha=0.7, color=colors[idx], edgecolor='black')
        ax.set_theta_zero_location('N')
        ax.set_theta_direction(-1)
        ax.set_title(f"{duration}\n(Ws={wind_speed}mps, FX_max={FX_max:.2f})", fontsize=10)
        ax.set_ylim(0, max(FR) * 1.1)
        ax.grid(True)
    
    plt.tight_layout()
    plt.savefig(f'RadarPlot_Ws{wind_speed}mps_{FX_channel}_vs_{FY_channel}.png', dpi=300, bbox_inches='tight')
    plt.show()



def write_channels_maximum_and_corresponding_values(folder_path, wind_speed=4.0, skip=200):
    """
    Extract maximum values for each channel and corresponding values of other channels.
    Creates an output file with channels as rows and columns.
    
    Parameters:
    - folder_path: str, path to folder containing .OUT files
    - wind_speed: float, target wind speed (e.g., 4.0 for 4 m/s)
    - skip: int, seconds to skip from beginning
    """
    
    BladeTower_Channels = ["RootFxc1","RootFyc1","RootFzc1","RootMyc1","RootMzc1","RootMxc1",
                           "TwrBsFxt","TwrBsFyt","TwrBsFzt","TwrBsMxt","TwrBsMyt","TwrBsMzt"]
    
    output_files = get_output_files(folder_path)
    
    # Find file matching the target wind speed
    target_file = None
    for file in output_files:
        ws = convert_string_decimal(file)
        if ws == wind_speed:
            target_file = file
            break
    
    if target_file is None:
        print(f"No file found for {wind_speed} m/s in {folder_path}")
        return
    
    # Read the output file
    df = pd.read_csv(target_file, sep=r"\s+", skiprows=[1], engine="python")
    
    # Check if all channels exist
    missing_channels = [ch for ch in BladeTower_Channels if ch not in df.columns]
    if missing_channels:
        print(f"Channels not found: {missing_channels}")
        return
    
    # Skip transient response
    df = df[df['Time'] >= skip].reset_index(drop=True)
    
    # Extract units from header
    channel_units = {}
    with open(target_file, 'r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            if 'Time' in line and i+1 < len(lines):
                units_line = lines[i+1]
                units_list = units_line.split()
                for j, col in enumerate(df.columns):
                    if j < len(units_list):
                        channel_units[col] = units_list[j]
                break
    
    # Create output matrix: rows = channels, columns = [max_value, corresponding values]
    output_data = {'Channel': BladeTower_Channels}
    
    for channel in BladeTower_Channels:
        # Get maximum value and its index
        max_idx = np.argmax(df[channel].values)
        max_value = df[channel].iloc[max_idx]

        min_idx = np.argmin(df[channel].values)
        min_value = df[channel].iloc[min_idx]
        
        # Get corresponding values from all channels at this index
        output_data[channel] = [max_value if ch == channel else df[ch].iloc[max_idx] 
                               for ch in BladeTower_Channels]
    
    # Create DataFrame
    result_df = pd.DataFrame(output_data).set_index('Channel')
    
    # Create output with units row
    units_row = pd.DataFrame([[channel_units.get(ch, 'N/A') for ch in BladeTower_Channels]], 
                             columns=BladeTower_Channels, index=['Units'])
    
    result_df = pd.concat([units_row, result_df])
    
    # Save to file
    output_filename = os.path.join(folder_path, f'CorrespondingValues_Ws{wind_speed}mps.csv')
    result_df.to_csv(output_filename)
    print(f"Output file saved: {output_filename}")
    
    return result_df

# wind = [4.0, 10.0, 16.0, 22.0]
# for files in folder_paths_all:
#     for w in wind:
#         write_channels_maximum_and_corresponding_values(files, wind_speed=w, skip=200)


    
# Usage example:
Mxy = ['TwrBsMyt', 'TwrBsMxt']
Ax_channel = 'TwrBsFzt'
Sect_prop = [TowerBaseDia, TowerBaseThk]
# for w in [4.0, 10.0, 16.0, 22.0]:
#     plot_channels_force_rose(folder_paths_all_dict, Mxy, Ax_channel, Sect_prop, n_angles=72, wind_speed=w)

# fig.legend(folder_paths_all_dict, loc='upper center', ncol=len(folder_paths_all_dict)/2, 
#            fontsize = Legend_FontSize, handlelength = 3, frameon=True, edgecolor='black',
#            fancybox=False, shadow=False)

# subprocess.check_call([sys.executable, "-m", "pip", "install", "scikit-learn"])


def get_channel_unit(output_file, channel_name):
    """Extract channel names and units from the header of an output file."""
    channel_units = {}

    with open(output_file, 'r') as f:
        lines = f.readlines()[0:2]
        channel_names = lines[0].strip().split()
        channel_units_list = lines[1].strip().split()

        for name, unit in zip(channel_names, channel_units_list):
            channel_units[name] = unit.replace("(", "").replace(")", "")  # Remove brackets

    unit = channel_units.get(channel_name)

    return unit
# for file in folder_paths_all:
#     write_damage_equivalent_load(file, skip=200)




Channel_Outputs = ["RootFxc1", "RootFyc1", "RootFzc1", "RootMyc1", "RootMzc1", "RootMxc1",
                   "TwrBsFxt", "TwrBsFyt", "TwrBsFzt", "TwrBsMxt", "TwrBsMyt", "TwrBsMzt",
                   "FAIRTEN1", "ANCHTEN1", "FAIRTEN2", "ANCHTEN2", "LSSGagMya","LSSGagMza"]

# for channel_name in Channel_Outputs:
#     if channel_name[0:4] == 'Root':
#         plot_normalised_DEL_barchart(folder_paths_all_dict, f"{channel_name}_[{get_channel_unit(OutputFile, channel_name)}]", m_slope=8)
#     else:
#         plot_normalised_DEL_barchart(folder_paths_all_dict, f"{channel_name}_[{get_channel_unit(OutputFile, channel_name)}]", m_slope=3)


def folders_path_for_regressionmodel(m):
    root_dir = "DLC1p1\\"

    durations = [600,1200,3600,7200,10800,14400,18000,21600]

    uls_data = []
    del_data = []

    for T in durations:
        folder = os.path.join(root_dir, f"{T}s")

        # ULS
        df_max = pd.read_csv(os.path.join(folder, "Statistics_Maximum.csv"))
        df_max = df_max.iloc[1:].apply(pd.to_numeric)
        df_max["duration"] = T
        uls_data.append(df_max)

        # DEL
        df_del = pd.read_csv(os.path.join(folder, f"DEL_m{m}.csv"))
        df_del = df_del.iloc[1:].apply(pd.to_numeric)
        df_del["duration"] = T
        del_data.append(df_del)

    return pd.concat(uls_data, ignore_index=True), pd.concat(del_data, ignore_index=True)



from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
import matplotlib.pyplot as plt



def wind_speed_surrogate(channel, wind_range, m):

    def clean_channel_names(df):
        """
        Removes units in square brackets from column names.
        Example: 'RootMxc1_[kN-m]' → 'RootMxc1'
        """
        new_columns = {}
        unit_dict = {}

        for col in df.columns:
            match = re.match(r'(.+?)_\[(.+?)\]', col)
            if match:
                clean_name = match.group(1)
                unit = match.group(2)
                new_columns[col] = clean_name
                unit_dict[clean_name] = unit
            else:
                new_columns[col] = col

        df = df.rename(columns=new_columns)
        return df, unit_dict
    
    uls_df , del_df = folders_path_for_regressionmodel(m)


    del_df, del_units = clean_channel_names(del_df)

    # --- Extract 21600s baseline only ---
    uls_base = uls_df[uls_df["duration"] == 21600][["Wind Speed", channel]]
    del_base = del_df[del_df["duration"] == 21600][["Wind Speed", channel]]

    U = uls_base["Wind Speed"].values.reshape(-1,1)
    y_uls = uls_base[channel].values
    y_del = del_base[channel].values

    # --------------------------
    # ULS Polynomial Fit
    # --------------------------
    poly = PolynomialFeatures(degree=2)
    U_poly = poly.fit_transform(U)

    model_uls = LinearRegression()
    model_uls.fit(U_poly, y_uls)

    y_uls_pred_train = model_uls.predict(U_poly)
    r2_uls = r2_score(y_uls, y_uls_pred_train)

    # --------------------------
    # DEL Power-law Fit
    # --------------------------
    logU = np.log(U)
    logDEL = np.log(y_del)

    model_del = LinearRegression()
    model_del.fit(logU, logDEL)

    logDEL_pred = model_del.predict(logU)
    y_del_pred_train = np.exp(logDEL_pred)
    r2_del = r2_score(y_del, y_del_pred_train)

    # --------------------------
    # Predict new wind speeds
    # --------------------------
    U_new = np.array(wind_range).reshape(-1,1)

    U_new_poly = poly.transform(U_new)
    y_uls_new = model_uls.predict(U_new_poly)
    y_del_new = np.exp(model_del.predict(np.log(U_new)))

    # --------------------------
    # Plot
    # --------------------------
    fig, ax = plt.subplots(1, 2, figsize=(7, 1.65))
    Legend_FontSize = 10
    Axis_FontSize = 9.5
    Ticks_FontSize = 8

    get_channel_unit(OutputFile, channel)
    maxx = max(wind_range)
    minx = min(wind_range)

    # ULS
    ax[0].plot(U_new, y_uls_new, 'k-', label='Fit', linewidth=1.0)
    ax[0].scatter(U, y_uls, marker='+', color='red', s=50)
    ax[0].set_xlabel("Wind Speed (m/s)", fontsize=Axis_FontSize)
    ax[0].set_ylabel(f"{channel} ULS ({get_channel_unit(OutputFile, channel)})", fontsize=Axis_FontSize-2)
    # ax[0].text(0.05, 0.95, f"$R^2$ = {r2_uls:.4f}", transform=ax[0].transAxes, fontsize=8, verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    ax[0].text(0.05, 0.95, f"$R^2$ = {r2_uls:.4f}", transform=ax[0].transAxes, fontsize=8, verticalalignment='top')
    # ax[0].tick_params(axis='both', which='major', labelsize=Ticks_FontSize, direction='in')
    ax[0].tick_params(axis='both', labelsize=Ticks_FontSize, direction='in')
    ax[0].yaxis.set_major_formatter(plt.ScalarFormatter(useMathText=True))
    ax[0].ticklabel_format(axis='y', style='sci', scilimits=(0,0))
    ax[0].yaxis.get_offset_text().set_fontsize(Ticks_FontSize)
    ax[0].set_xlim(minx - 1, maxx + 1)
    ax[0].set_ylim(min(y_uls_new) * 0.95, max(y_uls_new) * 1.05)
    # ax[0].grid(True, alpha=0.3)

    # DEL
    unit_label = del_units.get(channel, "")
    ax[1].plot(U_new, y_del_new, 'k-', label='Fit', linewidth=1.0)
    ax[1].scatter(U, y_del, marker='+', color='red', s=50)
    ax[1].set_xlabel("Wind Speed (m/s)", fontsize=Axis_FontSize)
    ax[1].set_ylabel(f"{channel} DEL ({get_channel_unit(OutputFile, channel)})", fontsize=Axis_FontSize-2)
    ax[1].text(0.05, 0.95, f"$R^2$ = {r2_del:.4f}", transform=ax[1].transAxes, fontsize=8, verticalalignment='top')
    # ax[1].tick_params(axis='both', which='major', labelsize=Ticks_FontSize, direction='in')
    ax[1].tick_params(axis='both', labelsize=Ticks_FontSize, direction='in')
    ax[1].yaxis.set_major_formatter(plt.ScalarFormatter(useMathText=True))
    ax[1].ticklabel_format(axis='y', style='sci', scilimits=(0,0))
    ax[1].yaxis.get_offset_text().set_fontsize(Ticks_FontSize)
    ax[1].set_xlim(minx - 1, maxx + 1)
    ax[1].set_ylim(min(y_del_new) * 0.95, max(y_del_new) * 1.05)
    # ax[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.tight_layout()
    image_format = 'svg'
    # image_name = os.path.join(str(OUTPUT_DIR), f'{channel}.svg')
    # plt.savefig(image_name, format=image_format, dpi=1200, bbox_inches='tight')
    plt.show()

    return y_uls_new, y_del_new

wind_range = np.arange(1,25,1)

# wind_speed_surrogate(Channel_Outputs[0], wind_range=wind_range, m=10)
# for channel_name in Channel_Outputs:
#     if channel_name[0:4] == 'Root':
#         wind_speed_surrogate(channel_name, wind_range=wind_range, m=10)
#     else:
#         wind_speed_surrogate(channel_name, wind_range=wind_range, m=4)