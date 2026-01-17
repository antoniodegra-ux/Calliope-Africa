# -*- coding: utf-8 -*-
"""
Investment / ΣGDP (2026–2040) per stato
(calcolato da results_energy_cap.csv + YAML cost files)
→ NO diesel backup
→ Transmission cost split 50/50 tra stati connessi
→ Stile grafico migliorato con legenda riquadrata
→ Scala asse y fissata tra 0 e 1.3 %
→ Stati etichettati con sigle a 3 lettere (EGY, SDN, TZA, ecc.)
"""

from pathlib import Path
import re, yaml
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ======== CONFIG ========
BASE_DIRS = {
    "2030": Path("/Users/antoniodegrazia/Desktop/run_2030_new_true"),
    "2035": Path("/Users/antoniodegrazia/Desktop/run_2035_new_true"),
    "2040": Path("/Users/antoniodegrazia/Desktop/run_2040_new_true"),
}
RESULTS_SUB = Path("results")

GDP_FILE = Path("/Users/antoniodegrazia/Downloads/GDP_per_country.xlsx")
GDP_SHEET = "Foglio1"
GDP_COL_COUNTRY = "locs"
GDP_COL_VALUE   = "GDP"  # in M$

OUT_DIR = Path("/Users/antoniodegrazia/Desktop/planning/inv_by_GDP")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV     = OUT_DIR / "INV_GDP_ratio_by_scenario.csv"
OUT_CSV_CMP = OUT_DIR / "INV_GDP_ratio_comparison.csv"

DISCOUNT_RATE = 0.10
BASE_YEAR = 2025

# ======== REGEX E FILTRI ========
PV_NEW   = re.compile(r"^PV_.*_MSR(?!.*installed$)", re.IGNORECASE)
WIND_NEW = re.compile(r"^Wind_.*_MSR(?!.*installed$)", re.IGNORECASE)
INST_END = re.compile(r"_installed$", re.IGNORECASE)

# ======== UTIL ========
def discount_to_2025(val, year):
    n = max(0, int(year) - BASE_YEAR)
    return val / ((1.0 + DISCOUNT_RATE) ** n)

def normalize_state(s: str) -> str:
    """
    Normalizza i nomi/locs degli stati alle sigle a 3 lettere
    coerenti con la mappa: LBY, EGY, SDN, SSD, ETH, ERI, DJI,
    RWA, UGA, KEN, BDI, TZA, DRC, ecc.
    """
    s = str(s).upper().strip()

    # Nord Africa / Corno
    if s.startswith(("EGY", "EGYPT")):
        return "EGY"
    if s.startswith(("LIBYA", "LYB")):
        return "LBY"
    if s.startswith(("SUDAN", "SDN")) and "SOUTH" not in s:
        return "SDN"
    if "SOUTH SUDAN" in s or s.startswith(("SSD", "S_SUDAN")) or "SOUTH_SUDAN" in s:
        return "SSD"
    if s.startswith(("ETH", "ETHIOP")):
        return "ETH"
    if s.startswith(("ERIT", "ERI")):
        return "ERI"
    if s.startswith(("DJI", "DJIB")):
        return "DJI"

    # East Africa
    if s.startswith(("KEN", "KENYA")):
        return "KEN"
    if s.startswith(("TZA", "TANZ", "TAN")):
        return "TZA"
    if s.startswith(("UGA", "UGAND")):
        return "UGA"
    if s.startswith(("RWA", "RWAN")):
        return "RWA"
    if s.startswith(("BDI", "BURUNDI")):
        return "BDI"

    # DRC
    if s.startswith(("DRC", "CONGO")):
        return "DRC"

    # Fallback: prima parte prima di "_" e primi 3 caratteri
    base = s.split("_")[0]
    return base[:3]

def read_costs_generation(tech_yaml_path: Path) -> dict:
    with open(tech_yaml_path, "r") as f:
        y = yaml.safe_load(f) or {}
    techs = (y.get("techs") or {})
    out = {}
    for t, tdef in techs.items():
        mon = ((tdef or {}).get("costs") or {}).get("monetary") or {}
        out[t] = {"capex": mon.get("energy_cap"), "om_annual": mon.get("om_annual")}
    return out

