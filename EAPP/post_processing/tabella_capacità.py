# -*- coding: utf-8 -*-
import pandas as pd
import matplotlib.pyplot as plt

# === 1. Carica CSV ===
file_path = "/Users/antoniodegrazia/Desktop/run_2040_new_true/run_existing/existing_VRES_2040_nostorage/results/results_energy_cap.csv"   # <-- cambia percorso se serve
df = pd.read_csv(file_path)

# === 2. Filtra nuove installazioni (MSR + OCGT_NG_new + installed) ===
mask = df["techs"].str.contains("MSR|OCGT_NG_new", case=False, na=False)
df_new = df[mask].copy()

# === 3. Funzione per accorpare sottoregioni ===
def normalize_country(loc):
    if loc.startswith("Egypt"):
        return "Egypt"
    elif loc.startswith("DRC"):
        return "DRC"
    elif loc.startswith("TAN"):
        return "Tanzania"
    elif loc.startswith("KEN"):
        return "Kenya"
    elif loc.startswith("Sudan"):
        return "Sudan"
    elif loc.startswith("Ethiopia"):
        return "Ethiopia"
    elif loc.startswith("Burundi"):
        return "Burundi"
    elif loc.startswith("Djibouti"):
        return "Djibouti"
    elif loc.startswith("Eritrea"):
        return "Eritrea"
    elif loc.startswith("Libya"):
        return "Libya"
    elif loc.startswith("Rwanda"):
        return "Rwanda"
    elif loc.startswith("Uganda"):
        return "Uganda"
    elif loc.startswith("SouthSudan") or loc.startswith("SSD"):
        return "South Sudan"
    else:
        return loc

df_new["country"] = df_new["locs"].apply(normalize_country)

# === 4. Raggruppa e somma capacità ===
df_summary = df_new.groupby("country")["energy_cap"].sum().reset_index()

# === 5. Converti kW → GW ===
df_summary["energy_cap_GW"] = df_summary["energy_cap"] / 1e6

# === 6. Ordina per capacità ===
df_summary = df_summary.sort_values(by="energy_cap_GW", ascending=False)

# === 7. Salva la tabella come immagine ===
fig, ax = plt.subplots(figsize=(8, 6))
ax.axis("off")
tbl = ax.table(cellText=df_summary.values,
               colLabels=df_summary.columns,
               loc="center",
               cellLoc="center")
tbl.auto_set_font_size(False)
tbl.set_fontsize(10)
tbl.scale(1.2, 1.2)

table_path = "/Users/antoniodegrazia/Desktop/planning/table.png"
plt.savefig(table_path, bbox_inches="tight")
plt.close()

# === 8. Grafico a barre ===
plt.figure(figsize=(10,6))
plt.bar(df_summary["country"], df_summary["energy_cap_GW"], color="skyblue")
plt.ylabel("Installed Capacity [GW]")
plt.title("New Installations by Country (MSR + OCGT_NG_new)")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()

barplot_path = "/Users/antoniodegrazia/Desktop/planning/new_installations_barplot.png"
plt.savefig(barplot_path, dpi=300)
plt.close()

print(f"✅ Tabella salvata in: {table_path}")
print(f"✅ Grafico salvato in: {barplot_path}")
