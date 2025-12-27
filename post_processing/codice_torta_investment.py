# -*- coding: utf-8 -*-
"""
Pie chart investimenti per Stato (sommati 2030+2035+2040)
Investimenti calcolati da capacity * costi unitari (no valori ammortizzati)
- Tecnologie considerate: PV_MSR, Wind_MSR, BESS, PHES, OCGT_NG_new, new_transmission*
- Aggrega regioni di KEN, TAN, EGYPT, DRC
- Per le linee inter-state, l'investimento è ripartito 50 %-50 % tra i due stati
- Output: 6 PNG (uno per scenario) per lo stato scelto
"""

from pathlib import Path
import re, yaml
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ========= CONFIG =========
BASE_DIRS = {
    "2030": Path("/Users/antoniodegrazia/Desktop/run_2030_new_true"),
    "2035": Path("/Users/antoniodegrazia/Desktop/run_2035_new_true"),
    "2040": Path("/Users/antoniodegrazia/Desktop/run_2040_new_true"),
}
RESULTS_SUB = Path("results")
ECAP_FILE = "results_energy_cap.csv"

TARGET_STATE = "Eritrea"  # <-- cambia qui (in maiuscolo)
OUT_DIR = Path("/Users/antoniodegrazia/Desktop/post_processing")
OUT_DIR.mkdir(parents=True, exist_ok=True)

SCENARIOS = {
    "VRES_nostorage":     "autarky_VRES_{y}_nostorage",
    "VRES_BESS":          "autarky_VRES_{y}_BESS",
    "VRES_PHES":          "autarky_VRES_{y}_PHES",
    "GT+VRES_nostorage":  "autarky_GT+VRES_{y}_nostorage",
    "GT+VRES_BESS":       "autarky_GT+VRES_{y}_BESS",
    "GT+VRES_PHES":       "autarky_GT+VRES_{y}_PHES",
}

# ========= REGEX & COLORI =========
PV_NEW        = re.compile(r"^PV_.*_MSR(?!.*installed$)", re.IGNORECASE)
WIND_NEW      = re.compile(r"^Wind_.*_MSR(?!.*installed$)", re.IGNORECASE)
INSTALLED_END = re.compile(r"_installed$", re.IGNORECASE)

COLORS = {"OCGT":"#e9967a","PV":"#ffd966","Storage":"#b6d7a8","Wind":"#c9daf8","Transmission":"#999999"}

DISCOUNT_RATE = 0.10
BASE_YEAR = 2025

# ========= FUNZIONI DI SUPPORTO =========
def normalize_state(s: str) -> str:
    s = str(s).upper().split("_")[0]
    if s.startswith("KEN"): return "KEN"
    if s.startswith("TAN"): return "TAN"
    if s.startswith("EGY"): return "EGYPT"
    if s.startswith("DRC"): return "DRC"
    return s

def discount_to_2025(val_usd: float, year: int) -> float:
    n = max(0, int(year) - BASE_YEAR)
    return val_usd / ((1.0 + DISCOUNT_RATE) ** n)

def read_costs_generation(tech_yaml_path: Path) -> dict:
    with open(tech_yaml_path, "r") as f:
        y = yaml.safe_load(f)
    techs = (y or {}).get("techs", {}) or {}
    costs = {}
    for tname, tdef in techs.items():
        mon = (((tdef or {}).get("costs") or {}).get("monetary") or {})
        cap = mon.get("energy_cap")
        if cap is not None:
            costs[tname] = {"energy_cap": cap}
    return costs

def read_tx_costs_and_distances(tx_links_yaml: Path):
    with open(tx_links_yaml, "r") as f:
        y = yaml.safe_load(f) or {}
    tx_costs = {"energy_cap": None, "energy_cap_per_distance": None}
    top_techs = (y.get("techs") or {})
    if "new_transmission" in top_techs:
        mon = (((top_techs["new_transmission"] or {}).get("costs") or {}).get("monetary") or {})
        tx_costs["energy_cap"] = mon.get("energy_cap")
        tx_costs["energy_cap_per_distance"] = mon.get("energy_cap_per_distance")
    dist_map = {}
    for pair, blob in (y.get("links") or {}).items():
        try: A,B = [s.strip() for s in pair.split(",")]
        except: continue
        key = tuple(sorted([A,B]))
        techs = (blob or {}).get("techs",{}) or {}
        if "new_transmission" in techs:
            d = (techs["new_transmission"] or {}).get("distance")
            if d is not None:
                dist_map[key] = float(d)
    return tx_costs, dist_map

