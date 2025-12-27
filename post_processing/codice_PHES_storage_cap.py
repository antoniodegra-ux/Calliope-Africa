import os
import pandas as pd
import matplotlib.pyplot as plt
import re

# === CONFIG ===
BASE_DIRS = {
    "2030": r"C:\Users\ilari\OneDrive\Desktop\tesi\2030_true\run_2030_new_contrue\run_autarky\autarky_VRES_2030_PHES",
    "2035": r"C:\Users\ilari\OneDrive\Desktop\tesi\2035_true\run_2035_new_true\run_autarky\autarky_VRES_2035_PHES",
    "2040": r"C:\Users\ilari\OneDrive\Desktop\tesi\2040_true\run_2040_new_true\run_autarky\autarky_VRES_2040_PHES",
}
OUTFILE = r"C:\Users\ilari\OneDrive\Desktop\tesi\GRAFICI\PHES_storage_capacity_2030_2035_2040.png"

COLORS = {"2030":"tab:blue", "2035":"tab:red", "2040":"tab:green"}

# pattern per includere PHES e le varianti installed
PATTERN_PHES = re.compile(r"^(PHES|PHES_2035_installed|PHES_2040_installed)$", re.IGNORECASE)

def map_state(loc: str) -> str:
    """Mappa i locs a Stati aggregati"""
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

def load_phes_capacity(base_dir: str, year: str) -> pd.Series:
    """Carica capacità PHES (incluse installed) da results_storage_cap.csv"""
    csv_path = os.path.join(base_dir, "results", "results_storage_cap.csv")
    if not os.path.exists(csv_path):
        print(f"[WARN] File mancante: {csv_path}")
        return pd.Series(dtype=float)
    df = pd.read_csv(csv_path)
    df_phes = df[df["techs"].astype(str).str.contains(PATTERN_PHES, na=False)].copy()
    if df_phes.empty:
        return pd.Series(dtype=float)
    df_phes["state"] = df_phes["locs"].apply(map_state)
    return df_phes.groupby("state")["storage_cap"].sum() / 1000.0  # kWh → MWh

# --- carico tutti gli anni ---
dfs = {}
all_states = set()
for year, base in BASE_DIRS.items():
    s = load_phes_capacity(base, year)
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
ax.set_ylabel("Storage Capacity [MWh]")
ax.set_title("PHES Installed Storage Capacity - Autarky")
ax.legend()

plt.tight_layout()
plt.savefig(OUTFILE, dpi=300)
plt.close()

print(f"✅ Grafico salvato in: {OUTFILE}")
