import pandas as pd
from pathlib import Path

# === CONFIG: metti qui il percorso del tuo CSV ===
INPUT_CSV = r"C:\Users\ilari\OneDrive\Desktop\tesi\2030_false\run_existing\existing_VRES_2030_nostorage\results\results_unmet_demand.csv"

# Se i nomi colonna non sono esattamente "locs" e "unmet_demand",
# questi alias permettono di riconoscerli in modo flessibile.
POSSIBLE_LOCS  = ["locs", "location", "region", "paese", "country"]
POSSIBLE_UNMET = ["unmet_demand", "unmet", "unmetdemand"]

def find_column(columns, candidates):
    cols = [c.strip().lower() for c in columns]
    # match esatto
    for cand in candidates:
        if cand in cols:
            return columns[cols.index(cand)]
    # match parziale (es. "unmet_demand_total")
    for i, c in enumerate(cols):
        if any(cand in c for cand in candidates):
            return columns[i]
    raise KeyError(f"Colonna non trovata. Cercate: {candidates}. Presenti: {list(columns)}")

def main():
    csv_path = Path(INPUT_CSV)
    if not csv_path.exists():
        raise FileNotFoundError(f"File non trovato: {csv_path}")

    df = pd.read_csv(csv_path)
    locs_col  = find_column(df.columns, POSSIBLE_LOCS)
    unmet_col = find_column(df.columns, POSSIBLE_UNMET)

    # garantisce numerico; i non-numerici diventano NaN e poi 0
    df[unmet_col] = pd.to_numeric(df[unmet_col], errors="coerce").fillna(0)

    # maschere
    pos = df[unmet_col] > 0
    neg = df[unmet_col] < 0

    # --- per-locs: somme separate e totale ---
    by_locs_pos = df.loc[pos].groupby(locs_col, dropna=False)[unmet_col].sum().rename("sum_positive")
    by_locs_neg = df.loc[neg].groupby(locs_col, dropna=False)[unmet_col].sum().rename("sum_negative")

    # unisci, riempi i mancanti con 0
    by_locs = pd.concat([by_locs_pos, by_locs_neg], axis=1).fillna(0).reset_index()
    by_locs["sum_total"] = by_locs["sum_positive"] + by_locs["sum_negative"]

    # ordina per totale decrescente
    by_locs = by_locs.sort_values("sum_total", ascending=False)

    # --- totali complessivi ---
    total_pos = df.loc[pos, unmet_col].sum()
    total_neg = df.loc[neg, unmet_col].sum()
    total_all = df[unmet_col].sum()

    totals = pd.DataFrame({
        "metric": ["sum_positive", "sum_negative", "sum_total"],
        "value":  [total_pos,      total_neg,      total_all]
    })

    # --- salvataggi accanto al file di input ---
    out_by_locs = csv_path.with_name(r"resultsunmet_pos_neg_by_locs.csv")
    out_totals  = csv_path.with_name(r"resultsunmet_pos_neg_totals.csv")
    by_locs.to_csv(out_by_locs, index=False)
    totals.to_csv(out_totals, index=False)

    # stampa breve
    print(f"✅ Salvato per-locs: {out_by_locs}")
    print(f"✅ Salvato totali:   {out_totals}")
    print("\nTotali complessivi:")
    print(totals.to_string(index=False))
    print("\nPrime 10 righe per-locs:")
    print(by_locs.head(10).to_string(index=False))

if __name__ == "__main__":
    main()
