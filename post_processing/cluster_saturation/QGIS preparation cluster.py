import pandas as pd
import os
import re
import geopandas as gpd
from shapely.geometry import Point

# === Percorsi ===
base_folder = "/Users/antoniodegrazia/Desktop/run_2030_new_true/run_new_trasmission"
PV_input_path = "/Users/antoniodegrazia/Desktop/post_processing/cluster_saturation/2030_true/solar_MSR_techs_latlon_capacity.csv"
Wind_input_path = "/Users/antoniodegrazia/Desktop/post_processing/cluster_saturation/2030_true/wind_MSR_techs_latlon_capacity.csv"
output_folder = "/Users/antoniodegrazia/Desktop/post_processing/cluster_saturation/2030_true_new_transmission"
os.makedirs(output_folder, exist_ok=True)

# === Scenari specifici ===
scenario_names = [
    "new_trasmission_VRES_2030_BESS",
    "new_trasmission_GT+VRES_2030_BESS",
    "new_trasmission_GT+VRES_2030_PHES",
    "new_trasmission_GT+VRES_2030_nostorage",
    "new_trasmission_VRES_2030_PHES",
    "new_trasmission_VRES_2030_nostorage"
]

# === Funzioni utili ===
def extract_base_tech(tech):
    return re.sub(r'_\d{4}_installed$', '', tech)

def assign_color(saturation):
    if pd.isna(saturation):
        return '#B0B0B0'
    elif saturation < 0.00005:
        return '#808080'
    elif saturation < 0.05:
        return '#00FF00'
    elif saturation < 0.15:
        return '#ADFF2F'
    elif saturation < 0.3:
        return '#FFFF00'
    elif saturation < 0.5:
        return '#FFD700'
    elif saturation < 0.75:
        return '#FFA500'
    elif saturation < 1:
        return '#FF4500'
    elif saturation >= 1:
        return '#FF0000'

def assign_bubble_size(capacity):
    if pd.isna(capacity):
        return 2
    elif capacity <= 1_000_000:
        return 2
    elif capacity <= 10_000_000:
        return 4
    elif capacity <= 30_000_000:
        return 6
    elif capacity <= 50_000_000:
        return 8
    else:
        return 10

# === Caricamento input cluster ===
PV_input_data = pd.read_csv(PV_input_path)
Wind_input_data = pd.read_csv(Wind_input_path)

# === Loop sugli scenari specifici ===
for scenario_name in scenario_names:
    scenario_path = os.path.join(base_folder, scenario_name)
    results_csv_path = os.path.join(scenario_path, "results", "results_energy_cap.csv")

    if not os.path.isfile(results_csv_path):
        print(f"⚠️ Nessun file trovato per {scenario_name}")
        continue

    msr_data = pd.read_csv(results_csv_path)
    msr_data = msr_data[msr_data['techs'].str.contains("MSR", na=False)]

    if 'energy_cap' not in msr_data.columns:
        print(f"❌ 'energy_cap' non trovato in {scenario_name}")
        continue

    msr_data['base_tech'] = msr_data['techs'].apply(extract_base_tech)
    grouped_data = msr_data.groupby('base_tech', as_index=False)['energy_cap'].sum()

    pv_data = grouped_data[grouped_data['base_tech'].str.contains("PV", na=False)]
    wind_data = grouped_data[grouped_data['base_tech'].str.contains("Wind", na=False)]

    merged_PV = pd.merge(PV_input_data, pv_data, left_on="techs", right_on="base_tech", how="left")
    merged_Wind = pd.merge(Wind_input_data, wind_data, left_on="techs", right_on="base_tech", how="left")

    merged_PV["Saturation"] = merged_PV["energy_cap"] / merged_PV["Max Capacity [kW]"]
    merged_Wind["Saturation"] = merged_Wind["energy_cap"] / merged_Wind["Max Capacity [kW]"]

    merged_PV["Color"] = merged_PV["Saturation"].apply(assign_color)
    merged_Wind["Color"] = merged_Wind["Saturation"].apply(assign_color)

    merged_PV["Bubble_Size"] = merged_PV["Max Capacity [kW]"].apply(assign_bubble_size)
    merged_Wind["Bubble_Size"] = merged_Wind["Max Capacity [kW]"].apply(assign_bubble_size)

    # === Crea colonna Color_Bubble per .qml ===
    merged_PV["Color_Bubble"] = merged_PV["Color"] + "_" + merged_PV["Bubble_Size"].astype(str)
    merged_Wind["Color_Bubble"] = merged_Wind["Color"] + "_" + merged_Wind["Bubble_Size"].astype(str)

    # === Pulizia colonne inutili (opzionale) ===
    columns_to_drop = ["locs", "energy_cap", "cluster_color", "Capacity [kW]"]
    merged_PV = merged_PV.drop(columns=columns_to_drop, errors='ignore')
    merged_Wind = merged_Wind.drop(columns=columns_to_drop, errors='ignore')

    # === Salva CSV ===
    PV_output_file = os.path.join(output_folder, f"{scenario_name}_Solar_MSR.csv")
    merged_PV.to_csv(PV_output_file, index=False)

    Wind_output_file = os.path.join(output_folder, f"{scenario_name}_Wind_MSR.csv")
    merged_Wind.to_csv(Wind_output_file, index=False)

    # === Esporta anche shapefile ===
    merged_PV["geometry"] = merged_PV.apply(lambda row: Point(row["Longitude"], row["Latitude"]), axis=1)
    gdf_pv = gpd.GeoDataFrame(merged_PV, geometry="geometry", crs="EPSG:4326")
    pv_shp_folder = os.path.join(output_folder, f"{scenario_name}_Solar_MSR_SHP")
    os.makedirs(pv_shp_folder, exist_ok=True)
    gdf_pv.to_file(os.path.join(pv_shp_folder, f"{scenario_name}_Solar_MSR.shp"))

    merged_Wind["geometry"] = merged_Wind.apply(lambda row: Point(row["Longitude"], row["Latitude"]), axis=1)
    gdf_wind = gpd.GeoDataFrame(merged_Wind, geometry="geometry", crs="EPSG:4326")
    wind_shp_folder = os.path.join(output_folder, f"{scenario_name}_Wind_MSR_SHP")
    os.makedirs(wind_shp_folder, exist_ok=True)
    gdf_wind.to_file(os.path.join(wind_shp_folder, f"{scenario_name}_Wind_MSR.shp"))

    print(f"✅ CSV + SHP + Color_Bubble generati per {scenario_name}")

print("🎉 Tutto completato! Ora puoi usare il .qml generico in QGIS.")
