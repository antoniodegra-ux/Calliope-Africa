import pandas as pd

# === CONFIG ===
CSV_PATH = r"C:\Users\ilari\OneDrive\Desktop\tesi\2030_false\run_existing\existing_VRES_2030_nostorage\results\results_carrier_prod.csv"  # <-- aggiorna qui
STATE    = "Egypt_ME"   # <-- cambia con il nome dello stato che vuoi analizzare

# Prefissi delle tecnologie di trasmissione da considerare
TRANS_PREFIXES = ["132_kV", "220_kV", "400_kV", "500_kV", "transmission_2030_installed"]

# Stampa anche il dettaglio per controparte?
SHOW_BREAKDOWN = True

# === FUNZIONE ===
def calc_imports(csv_path, state, prefixes, show_breakdown=False):
    # Carica il file
    df = pd.read_csv(csv_path, low_memory=False)

    # Coercizione a stringa
    locs = df["locs"].astype(str)
    techs = df["techs"].astype(str)

    # Filtra locazioni dello stato
    m_state = locs.str.startswith(state)

    # Filtra tecnologie che **iniziano** con uno dei prefissi (es. "220_kV:DEST")
    m_tech = False
    for p in prefixes:
        m_tech = m_tech | techs.str.startswith(p)

    # Considera solo gli import: carrier_prod > 0
    m_import = df["carrier_prod"] > 0

    df_imp = df.loc[m_state & m_tech & m_import].copy()

    # Somma e converte da kWh a GWh
    total_import_gwh = df_imp["carrier_prod"].sum() / 1e6

    # Breakdown per controparte
    if show_breakdown and not df_imp.empty:
        df_imp["orig"] = df_imp["techs"].str.split(":", n=1).str[1].fillna("installed/unspecified")
        by_orig = (df_imp.groupby("orig")["carrier_prod"].sum() / 1e6).sort_values(ascending=False)
        print("\nImport per controparte (GWh):")
        for orig, val in by_orig.items():
            print(f"  {orig:25s} {val:,.2f}")

    return total_import_gwh

# === ESECUZIONE ===
imports = calc_imports(CSV_PATH, STATE, TRANS_PREFIXES, show_breakdown=SHOW_BREAKDOWN)
print(f"\nTotale import di {STATE}: {imports:.2f} GWh")