def read_tx_costs_and_distances(tx_links_yaml: Path):
    with open(tx_links_yaml, "r") as f:
        y = yaml.safe_load(f) or {}
    tx_costs = {"energy_cap": None, "energy_cap_per_distance": None}
    if "new_transmission" in (y.get("techs") or {}):
        mon = ((y["techs"]["new_transmission"]).get("costs") or {}).get("monetary") or {}
        tx_costs["energy_cap"] = mon.get("energy_cap")
        tx_costs["energy_cap_per_distance"] = mon.get("energy_cap_per_distance")
    dist_map = {}
    for pair, blob in (y.get("links") or {}).items():
        try:
            A, B = [s.strip() for s in pair.split(",")]
        except:
            continue
        key = tuple(sorted([A, B]))
        if "new_transmission" in (blob.get("techs") or {}):
            d = (blob["techs"]["new_transmission"] or {}).get("distance")
            if d is not None:
                dist_map[key] = float(d)
    return tx_costs, dist_map

def compute_investments_from_ecap(df_cap, gen_costs, tx_costs, tx_dist):
    """Calcola gli investimenti in USD per categoria, split Transmission 50/50 tra stati"""
    out = {"PV": 0.0, "Wind": 0.0, "OCGT": 0.0, "Storage": 0.0, "Transmission": 0.0}
    trans_split = {}  # accumula costi trasmissione per stato
    if df_cap.empty:
        return pd.Series(out, dtype=float), trans_split

    # generation + storage
    for _, row in df_cap.iterrows():
        tech = str(row["techs"])
        capkW = float(row["energy_cap"])
        if capkW <= 0 or INST_END.search(tech):
            continue
        if   PV_NEW.match(tech): cat = "PV"
        elif WIND_NEW.match(tech): cat = "Wind"
        elif tech == "OCGT_NG_new": cat = "OCGT"
        elif tech in ("BESS","PHES"): cat = "Storage"
        elif tech.startswith("new_transmission"):
            continue
        else:
            continue
        c = (gen_costs.get(tech) or {}).get("capex")
        if c:
            out[cat] += capkW * float(c)

    # transmission split 50/50
    pair_cap = {}
    mask_tx = pd.Series(df_cap["techs"]).astype(str).str.startswith("new_transmission", na=False)
    for _, row in df_cap[mask_tx].iterrows():
        locA = str(row["locs"]).strip()
        techf = str(row["techs"]).strip()
        capkW = float(row["energy_cap"])
        if capkW <= 0 or ":" not in techf:
            continue
        _, nodeB = techf.split(":", 1)
        nodeB = nodeB.strip()
        pair = tuple(sorted([locA, nodeB]))
        pair_cap[pair] = max(pair_cap.get(pair, 0.0), capkW)

    c_cap = tx_costs.get("energy_cap")
    c_dist = tx_costs.get("energy_cap_per_distance")
    for pair, capkW in pair_cap.items():
        d100 = tx_dist.get(pair, 0.0)
        cost = capkW * (float(c_cap) if c_cap else 0.0)
        cost += capkW * d100 * (float(c_dist) if c_dist else 0.0)
        cost_half = cost / 2.0
        for state in pair:
            trans_split[state] = trans_split.get(state, 0.0) + cost_half
        out["Transmission"] += cost  # totale (globale)
    return pd.Series(out, dtype=float), trans_split

# ======== GDP ========
gdp_df = pd.read_excel(GDP_FILE, sheet_name=GDP_SHEET)
gdp_df = gdp_df[[GDP_COL_COUNTRY, GDP_COL_VALUE]].rename(
    columns={GDP_COL_COUNTRY:"state", GDP_COL_VALUE:"GDP2025_M$"}
)
gdp_df["state"] = gdp_df["state"].apply(normalize_state)

GDP_YEARS = list(range(2026, 2041))
ratios = {}
for _, row in gdp_df.iterrows():
    s = row["state"]
    gdp2025_M = pd.to_numeric(row["GDP2025_M$"], errors="coerce")
    if not np.isfinite(gdp2025_M):
        continue
    gdp2025_B = gdp2025_M / 1000.0
    gdps = [gdp2025_B * (1.03 ** (y-2025)) for y in GDP_YEARS]
    ratios[s] = float(sum(gdps))

