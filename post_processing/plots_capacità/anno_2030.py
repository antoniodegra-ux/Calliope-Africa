# -*- coding: utf-8 -*-
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
from pathlib import Path

# ========= PATH (solo 2030) =========
ROOT_2030 = Path("/Users/antoniodegrazia/Desktop/run_2030_new_false/run_autarky")

# Dove salvare il grafico
OUT_DIR = Path("/Users/antoniodegrazia/Desktop/planning/grafici")
OUT_DIR.mkdir(parents=True, exist_ok=True)
PNG_OUT = OUT_DIR / "new_trasmission_capacity_2030.png"

# ========= COLORI =========
COLORS = {
    "Existing": "#9467bd",  # viola
    "OCGT":    "#ff9999",   # rosso chiaro
    "Wind":    "#66c2ff",   # celeste
    "PV":      "#ffd966",   # giallo chiaro
}

ORDER_FAMILY   = ["VRES", "VRES+GT"]
ORDER_STORAGE  = ["N", "B", "P"]  # N=NoStorage, B=BESS, P=PHES

def parse_scenario_name(name: str):
    """
    Funziona con nomi tipo:
      - vres_bess_2030
      - vres+gt_nostorage_2030
      - new_trasmission_VRES_2030_BESS
      - new_trasmission_GT+VRES_2030_nostorage
    """
    s = name.lower()

    # family
    if ("gt+vres" in s) or ("vres+gt" in s):
        family = "VRES+GT"
    elif "vres" in s:
        family = "VRES"
    else:
        family = "?"

    # storage tag
    if   "nostorage" in s:
        tag = "N"
    elif "bess" in s:
        tag = "B"
    elif "phes" in s:
        tag = "P"
    else:
        tag = "?"

    return family, tag

# ---------- Existing fisso GLOBALE ----------
def load_existing_global(root_2030: Path) -> float:
    """
    Cerca tra le sottocartelle il PRIMO inputs_energy_cap_equals.csv valido
    e somma tutte le capacity equals (kW -> GW) escludendo storage/transmission/final_demand/_kv.
    Così non dipende dal nome della cartella né dall'ordine.
    """
    if not root_2030.is_dir():
        return 0.0

    for scen_dir in sorted([p for p in root_2030.iterdir() if p.is_dir()]):
        eq_path = scen_dir / "results" / "inputs_energy_cap_equals.csv"
        if not eq_path.exists():
            continue
        try:
            df_eq = pd.read_csv(eq_path)
        except Exception:
            continue

        # normalizza nome colonna
        if "energy_cap_equals" not in df_eq.columns and "value" in df_eq.columns:
            df_eq = df_eq.rename(columns={"value": "energy_cap_equals"})

        if "techs" not in df_eq.columns:
            continue

        tech_lower = df_eq["techs"].astype(str).str.lower()
        # escludi: storage, transmission, domande finali, linee _kv
        mask = ~(tech_lower.str.contains("bess|phes|transmission|final_demand|_kv"))
        val = df_eq.loc[mask, "energy_cap_equals"].sum() / 1e6  # kW→GW
        return float(val)

    # se non ha trovato nulla
    return 0.0

# ---------- Nuove capacità per singolo scenario ----------
def load_new_caps_one_scenario(results_dir: Path) -> dict:
    """
    Ritorna nuove capacità (GW) per OCGT/Wind/PV = (energy_cap - energy_cap_equals).
    Se manca inputs_energy_cap_equals.csv assume 0 come equals.
    """
    ec_csv = results_dir / "results_energy_cap.csv"
    eq_csv = results_dir / "inputs_energy_cap_equals.csv"
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
        # crea equals=0 sugli stessi tech/locs
        df_eq = df_ec[["techs", "locs"]].copy()
        df_eq["energy_cap_equals"] = 0.0

    # merge e differenza
    df = pd.merge(df_ec, df_eq, on=["techs", "locs"], how="left")
    df["energy_cap_equals"] = df["energy_cap_equals"].fillna(0.0)
    df["new_capacity"] = df["energy_cap"] - df["energy_cap_equals"]

    def sum_new(substr):
        return (
            df.loc[df["techs"].astype(str).str.lower().str.contains(substr), "new_capacity"]
            .sum() / 1e6
        )

    return {
        "OCGT": sum_new("ocgt"),
        "Wind": sum_new("wind"),
        "PV":   sum_new("pv"),
    }

