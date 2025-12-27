# -*- coding: utf-8 -*-
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
from pathlib import Path

# ========= PATH (aggiorna se necessario) =========
ROOTS = {
    2030: Path("/Users/antoniodegrazia/Desktop/run_2030_new_true/run_new_trasmission"),
    2035: Path("/Users/antoniodegrazia/Desktop/run_2035_new_true/run_new_trasmission"),
    2040: Path("/Users/antoniodegrazia/Desktop/run_2040_new_true/run_new_trasmission"),
}
OUT_DIR = ROOTS[2035].parent.parent / "planning" / "grafici"
OUT_DIR.mkdir(parents=True, exist_ok=True)
PNG_OUT = OUT_DIR / "existing_2030_2035_2040_boxed_leftlegend.png"

# ========= COLORI =========
COLORS = {
    "Existing": "#d1c7de",  # viola-grigio neutro
    "OCGT":     "#ff9999",  # rosso medio
    "Wind":     "#66b3ff",  # azzurro
    "PV":       "#ffd700",  # giallo solare
}

STACK_CATS     = ["Existing", "OCGT", "Wind", "PV"]
ORDER_FAMILY   = ["VRES", "VRES+GT"]
ORDER_STORAGE  = ["N", "B", "P"]
YEARS_SORTED   = sorted(ROOTS.keys())

# === FUNZIONI ===
def parse_scenario_name(name: str):
    s = name.lower()
    family = "VRES+GT" if ("gt+vres" in s or "vres+gt" in s) else "VRES"
    if   "nostorage" in s: tag = "N"
    elif "bess" in s:      tag = "B"
    elif "phes" in s:      tag = "P"
    else:                  tag = "?"
    return family, tag

def load_existing_global(roots: dict) -> float:
    for y in sorted(roots.keys()):
        for scen_dir in sorted(roots[y].iterdir()):
            eq_path = scen_dir / "results" / "inputs_energy_cap_equals.csv"
            if eq_path.exists():
                df_eq = pd.read_csv(eq_path)
                if "energy_cap_equals" not in df_eq.columns and "value" in df_eq.columns:
                    df_eq = df_eq.rename(columns={"value": "energy_cap_equals"})
                t = df_eq["techs"].str.lower()
                mask = ~(t.str.contains("bess|phes|transmission|final_demand|_kv"))
                return df_eq.loc[mask, "energy_cap_equals"].sum() / 1e6
    return 0.0

existing_FIXED_GW = load_existing_global(ROOTS)

def load_new_caps_one_scenario(results_dir: Path) -> dict:
    df_ec = pd.read_csv(results_dir / "results_energy_cap.csv")
    if "energy_cap" not in df_ec.columns and "value" in df_ec.columns:
        df_ec = df_ec.rename(columns={"value": "energy_cap"})
    df_eq = pd.read_csv(results_dir / "inputs_energy_cap_equals.csv")
    if "energy_cap_equals" not in df_eq.columns and "value" in df_eq.columns:
        df_eq = df_eq.rename(columns={"value": "energy_cap_equals"})
    df = pd.merge(df_ec, df_eq, on=["techs", "locs"], how="left")
    df["energy_cap_equals"] = df["energy_cap_equals"].fillna(0.0)
    df["new_capacity"] = df["energy_cap"] - df["energy_cap_equals"]
    def sum_new(cat): return df.loc[df["techs"].str.lower().str.contains(cat), "new_capacity"].sum() / 1e6
    return {"OCGT": sum_new("ocgt"), "Wind": sum_new("wind"), "PV": sum_new("pv")}