def compute_investment_per_state(df_cap: pd.DataFrame, gen_costs_yaml: dict,
                                 tx_costs: dict, tx_dist_100km: dict,
                                 year: int) -> pd.DataFrame:
    out_rows = []
    if df_cap.empty: return pd.DataFrame(columns=["state","category","invest_M$"])
    df = df_cap.copy()
    df["techs"] = df["techs"].astype(str)
    df["energy_cap"] = pd.to_numeric(df["energy_cap"], errors="coerce").fillna(0.0)
    df["state"] = df["locs"].apply(normalize_state)

    # --- GENERAZIONE + STORAGE ---
    for _, row in df.iterrows():
        tech = row["techs"]
        capkW = row["energy_cap"]
        state = row["state"]
        if capkW <= 0 or INSTALLED_END.search(tech): continue

        if PV_NEW.match(tech): cat = "PV"
        elif WIND_NEW.match(tech): cat = "Wind"
        elif tech == "OCGT_NG_new": cat = "OCGT"
        elif tech in ("BESS","PHES"): cat = "Storage"
        else: continue

        c = (gen_costs_yaml.get(tech) or {}).get("energy_cap")
        if c is None: continue
        inv_usd = capkW * float(c)
        inv_disc = discount_to_2025(inv_usd, year)
        out_rows.append((state, cat, inv_disc / 1e6))  # M$

    # --- TRANSMISSION (ripartita 50% per nodo) ---
    mask_tx = df["techs"].str.startswith("new_transmission", na=False)
    pair_cap = {}
    for _, row in df[mask_tx].iterrows():
        locA = str(row["locs"]).strip()
        tech_full = str(row["techs"]).strip()
        capkW = float(row["energy_cap"])
        if capkW <= 0 or ":" not in tech_full: continue
        _, nodeB = tech_full.split(":", 1)
        nodeB = nodeB.strip()
        pair = tuple(sorted([locA, nodeB]))
        pair_cap[pair] = max(pair_cap.get(pair,0.0), capkW)

    c_cap = tx_costs.get("energy_cap")
    c_per_dist = tx_costs.get("energy_cap_per_distance")
    for pair, capkW in pair_cap.items():
        dist_100km = tx_dist_100km.get(pair, 0.0)
        inv_cap = capkW * float(c_cap or 0)
        inv_per_dist = capkW * dist_100km * float(c_per_dist or 0)
        inv_disc = discount_to_2025(inv_cap + inv_per_dist, year)
        share = inv_disc / 2.0  # metà a ciascun nodo
        for node in pair:
            st = normalize_state(node)
            out_rows.append((st,"Transmission",share / 1e6))
    return pd.DataFrame(out_rows, columns=["state","category","invest_M$"])

def collect_state_investments(base_dirs, scen_template: str, target_state: str) -> pd.DataFrame:
    pieces = []
    for year, base in base_dirs.items():
        scen = scen_template.format(y=year)
        scen_dir = base / "run_autarky" / scen
        results_dir = scen_dir / RESULTS_SUB
        ecap_path = results_dir / ECAP_FILE
        if not ecap_path.exists(): continue

        tech_yaml = scen_dir / "Model_config" / "Technologies.yaml"
        tx_yaml   = scen_dir / "Model_config" / "Transmission_links.yaml"
        if not tech_yaml.exists() or not tx_yaml.exists(): continue

        df_cap = pd.read_csv(ecap_path)
        gen_costs_yaml = read_costs_generation(tech_yaml)
        tx_costs, tx_dist_100km = read_tx_costs_and_distances(tx_yaml)
        df_inv = compute_investment_per_state(df_cap, gen_costs_yaml, tx_costs, tx_dist_100km, int(year))
        df_state = df_inv[df_inv["state"] == target_state.upper()]
        pieces.append(df_state)
    if not pieces:
        return pd.DataFrame(columns=["category","Total_M$"])
    df = pd.concat(pieces, ignore_index=True)
    return df.groupby("category", as_index=False)["invest_M$"].sum().rename(columns={"invest_M$":"Total_M$"})

def plot_donut(df: pd.DataFrame, title: str, out_path: Path):
    fig, ax = plt.subplots(figsize=(6,6))
    if df.empty or df["Total_M$"].sum() == 0:
        ax.text(0.5,0.5,"No Data",ha="center",va="center")
        ax.axis("off")
        plt.savefig(out_path,dpi=300,bbox_inches="tight"); plt.close(); return

    values = df["Total_M$"].to_numpy()
    labels = df["category"].tolist()
    colors = [COLORS.get(l,"#cccccc") for l in labels]

    wedges, _ = ax.pie(values, labels=None, startangle=90, colors=colors)
    centre_circle = plt.Circle((0,0),0.70,fc='white')
    fig.gca().add_artist(centre_circle)

    total_val = values.sum()
    ax.text(0,0,f"{total_val:,.0f} M$".replace(","," "),
            ha="center",va="center",fontsize=13,fontweight="bold")

    legend_labels = [f"{lab}: {val/total_val*100:.1f}%"
                     for lab,val in zip(labels,values)]
    ax.legend(wedges, legend_labels, loc="center left", bbox_to_anchor=(1,0.5))
    ax.set_title(title.upper(), fontsize=13, fontweight="bold")

    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✅ Salvato: {out_path}")

# ===== MAIN =====
for scen_name, scen_template in SCENARIOS.items():
    df_state = collect_state_investments(BASE_DIRS, scen_template, TARGET_STATE)
    plot_donut(df_state, TARGET_STATE, OUT_DIR / f"{TARGET_STATE}_{scen_name}_pie.png")
