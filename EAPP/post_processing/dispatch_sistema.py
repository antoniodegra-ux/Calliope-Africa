# -*- coding: utf-8 -*-
"""
Electricity Mix Generation – Total EAPP (excluding storage & transmission)
Percentages only in legend – Save as PNG with scenario name
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# === 1. Load dispatch data ===
dispatch_file = Path("/Users/antoniodegrazia/Desktop/run_2040_new_true/run_new_trasmission/new_trasmission_VRES_2040_PHES/results/results_carrier_prod.csv")
df = pd.read_csv(dispatch_file, usecols=["timesteps", "techs", "carrier_prod"])

# === 2. Exclude storage and transmission ===
exclude_keywords = [
    "BESS", "PHES",
    "220_kV", "132_kV", "400_kV", "500_kV",
    "new_transmission", "transmission_2030_installed",
    "transmission_2035_installed", "transmission_2040_installed"
]
mask = ~df["techs"].str.contains("|".join(exclude_keywords), case=False, na=False)
df = df[mask].copy()

# === 3. Map technologies to macro-categories ===
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
    elif any(x in t for x in ["ocgt", "ccgt", "diesel", "hfo", "steam_turbine", "gas_engine"]):
        return "Fossil"
    else:
        return "Other"

df["category"] = df["techs"].apply(map_category)

# === 4. Aggregate total production by category ===
totals = df.groupby("category")["carrier_prod"].sum()
total_gen = totals.sum()

# === 5. Calculate shares and filter <1% ===
shares = (totals / total_gen * 100).sort_values(ascending=False)
shares_filtered = shares[shares >= 1]

# === 6. Thesis colors (Other -> light gray) ===
colors = {
    "Fossil": "#8c564b",      # marrone scuro
    "Bioenergy": "#2ca02c",   # verde
    "Geothermal": "#ff7f0e",  # arancione
    "Hydro": "#1f77b4",       # blu scuro
    "Solar": "#ffd700",       # giallo
    "Wind": "#cfe3ff",        # azzurro chiaro
    "Other": "#d3d3d3"        # grigio chiaro
}

# === 7. Plot total EAPP pie ===
plt.figure(figsize=(6, 6))
wedges, texts = plt.pie(
    shares_filtered.values,
    colors=[colors.get(c, "#d3d3d3") for c in shares_filtered.index],
    startangle=90
)

# === 8. Legend with percentages ===
legend_labels = [f"{cat}: {shares_filtered[cat]:.1f}%" for cat in shares_filtered.index]
plt.legend(
    wedges, legend_labels,
    loc="center left", bbox_to_anchor=(1, 0.5),
    fontsize=11
)

plt.tight_layout()

# === 9. Save figure with scenario name ===
scenario_name = dispatch_file.parts[-3]  # estrae "new_trasmission_VRES_2040_nostorage"
out_path = dispatch_file.parent / f"{scenario_name}.png"

plt.savefig(out_path, dpi=400, bbox_inches="tight")
plt.close()

print(f"✅ Figure saved to: {out_path}")
