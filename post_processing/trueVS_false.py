# -*- coding: utf-8 -*-
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
from pathlib import Path

# ========= PATHS =========
ROOT_TRUE  = Path("/Users/antoniodegrazia/Desktop/run_2030_new_true/run_autarky")
ROOT_FALSE = Path("/Users/antoniodegrazia/Desktop/run_2030_new_false/run_autarky")
OUT_DIR = Path("/Users/antoniodegrazia/Desktop/planning/grafici")
OUT_DIR.mkdir(parents=True, exist_ok=True)
PNG_OUT = OUT_DIR / "compare_force_resource_UTOPIA_2030_final.png"

# ========= SETTINGS =========
COUNTRY = "DRC"     # i dati restano DRC
COUNTRY_LABEL = "Utopia"  # nome mostrato nel titolo
SCEN_TAG = ("VRES", "N")  # VRES + NoStorage

# === COLORI VIVI (come nelle figure di tesi) ===
COLORS = {
    "Existing": "#d1c7de",  # viola
    "OCGT":     "#ff9999",  # rosso chiaro
    "Wind":     "#66b3ff",  # azzurro
    "PV":       "#ffd966",  # giallo
}

# ========= FUNZIONI BASE =========
def parse_scenario_name(name: str):
    s = name.lower()
    if ("gt+vres" in s) or ("vres+gt" in s):
        family = "VRES+GT"
    elif "vres" in s:
        family = "VRES"
    else:
        family = "?"
    if   "nostorage" in s:
        tag = "N"
    elif "bess" in s:
        tag = "B"
    elif "phes" in s:
        tag = "P"
    else:
        tag = "?"
    return family, tag


def load_existing_for_country(root: Path, country: str) -> float:
    for scen_dir in sorted([p for p in root.iterdir() if p.is_dir()]):
        eq_path = scen_dir / "results" / "inputs_energy_cap_equals.csv"
        if not eq_path.exists():
            continue
        df_eq = pd.read_csv(eq_path)
        if "energy_cap_equals" not in df_eq.columns and "value" in df_eq.columns:
            df_eq = df_eq.rename(columns={"value": "energy_cap_equals"})
        if "techs" not in df_eq.columns or "locs" not in df_eq.columns:
            continue
        mask = (
            df_eq["locs"].astype(str).str.contains(country, case=False)
            & ~df_eq["techs"].astype(str).str.contains("bess|phes|transmission|final_demand|_kv", case=False)
        )
        return df_eq.loc[mask, "energy_cap_equals"].sum() / 1e6
    return 0.0


def load_new_caps_for_country(root: Path, country: str, family: str, tag: str):
    for scen_dir in sorted([p for p in root.iterdir() if p.is_dir()]):
        f, t = parse_scenario_name(scen_dir.name)
        if (f, t) != (family, tag):
            continue
        res_dir = scen_dir / "results"
        ec_csv = res_dir / "results_energy_cap.csv"
        eq_csv = res_dir / "inputs_energy_cap_equals.csv"
        if not ec_csv.exists():
            return {"OCGT": 0.0, "Wind": 0.0, "PV": 0.0}
        df_ec = pd.read_csv(ec_csv)
        if "energy_cap" not in df_ec.columns and "value" in df_ec.columns:
            df_ec = df_ec.rename(columns={"value": "energy_cap"})

        if eq_csv.exists():
            df_eq = pd.read_csv(eq_csv)
            if "energy_cap_equals" not in df_eq.columns and "value" in df_eq.columns:
                df_eq = df_eq.rename(columns={"value": "energy_cap_equals"})
        else:
            df_eq = df_ec[["techs", "locs"]].copy()
            df_eq["energy_cap_equals"] = 0.0

        df = pd.merge(df_ec, df_eq, on=["techs", "locs"], how="left")
        df["energy_cap_equals"] = df["energy_cap_equals"].fillna(0.0)
        df["new_capacity"] = df["energy_cap"] - df["energy_cap_equals"]
        df = df[df["locs"].astype(str).str.contains(country, case=False)]

        def sum_new(substr):
            return df.loc[df["techs"].astype(str).str.contains(substr, case=False), "new_capacity"].sum() / 1e6

        return {"OCGT": sum_new("ocgt"), "Wind": sum_new("wind"), "PV": sum_new("pv")}
    return {"OCGT": 0.0, "Wind": 0.0, "PV": 0.0}


# ========= CARICAMENTO DATI =========
data = {}
for label, root in [("Case A", ROOT_TRUE), ("Case B", ROOT_FALSE)]:
    existing = load_existing_for_country(root, COUNTRY)
    new_caps = load_new_caps_for_country(root, COUNTRY, *SCEN_TAG)
    new_caps["Existing"] = existing
    data[label] = new_caps

df = pd.DataFrame(data).T[["Existing", "OCGT", "Wind", "PV"]]

# rimuovi OCGT se tutto zero
if (df["OCGT"] == 0).all():
    df = df.drop(columns=["OCGT"])
    COLORS.pop("OCGT", None)

print(df)

# ========= PLOT =========
mpl.rcParams.update({
    "font.family": "serif",
    "font.size": 13,
    "axes.labelsize": 15,
    "axes.titlesize": 18,
    "axes.titleweight": "bold",
    "axes.linewidth": 1.2,
    "xtick.labelsize": 13,
    "ytick.labelsize": 13,
    "legend.frameon": True,
})

fig, ax = plt.subplots(figsize=(4.3, 4.2))

x = np.arange(len(df))
bar_width = 0.55
bottom = np.zeros_like(x, dtype=float)

for cat in df.columns:
    vals = df[cat].values
    ax.bar(
        x, vals, bottom=bottom,
        color=COLORS[cat],
        width=bar_width,
        edgecolor="white", linewidth=0.6,
        label=cat
    )
    bottom += vals

ax.set_xticks(x)
ax.set_xticklabels(df.index, rotation=0)
ax.set_ylabel("Capacity [GW]", fontweight="bold", labelpad=4)
ax.set_title(f"{COUNTRY_LABEL}: VRES NoStorage (2030)", pad=10, weight="bold")

ymax = np.ceil(bottom.max() / 20) * 20
ax.set_ylim(0, ymax * 1.05)

ax.grid(axis="y", linestyle=":", alpha=0.55)
for spine in ["top", "right"]:
    ax.spines[spine].set_visible(False)

# Legenda compatta, in alto a sinistra
leg = ax.legend(
    loc="upper left",
    frameon=True,
    fontsize=11,
    ncol=1,
)
leg.get_frame().set_edgecolor("0.85")

plt.tight_layout()
plt.savefig(PNG_OUT, dpi=400, bbox_inches="tight")
plt.close()
print(f"📁 Salvato: {PNG_OUT}")