def additions_df_for_year(root: Path) -> pd.DataFrame:
    rows = {}
    for scen_dir in sorted(root.iterdir()):
        res_dir = scen_dir / "results"
        if not res_dir.is_dir():
            continue
        family, tag = parse_scenario_name(scen_dir.name)
        rows[(family, tag)] = load_new_caps_one_scenario(res_dir)
    index = [(f, t) for f in ORDER_FAMILY for t in ORDER_STORAGE]
    data = {k: [] for k in ["OCGT", "Wind", "PV"]}
    for key in index:
        vals = rows.get(key, {"OCGT": 0.0, "Wind": 0.0, "PV": 0.0})
        for c in data:
            data[c].append(vals[c])
    return pd.DataFrame(data, index=pd.MultiIndex.from_tuples(index, names=["Family", "Tag"]))

# ---------- cumulative ----------
cumulative_by_year = {}
cum = None
for y in YEARS_SORTED:
    add_df = additions_df_for_year(ROOTS[y])
    cum = add_df if cum is None else (cum + add_df)
    cum_with_existing = cum.copy()
    cum_with_existing["Existing"] = existing_FIXED_GW
    cum_with_existing = cum_with_existing[["Existing", "OCGT", "Wind", "PV"]]
    cumulative_by_year[y] = cum_with_existing

# ========= PLOT =========
plt.rcParams.update({"font.size": 13})
fig, axes = plt.subplots(1, 3, figsize=(19, 7.5), sharey=True)
fig.subplots_adjust(left=0.07, right=0.95, top=0.83, bottom=0.22, wspace=0.08)

group_gap = 0.9
x_vres = np.arange(0, 3)
x_vres_gt = np.arange(0, 3) + 3 + group_gap
x_all = np.concatenate([x_vres, x_vres_gt])
x_ticklbl = ["N", "B", "P", "N", "B", "P"]

for ax, year in zip(axes, YEARS_SORTED):
    df = cumulative_by_year[year]
    bottom = np.zeros_like(x_all, dtype=float)

    for cat in STACK_CATS:
        vals = np.array(
            [df.loc[("VRES", t), cat] for t in ORDER_STORAGE] +
            [df.loc[("VRES+GT", t), cat] for t in ORDER_STORAGE]
        )
        ax.bar(
            x_all, vals, bottom=bottom, color=COLORS[cat], width=0.9,
            edgecolor="white", linewidth=0.8, label=cat
        )
        bottom += vals

    # --- asse e scritte ---
    ax.set_title(f"{year}", fontsize=15, fontweight="bold")
    ax.set_xlim(-0.75, x_all[-1] + 0.75)
    ax.set_ylim(0, 350)
    ax.set_xticks(x_all)
    ax.set_xticklabels(x_ticklbl)
    if ax is axes[0]:
        ax.set_ylabel("Capacity [GW]", fontsize=14, fontweight="bold")

    # scritte VRES / VRES+GT più distanziate
    ax.text(x_vres.mean(), -30, "VRES", ha="center", va="top", fontsize=12)
    ax.text(x_vres_gt.mean(), -30, "VRES+GT", ha="center", va="top", fontsize=12)

    # === legende interne ===
    tech_labels = ["Existing", "OCGT", "Wind", "PV"]
    tech_handles = [plt.Rectangle((0, 0), 1, 1, color=COLORS[k]) for k in tech_labels]
    legend1 = ax.legend(tech_handles, tech_labels, loc="upper right",
                        fontsize=11, frameon=True)
    ax.add_artist(legend1)

    # legenda N/B/P leggermente spostata
    storage_handles = [plt.Rectangle((0, 0), 1, 1, fc="white", ec="none", alpha=0)]
    ax.legend(
        storage_handles,
        ["N = NoStorage\nB = BESS\nP = PHES"],
        loc="upper left", fontsize=11,
        frameon=True, bbox_to_anchor=(0.05, 0.97)
    )

    # riquadro nero
    for side in ["top", "bottom", "left", "right"]:
        ax.spines[side].set_visible(True)
        ax.spines[side].set_linewidth(1.5)

    ax.grid(False)

# --- Titolo generale RIMOSSO ---
plt.savefig(PNG_OUT, dpi=300, bbox_inches="tight")
plt.close()
print(f"📁 Salvato: {PNG_OUT}")
