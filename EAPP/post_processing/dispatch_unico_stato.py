import pandas as pd
import matplotlib.pyplot as plt

# === 1. Load dispatch data ===
dispatch_file = "/Users/antoniodegrazia/Desktop/run_2040_new_true/run_autarky/autarky_GT+VRES_2040_PHES/results/results_carrier_prod.csv"
df = pd.read_csv(dispatch_file)

# === 2. Exclude storage (BESS/PHES) and transmission lines ===
exclude_keywords = [
    "BESS", "PHES",                # storage
    "220_kV", "132_kV", "400_kV", "500_kV",  # transmission
    "new_transmission", "transmission_2030_installed",
    "transmission_2035_installed", "transmission_2040_installed"
]
mask = ~df["techs"].str.contains("|".join(exclude_keywords), case=False, na=False)
df = df[mask].copy()

# === 3. Normalize locs (merge subregions for Egypt, TAN, DRC, KEN, Sudan) ===
def normalize_country(loc):
    if loc.startswith("Egypt"):
        return "Egypt"
    elif loc.startswith("TAN"):
        return "Tanzania"
    elif loc.startswith("DRC"):
        return "DRC"
    elif loc.startswith("KEN"):
        return "Kenya"
    elif loc.startswith("South_Sudan"):
        return "South Sudan"
    elif loc.startswith("Sudan"):   # attenzione: solo Sudan, non South Sudan
        return "Sudan"
    else:
        return loc

df["country"] = df["locs"].apply(normalize_country)

# === 4. Filter for one country ===
country_selected = "Ethiopia"   # scrivilo SEMPRE in minuscolo
df = df[df["country"].str.lower() == country_selected].copy()

# === 5. Convert time ===
df["timesteps"] = pd.to_datetime(df["timesteps"])

# === 6. Group by macro-categories ===
def map_category(tech):
    t = tech.lower()
    if "solar" in t or "pv" in t:
        return "Solar"
    elif "wind" in t:
        return "Wind"
    elif "hydro" in t:
        return "Hydro"
    elif "geo" in t:
        return "Geothermal"
    elif "bio" in t:
        return "Bioenergy"
    elif "nuclear" in t:
        return "Nuclear"
    elif any(x in t for x in ["ocgt", "ccgt", "diesel", "hfo", "steam_turbine", "gas_engine"]):
        return "Fossil"
    else:
        return "Other"

df["category"] = df["techs"].apply(map_category)

# === 7. Aggregate production ===
df_grouped = df.groupby(["timesteps", "category"])["carrier_prod"].sum().reset_index()
df_grouped["hour"] = df_grouped["timesteps"].dt.hour

# Profilo medio orario per categoria
df_avg = df_grouped.groupby(["hour", "category"])["carrier_prod"].mean().reset_index()
df_pivot = df_avg.pivot(index="hour", columns="category", values="carrier_prod").fillna(0)

# === 8. Fixed category order ===
category_order = ["Fossil", "Nuclear", "Bioenergy", "Geothermal", "Hydro", "Wind", "Solar"]
df_pivot = df_pivot.reindex(columns=[c for c in category_order if c in df_pivot.columns])

# === 9. Fixed colors ===
colors = {
    "Fossil": "#8c564b",
    "Nuclear": "#9467bd",
    "Bioenergy": "#2ca02c",
    "Geothermal": "#ff7f0e",
    "Hydro": "#1f77b4",
    "Solar": "#ffd700",
    "Wind": "#17becf"
}

# === 10. Load demand data ===
demand_file = "/Users/antoniodegrazia/Desktop/run_2040_new_true/run_autarky/autarky_GT+VRES_2040_PHES/Timeseries/Demand.csv"
df_demand = pd.read_csv(demand_file)

df_demand = df_demand.rename(columns={"Unnamed: 0": "timesteps"})
df_demand["timesteps"] = pd.to_datetime(df_demand["timesteps"], errors="coerce")

# Normalizza colonne (merge subregions)
df_demand = df_demand.rename(columns=lambda x: normalize_country(x) if x != "timesteps" else x)

# Porta tutte le colonne in minuscolo
df_demand.columns = [c.lower() for c in df_demand.columns]

# Somma solo le colonne corrispondenti al paese scelto (anche se duplicate)
mask = df_demand.columns == country_selected
if mask.any():
    df_demand["total_demand"] = -df_demand.loc[:, mask].sum(axis=1)
else:
    df_demand["total_demand"] = 0

# Profilo medio orario della domanda
df_demand["hour"] = df_demand["timesteps"].dt.hour
demand_profile = df_demand.groupby("hour")["total_demand"].mean()

# === 11. Plot dispatch + demand ===
plt.figure(figsize=(12,6))
ax = df_pivot.plot.area(ax=plt.gca(), alpha=0.9,
                        color=[colors[c] for c in df_pivot.columns])

# Linea della domanda
ax.plot(demand_profile.index, demand_profile.values,
        color="black", linewidth=2.0, label="Demand")

plt.title(f"Average Dispatch + Demand ({country_selected.capitalize()}, typical day, storage excluded)")
plt.xlabel("Hour of Day")
plt.ylabel("Generation [MWh]")
plt.legend(title="Category", bbox_to_anchor=(1.05, 1), loc="upper left")
plt.tight_layout()
plt.show()
