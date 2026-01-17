# -*- coding: utf-8 -*-
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from matplotlib.patches import Patch

# === PATH SCENARI ===
BASE_2040 = Path("/Users/antoniodegrazia/Desktop/run_2040_new_true")
SCENARIOS = {
    "Autarky":                BASE_2040 / "run_autarky",
    "Existing Transmission":  BASE_2040 / "run_existing",
    "Transmission Expansion": BASE_2040 / "run_new_trasmission",
}

OUT_DIR = BASE_2040.parent / "planning" / "grafici"
OUT_DIR.mkdir(parents=True, exist_ok=True)
PNG_OUT = OUT_DIR / "capacity_total_2040_panels.png"

# === COLORI ===
COLORS = {"OCGT": "#ff9999", "Wind": "#66b3ff", "PV": "#ffd700"}
STACK_CATS    = ["OCGT", "Wind", "PV"]
ORDER_FAMILY  = ["VRES", "VRES+GT"]
ORDER_STORAGE = ["N", "B", "P"]

# === FUNZIONI ===
def parse_scenario_name(name: str):
    s = name.lower()
    family = "VRES+GT" if ("gt+vres" in s or "vres+gt" in s) else "VRES"
    if   "nostorage" in s: tag = "N"
    elif "bess" in s:      tag = "B"
    elif "phes" in s:      tag = "P"
    else:                  tag = "?"
    return family, tag

def load_caps_total_2040(results_dir: Path) -> dict:
    df = pd.read_csv(results_dir / "results_energy_cap.csv")
    if "energy_cap" not in df.columns and "value" in df.columns:
        df = df.rename(columns={"value": "energy_cap"})
    df["techs"] = df["techs"].str.lower()

    out = {}
    out["Wind"] = df.loc[df["techs"].str.contains("wind") & df["techs"].str.contains("msr"), "energy_cap"].sum() / 1e6
    out["PV"]   = df.loc[df["techs"].str.contains("pv")   & df["techs"].str.contains("msr"), "energy_cap"].sum() / 1e6
    out["OCGT"] = df.loc[df["techs"].str.contains("ocgt") & df["techs"].str.contains("new"), "energy_cap"].sum() / 1e6
    return out

# === COSTRUZIONE DATAFRAME ===
rows = {}
for scen_name, scen_root in SCENARIOS.items():
    for sub in sorted(scen_root.iterdir()):
        res_dir = sub / "results"
        if not res_dir.is_dir():
            continue
        fam, tag = parse_scenario_name(sub.name)
        rows[(scen_name, fam, tag)] = load_caps_total_2040(res_dir)

index = [(s, f, t) for s in SCENARIOS for f in ORDER_FAMILY for t in ORDER_STORAGE]
df = pd.DataFrame([rows.get(k, {c:0 for c in STACK_CATS}) for k in index],
                  index=pd.MultiIndex.from_tuples(index, names=["Scenario","Family","Tag"]))

# === MAX CAPACITY dinamico ===
ymax = df.sum(axis=1).max() * 1.15

# ========= PLOT =========
plt.rcParams.update({"font.size": 13})
fig, axes = plt.subplots(1, 3, figsize=(18, 7), sharey=True)
# ↓ pannelli leggermente più vicini
fig.subplots_adjust(left=0.07, right=0.95, top=0.82, bottom=0.22, wspace=0.08)

for ax, (scen, scen_root) in zip(axes, SCENARIOS.items()):
    positions = []
    labels_NBP = []
    group_centers = {}
    x = 0.0
    STEP = 1.8
    INNER_GAP = 0.8

    # --- BLOCCO VRES ---
    xs_block = []
    for tag in ORDER_STORAGE:
        bottom = 0
        for cat in STACK_CATS:
            val = df.loc[(scen, "VRES", tag), cat]
            ax.bar(x, val, bottom=bottom, color=COLORS[cat],
                   edgecolor="white", width=1.0)
            bottom += val
        positions.append(x)
        labels_NBP.append(tag)
        xs_block.append(x)
        x += STEP
    group_centers["VRES"] = sum(xs_block) / len(xs_block)

    x += INNER_GAP

    # --- BLOCCO VRES+GT ---
    xs_block = []
    for tag in ORDER_STORAGE:
        bottom = 0
        for cat in STACK_CATS:
            val = df.loc[(scen, "VRES+GT", tag), cat]
            ax.bar(x, val, bottom=bottom, color=COLORS[cat],
                   edgecolor="white", width=1.0)
            bottom += val
        positions.append(x)
        labels_NBP.append(tag)
        xs_block.append(x)
        x += STEP
    group_centers["VRES+GT"] = sum(xs_block) / len(xs_block)

    ax.set_xticks(positions)
    ax.set_xticklabels(labels_NBP)
    ax.set_ylim(0, ymax)
    ax.set_title(f"{scen}", fontsize=15, fontweight="bold")

    # scritte sotto (VRES e VRES+GT)
    ax.text(group_centers["VRES"], -0.10*ymax, "VRES", ha="center", va="top", fontsize=12)
    ax.text(group_centers["VRES+GT"], -0.10*ymax, "VRES+GT", ha="center", va="top", fontsize=12)

    # === Prima legenda: tecnologie ===
    tech_patches = [
        Patch(color=COLORS["OCGT"], label="OCGT"),
        Patch(color=COLORS["Wind"], label="Wind"),
        Patch(color=COLORS["PV"],   label="PV")
    ]
    legend1 = ax.legend(handles=tech_patches, loc="upper right", fontsize=11, frameon=True)
    ax.add_artist(legend1)

    # === Seconda legenda: storage ===
    storage_patches = [
        Patch(color="white", label="N = No storage"),
        Patch(color="white", label="B = BESS"),
        Patch(color="white", label="P = PHES"),
    ]
    ax.legend(handles=storage_patches, loc="upper right", fontsize=11, frameon=True, bbox_to_anchor=(1, 0.78))

    # contorno spesso
    for side in ["top", "bottom", "left", "right"]:
        ax.spines[side].set_linewidth(1.5)

# Titolo generale sopra tutti i pannelli


# ↓ unica label asse y
fig.text(0.02, 0.5, "Capacity [GW]", va='center', rotation='vertical',
         fontsize=16, fontweight='bold')

plt.savefig(PNG_OUT, dpi=300, bbox_inches="tight")
plt.close()
print(f"📁 Salvato: {PNG_OUT}")
