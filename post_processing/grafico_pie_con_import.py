# -*- coding: utf-8 -*-
"""
Grafico a torta degli import per una data regione
Correzione robusta del parsing origine/destinazione
"""

import pandas as pd
import matplotlib.pyplot as plt
import re
from pathlib import Path

# ====== CONFIGURAZIONE ======
FILE = Path("/Users/antoniodegrazia/Desktop/run_2030_new_true/run_new_trasmission/new_trasmission_VRES_2030_nostorage/results/results_carrier_prod.csv")  # <-- percorso file
SELECTED_LOC = "Ethiopia"   # <-- cambia qui la regione di interesse
OUT_DIR = Path("/Users/antoniodegrazia/Desktop/plots")
OUT_DIR.mkdir(exist_ok=True)

# ====== COLORI TESI ======
COLORS = {
    "PV_MSR": "#f9d057",
    "Wind_MSR": "#6baed6",
    "OCGT_NG_new": "#e34a33",
    "BESS": "#7fc97f",
    "PHES": "#31a354",
    "Import": "#9e9e9e",
}

# ====== LETTURA DATI ======
df = pd.read_csv(FILE)

# Escludi solo storage (manteniamo la trasmissione)
exclude_keywords = ["BESS", "PHES"]
mask = ~df["techs"].str.contains("|".join(exclude_keywords), case=False, na=False)
df = df[mask].copy()

# ====== FILTRO LINEE DI TRASMISSIONE ======
trans_mask = df["techs"].str.contains("transmission", case=False, na=False)
imports = df[trans_mask].copy()

# Parsing robusto dei link (es. "transmission_2035_installed_egypt-sudan")
def parse_link(tech):
    try:
        # prendo l'ultimo gruppo tipo "egypt-sudan" o "egypt_sudan"
        part = tech.split("_")[-1]
        m = re.split(r"[-_]", part)
        if len(m) >= 2:
            return m[0].capitalize(), m[1].capitalize()
    except Exception:
        pass
    return (None, None)

from_list, to_list = zip(*[parse_link(t) for t in imports["techs"]])
imports["from"] = from_list
imports["to"] = to_list

# ====== FILTRO PER REGIONE SELEZIONATA ======
imports_sel = imports[imports["locs"].str.contains(SELECTED_LOC, case=False, na=False)]

# ====== SOMMA IMPORT PER ORIGINE ======
imports_sum = (
    imports_sel.groupby("from")["carrier_prod"]
    .sum()
    .sort_values(ascending=False)
)

# ====== GRAFICO A TORTA ======
if imports_sum.empty:
    print(f"Nessun import trovato per {SELECTED_LOC}")
else:
    plt.figure(figsize=(6, 6))
    wedges, texts, autotexts = plt.pie(
        imports_sum,
        labels=imports_sum.index,
        autopct='%1.1f%%',
        startangle=90,
        colors=[COLORS["Import"]] * len(imports_sum),
        textprops={'fontsize': 11}
    )

    plt.title(f"Import share by origin region — {SELECTED_LOC}",
              fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUT_DIR / f"import_share_{SELECTED_LOC}.png", dpi=300)
    plt.show()