# ======== SCENARI ========
SCENARIOS = {
    "VRES_nostorage":     "new_trasmission_VRES_{y}_nostorage",
    "VRES_BESS":          "new_trasmission_VRES_{y}_BESS",
    "VRES_PHES":          "new_trasmission_VRES_{y}_PHES",
    "GT+VRES_nostorage":  "new_trasmission_GT+VRES_{y}_nostorage",
    "GT+VRES_BESS":       "new_trasmission_GT+VRES_{y}_BESS",
    "GT+VRES_PHES":       "new_trasmission_GT+VRES_{y}_PHES",
}

# ======== RACCOLTA INVESTIMENTI ========
def collect_scenario_totals(base_dirs, scen_template: str) -> pd.DataFrame:
    pieces = []
    for year, base in base_dirs.items():
        scen = scen_template.format(y=year)
        scen_dir = base / "run_new_trasmission" / scen
        results_dir = scen_dir / RESULTS_SUB
        cap_path = results_dir / "results_energy_cap.csv"
        tech_yaml = scen_dir / "Model_config" / "Technologies.yaml"
        tx_yaml   = scen_dir / "Model_config" / "Transmission_links.yaml"
        if not (cap_path.exists() and tech_yaml.exists() and tx_yaml.exists()):
            continue

        df_cap = pd.read_csv(cap_path)
        if "locs" not in df_cap.columns:
            continue
        df_cap["state"] = df_cap["locs"].apply(normalize_state)
        gen_costs = read_costs_generation(tech_yaml)
        tx_costs, tx_dist = read_tx_costs_and_distances(tx_yaml)

        invest_by_state = {}
        for st in df_cap["state"].unique():
            invest_by_state[st] = 0.0

        inv_df, trans_split = compute_investments_from_ecap(df_cap, gen_costs, tx_costs, tx_dist)
        total_cost_by_state = {st: 0.0 for st in invest_by_state.keys()}
        for st in total_cost_by_state:
            total_cost_by_state[st] += 0.0

        for st, val in trans_split.items():
            st_norm = normalize_state(st)
            total_cost_by_state[st_norm] = total_cost_by_state.get(st_norm, 0.0) + val

        for _, row in df_cap.iterrows():
            st = row["state"]
            tech = str(row["techs"])
            capkW = float(row["energy_cap"])
            if capkW <= 0 or INST_END.search(tech):
                continue
            if PV_NEW.match(tech):
                c = (gen_costs.get(tech) or {}).get("capex")
                if c:
                    total_cost_by_state[st] = total_cost_by_state.get(st, 0.0) + capkW*float(c)
            elif WIND_NEW.match(tech):
                c = (gen_costs.get(tech) or {}).get("capex")
                if c:
                    total_cost_by_state[st] = total_cost_by_state.get(st, 0.0) + capkW*float(c)
            elif tech == "OCGT_NG_new":
                c = (gen_costs.get(tech) or {}).get("capex")
                if c:
                    total_cost_by_state[st] = total_cost_by_state.get(st, 0.0) + capkW*float(c)
            elif tech in ("BESS","PHES"):
                c = (gen_costs.get(tech) or {}).get("capex")
                if c:
                    total_cost_by_state[st] = total_cost_by_state.get(st, 0.0) + capkW*float(c)

        df_year = pd.DataFrame({
            "state": list(total_cost_by_state.keys()),
            "invest_BUSD": [discount_to_2025(v, int(year))/1e9 for v in total_cost_by_state.values()]
        })
        pieces.append(df_year)

    if not pieces:
        return pd.DataFrame(columns=["state","Total_B$"])

    df = pd.concat(pieces, ignore_index=True)
    df = df.groupby("state", as_index=False)["invest_BUSD"].sum().rename(columns={"invest_BUSD":"Total_B$"})
    return df

