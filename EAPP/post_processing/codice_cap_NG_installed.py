import os
import pandas as pd
import matplotlib.pyplot as plt
import re

# === CONFIG ===
BASE_DIRS = {
    "2030": r"C:\Users\ilari\OneDrive\Desktop\tesi\2030_true\run_2030_new_contrue\run_autarky\autarky_GT+VRES_2030_BESS",
    "2035": r"C:\Users\ilari\OneDrive\Desktop\tesi\2035_true\run_2035_new_true\run_autarky\autarky_GT+VRES_2035_BESS",
    "2040": r"C:\Users\ilari\OneDrive\Desktop\tesi\2040_true\run_2040_new_true\run_autarky\autarky_GT+VRES_2040_BESS",
}
OUTFILE = r"C:\Users\ilari\OneDrive\Desktop\tesi\GRAFICI\NG_installed_capacity_2030_2035_2040.png"

COLORS = {"2030":"tab:blue", "2035":"tab:red", "2040":"tab:green"}

# regex per tecnologie NG
PATTERN_NG = re.compile(r"(OCGT_NG|OCGT_NG_new|CCGT_NG|Steam_turbine_NG|Gas_Turbine|Gas_Engine|OCGT_NG_new_2035_installed|OCGT_NG_new_2040_installed)", re.IGNORECASE)

def map_state(loc):
    if loc.startswith("TAN_"):
        return "TAN"
    elif loc.startswith("Egypt_"):
        return "Egypt"
    elif loc.startswith("DRC_"):
        return "DRC"
    elif loc.startswith("KEN_"):
        return "KEN"
    else:
        return loc.split("_")[0]  # fallback: prefisso dello stato

def load_ng_capacity(base_dir, year):
    csv_path = os.path.join(base_dir, "results", "results_energy_cap.csv")
    df = pd.read_csv(csv_path)
    df_ng = df[df["techs"].astype(str).str.contains(PATTERN_NG, na=False)].copy()
    df_ng["state"] = df_ng["locs"].apply(map_state)
    return df_ng.groupby("state")["energy_cap"].sum() / 1000.0  # kW→MW

# --- carico tutti gli anni ---
dfs = {}
all_states = set()
for year, base in BASE_DIRS.items():
    s = load_ng_capacity(base, year)
    dfs[year] = s
    all_states |= set(s.index)

# merge in un unico DataFrame
df_plot = pd.DataFrame(index=sorted(all_states))
for year, s in dfs.items():
    df_plot[year] = s
df_plot = df_plot.fillna(0)

# --- plot ---
fig, ax = plt.subplots(figsize=(12,6))
bar_width = 0.25
x = range(len(df_plot.index))

for i, year in enumerate(["2030","2035","2040"]):
    ax.bar([xx + (i-1)*bar_width for xx in x],
           df_plot[year].values,
           width=bar_width,
           label=year,
           color=COLORS[year])

ax.set_xticks(x)
ax.set_xticklabels(df_plot.index, rotation=45, ha="right")
ax.set_ylabel("NG Capacity [MW]")
ax.set_title("Natural Gas Capacity - Autarky")
ax.legend()

plt.tight_layout()
plt.savefig(OUTFILE, dpi=300)
plt.close()

print(f"Grafico salvato in: {OUTFILE}")
