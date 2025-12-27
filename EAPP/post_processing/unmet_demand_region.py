import pandas as pd

# === CONFIGURAZIONE ===
input_csv = "/Users/antoniodegrazia/Desktop/run_2030_new_true/run_new_trasmission/new_trasmission_VRES_2030_nostorage/results/results_unmet_demand.csv"

# === CARICAMENTO E PULIZIA ===
df = pd.read_csv(input_csv)
df.columns = df.columns.str.strip()

# === FILTRA SOLO I VALORI POSITIVI DI UNMET DEMAND ===
df_positive = df[df["unmet_demand"] > 0]

# === CALCOLO SOMMA UNMET DEMAND PER REGIONE (SOLO POSITIVI) ===
summary_table = df_positive.groupby("locs")["unmet_demand"].sum().reset_index()

# === RINOMINA COLONNE E ORDINA ===
summary_table.columns = ["Regione", "Unmet Demand Totale Positiva (kWh)"]
summary_table = summary_table.sort_values(by="Unmet Demand Totale Positiva (kWh)", ascending=False)

# === SALVATAGGIO SU FILE CSV ===
summary_table.to_csv("/Users/antoniodegrazia/Desktop/post_processing/unmet_demand_per_regione_2030_phes.csv", index=False)

# === OPZIONALE: STAMPA A SCHERMO ===
print(summary_table)