# ======== GRAFICI SINGOLI ========
all_results = []
for scen_name, scen_template in SCENARIOS.items():
    df = collect_scenario_totals(BASE_DIRS, scen_template)
    if df.empty:
        continue
    df["GDPsum_BUSD"] = df["state"].map(ratios)
    df["Ratio"] = np.where(df["GDPsum_BUSD"]>0, df["Total_B$"]/df["GDPsum_BUSD"], np.nan)
    df["Ratio_percent"] = df["Ratio"] * 100
    df_plot = df.sort_values("Ratio", ascending=False)

    color_single = "#1E88E5"

    fig, ax = plt.subplots(figsize=(12,6))
    vals = df_plot["Ratio_percent"].values
    ax.bar(df_plot["state"], vals, color=color_single)
    ax.set_ylabel("Investment to GDP [%]", fontsize=13, fontweight="bold")
    ax.set_ylim(0, 1.3)  # scala fissata
    plt.xticks(rotation=45, ha="right", fontsize=12)  # ascisse un po' più grandi
    plt.tight_layout()
    out_png = OUT_DIR / f"{scen_name}_INV_GDP_ratio.png"
    plt.savefig(out_png, dpi=300)
    plt.close()
    print(f"✅ Salvato grafico: {out_png}")

    df["scenario"] = scen_name
    all_results.append(df)

# ======== CSV UNICO ========
if all_results:
    out_df = pd.concat(all_results, ignore_index=True)
    out_df.to_csv(OUT_CSV, index=False)
    print(f"✅ Salvato CSV: {OUT_CSV}")

# ======== CONFRONTO ========
def collect_ratio_total(base_dirs, scen_template: str) -> pd.DataFrame:
    df = collect_scenario_totals(base_dirs, scen_template)
    if df.empty:
        return df.assign(GDPsum_BUSD=np.nan, Ratio_Total=np.nan)
    df["GDPsum_BUSD"] = df["state"].map(ratios)
    df["Ratio_Total"] = np.where(df["GDPsum_BUSD"]>0, df["Total_B$"]/df["GDPsum_BUSD"], np.nan)
    return df[["state","Ratio_Total"]]

df_vres = collect_ratio_total(BASE_DIRS, "new_trasmission_VRES_{y}_BESS")
df_gt   = collect_ratio_total(BASE_DIRS, "new_trasmission_GT+VRES_{y}_BESS")

df_merge = pd.merge(df_vres, df_gt, on="state", how="outer", suffixes=("_VRES","_GT"))
df_merge = df_merge.sort_values("state").reset_index(drop=True)
mask_valid = np.isfinite(df_merge["Ratio_Total_VRES"]) | np.isfinite(df_merge["Ratio_Total_GT"])
df_merge = df_merge[mask_valid]

df_cmp = df_merge.copy()
df_cmp["Ratio_Total_VRES_percent"] = df_cmp["Ratio_Total_VRES"] * 100
df_cmp["Ratio_Total_GT_percent"]   = df_cmp["Ratio_Total_GT"] * 100
df_cmp["Delta_GT_minus_VRES_percent"] = df_cmp["Ratio_Total_GT_percent"] - df_cmp["Ratio_Total_VRES_percent"]
cols_order = ["state",
              "Ratio_Total_VRES", "Ratio_Total_VRES_percent",
              "Ratio_Total_GT",   "Ratio_Total_GT_percent",
              "Delta_GT_minus_VRES_percent"]
df_cmp = df_cmp[cols_order]
df_cmp.to_csv(OUT_CSV_CMP, index=False)
print(f"✅ Salvato CSV confronto: {OUT_CSV_CMP}")

# ======== GRAFICO CONFRONTO ========
fig, ax = plt.subplots(figsize=(14,6))
x = np.arange(len(df_merge["state"]))
bar_w = 0.4

color_gt   = "skyblue"
color_vres = "steelblue"

vals_gt   = (df_merge["Ratio_Total_GT"].fillna(0)*100).values
vals_vres = (df_merge["Ratio_Total_VRES"].fillna(0)*100).values

ax.bar(x - bar_w/2, vals_gt,  width=bar_w, color=color_gt,   label="GT+VRES BESS")
ax.bar(x + bar_w/2, vals_vres, width=bar_w, color=color_vres, label="VRES BESS")

ax.set_xticks(x)
ax.set_xticklabels(df_merge["state"], rotation=45, ha="right", fontsize=12)
ax.set_ylabel("Investment to GDP [%]", fontsize=18, fontweight="bold")
ax.set_ylim(0, 1.3)  # scala fissata
ax.legend(loc="upper right", fontsize=18, frameon=True)  # legenda un po' più grande

plt.tight_layout()
cmp_png = OUT_DIR / "Comparison_VRES_vs_GT_sidebyside.png"
plt.savefig(cmp_png, dpi=300)
plt.close()
print(f"✅ Salvato grafico confronto: {cmp_png}")
