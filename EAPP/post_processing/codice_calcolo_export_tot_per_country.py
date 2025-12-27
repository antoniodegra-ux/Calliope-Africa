import pandas as pd

# === CONFIG ===
CSV_PATH = r"C:\Users\ilari\OneDrive\Desktop\tesi\2030_true\run_2030_new_contrue\run_autarky\autarky_VRES_2030_nostorage\results\results_carrier_con.csv"  # <-- aggiorna qui
STATE    = "Egypt_UE"   # <-- cambia con il nome dello stato che vuoi analizzare

# Prefissi delle tecnologie di trasmissione da considerare
TRANS_PREFIXES = ["132_kV", "220_kV", "400_kV", "500_kV", "transmission_2030_installed"]

# Stampa anche il dettaglio per controparte?
SHOW_BREAKDOWN = True

# === FUNZIONE ===
def calc_exports(csv_path, state, prefixes, show_breakdown=False):
    # Carica il file
    df = pd.read_csv(csv_path, low_memory=False)

    # Coercizione a stringa per sicurezza
    locs = df["locs"].astype(str)
    techs = df["techs"].astype(str)

    # Filtra locazioni dello stato (es. "Egypt_ME", "Egypt_ME_...")
    m_state = locs.str.startswith(state)

    # Filtra tecnologie che **iniziano** con uno dei prefissi (gestisce anche "220_kV:DEST")
    m_tech = False
    for p in prefixes:
        m_tech = m_tech | techs.str.startswith(p)

    # Considera solo gli export (carrier_con < 0)
    m_export = df["carrier_con"] < 0

    df_exp = df.loc[m_state & m_tech & m_export].copy()

    # Somma e converte da kWh a GWh; metto il segno positivo sugli export
    total_export_gwh = -df_exp["carrier_con"].sum() / 1e6

    # Breakdown per controparte (parte dopo i due punti nel nome tech), opzionale
    if show_breakdown and not df_exp.empty:
        # Estrae la destinazione se presente: "220_kV:Egypt_AL" -> "Egypt_AL"
        df_exp["dest"] = df_exp["techs"].str.split(":", n=1).str[1].fillna("installed/unspecified")
        by_dest = (-df_exp.groupby("dest")["carrier_con"].sum() / 1e6).sort_values(ascending=False)
        print("\nExport per controparte (GWh):")
        for dest, val in by_dest.items():
            print(f"  {dest:25s} {val:,.2f}")

    return total_export_gwh

# === ESECUZIONE ===
exports = calc_exports(CSV_PATH, STATE, TRANS_PREFIXES, show_breakdown=SHOW_BREAKDOWN)
print(f"\nTotale export di {STATE}: {exports:.2f} GWh")