def additions_df_for_2030(root: Path) -> pd.DataFrame:
    """
    Costruisce una tabella MultiIndex (Family, Tag) con colonne OCGT/Wind/PV (GW).
    Riempie con 0 gli scenari mancanti.
    """
    rows = {}
    if root.is_dir():
        for scen_dir in sorted([p for p in root.iterdir() if p.is_dir()]):
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

# ========= CARICAMENTO DATI =========
# stampa di debug per vedere cosa viene trovato
print("== Scenari trovati e parsing ==")
if ROOT_2030.is_dir():
    for scen_dir in sorted([p for p in ROOT_2030.iterdir() if p.is_dir()]):
        family, tag = parse_scenario_name(scen_dir.name)
        has_results = (scen_dir / "results").is_dir()
        has_ec  = (scen_dir / "results" / "results_energy_cap.csv").exists()
        has_eq  = (scen_dir / "results" / "inputs_energy_cap_equals.csv").exists()
        print(f"- {scen_dir.name:45s} -> family={family:7s} tag={tag} | results={has_results} ec={has_ec} eq={has_eq}")

EXISTING_FIXED_GW = load_existing_global(ROOT_2030)
print(f"\nExisting (GW) usato per tutte le barre: {EXISTING_FIXED_GW:.3f}\n")

add_2030 = additions_df_for_2030(ROOT_2030)
df_2030 = add_2030.copy()
df_2030["Existing"] = EXISTING_FIXED_GW
df_2030 = df_2030[["Existing", "OCGT", "Wind", "PV"]]

# ========= PLOT =========
mpl.rcParams.update({
    "font.size": 16,
    "axes.labelsize": 18,
    "axes.labelweight": "bold",
    "axes.titlesize": 24,
    "axes.titleweight": "bold",
    "axes.linewidth": 2.0,
    "xtick.labelsize": 16,
    "ytick.labelsize": 16,
    "xtick.major.width": 1.5,
    "ytick.major.width": 1.5,
    "legend.frameon": True,
})

fig, ax = plt.subplots(figsize=(9.5, 7.8))

# “stacco” visivo tra VRES e VRES+GT
group_gap = 0.9
x_vres    = np.arange(0, 3)                 # N, B, P
x_vres_gt = np.arange(0, 3) + 3 + group_gap # N, B, P dopo il gap
x_all     = np.concatenate([x_vres, x_vres_gt])
x_ticklbl = ["N", "B", "P", "N", "B", "P"]

# stack (Existing, OCGT, Wind, PV)
bottom = np.zeros_like(x_all, dtype=float)
for cat in ["Existing", "OCGT", "Wind", "PV"]:
    vals = np.array(
        [df_2030.loc[("VRES", t), cat] for t in ORDER_STORAGE] +
        [df_2030.loc[("VRES+GT", t), cat] for t in ORDER_STORAGE]
    )
    ax.bar(
        x_all, vals, bottom=bottom, color=COLORS[cat], width=0.75,
        edgecolor="white", linewidth=0.8, label=cat
    )
    bottom += vals

# asse e look
ax.set_title("2030", pad=10)
ax.set_xlim(-0.75, x_all[-1] + 0.75)
ax.set_ylabel("Capacity [GW]")

ymax = max(125, np.ceil(bottom.max() / 10) * 10) if bottom.size else 10
ax.set_ylim(0, ymax * 1.05)
ax.grid(axis="y", linestyle=":", alpha=0.45)
for spine in ["top", "right"]:
    ax.spines[spine].set_visible(False)

# tick e label dei due gruppi
ax.set_xticks(x_all)
ax.set_xticklabels(x_ticklbl)
ax.text(x_vres.mean(),    -ymax * 0.08, "VRES",    ha="center", va="top", fontsize=18)
ax.text(x_vres_gt.mean(), -ymax * 0.08, "VRES+GT", ha="center", va="top", fontsize=18)

# ===== legenda spostata a destra (fuori dal grafico) =====
handles, labels = ax.get_legend_handles_labels()
leg = fig.legend(
    handles, labels,
    loc="center left", bbox_to_anchor=(1.02, 0.5),
    frameon=True, fontsize=15
)
leg.get_frame().set_edgecolor("0.8")

# titolo generale
fig.suptitle("new_trasmssion 2030: Capacity [GW]", fontsize=28, weight="bold", y=1.02)

# lascia margine a destra per la legenda
plt.tight_layout(rect=[0, 0, 0.88, 1])
plt.savefig(PNG_OUT, dpi=300, bbox_inches="tight")
plt.close()
print(f"📁 Salvato: {PNG_OUT}")
