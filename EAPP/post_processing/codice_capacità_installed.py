import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import re

# === Percorso principale ===
# === Percorso principale ===
main_folder = "/Users/antoniodegrazia/Desktop/run_2030_new_true"
run_folders = {
    "autarky": "run_autarky",
    "existing": "run_existing",

    "new_transmission": "run_new_trasmission",  # la cartella reale si chiama così
}
output_folder = os.path.join(main_folder, "planning", "grafici")
os.makedirs(output_folder, exist_ok=True)

# === Classificazione tecnologica (senza trasmissione) ===
def classify_tech(tech):
    tech_lower = tech.lower()
    if "new_transmission" in tech_lower or "transmission_2030_installed" in tech_lower or "_kv" in tech_lower:
        return None  # Escludi trasmissione
    if "transmission" in tech_lower or "final_demand" in tech_lower:
        return None
    if "solar" in tech_lower or "pv" in tech_lower:
        return "Solar"
    if "wind" in tech_lower:
        return "Wind"
    if "hydro" in tech_lower:
        return "Hydro"
    if "ocgt" in tech_lower:
        return "OCGT"
    if "phes" in tech_lower:
        return "PHES"
    if "bess" in tech_lower:
        return "BESS"
    return "Other"

# === Ordine tecnologie (PHES e BESS alla fine) ===
tech_order = ["Solar", "Wind", "Hydro", "OCGT", "Other", "PHES", "BESS"]

# === Funzione principale per ogni macro-cartella ===
def process_macro_folder(label, folder_name):
    full_path = os.path.join(main_folder, folder_name)
    scenarios = [d for d in os.listdir(full_path) if os.path.isdir(os.path.join(full_path, d))]
    records = []

    for scenario in scenarios:
        folder = os.path.join(full_path, scenario, "results")
        try:
            energy_cap = pd.read_csv(os.path.join(folder, "results_energy_cap.csv"))
            input_cap = pd.read_csv(os.path.join(folder, "inputs_energy_cap_equals.csv"))
            merged = pd.merge(energy_cap, input_cap, on=["techs", "locs"], how="left")
            merged["energy_cap_equals"] = merged["energy_cap_equals"].fillna(0)
            merged["new_capacity"] = merged["energy_cap"] - merged["energy_cap_equals"]
            merged["category"] = merged["techs"].apply(classify_tech)
            merged = merged[merged["category"].notna()]
            grouped = merged.groupby("category")[["energy_cap_equals", "new_capacity"]].sum().reset_index()
            grouped["Scenario"] = scenario
            records.append(grouped)
            print(f"✅ {label} — Caricato: {scenario}")
        except Exception as e:
            print(f"⚠️ {label} — Errore in {scenario}: {e}")

    if not records:
        print(f"⚠️ Nessun dato trovato per {label}")
        return

    # === Combina ===
    df = pd.concat(records)
    df["Existing"] = df["energy_cap_equals"] * 1e-6  # kW to GW
    df["New"] = df["new_capacity"] * 1e-6
    df = df[["Scenario", "category", "Existing", "New"]]

    scenarios_order = sorted(df["Scenario"].unique())

    # Completa combinazioni
    full_index = pd.MultiIndex.from_product([scenarios_order, tech_order], names=["Scenario", "category"])
    df = df.set_index(["Scenario", "category"]).reindex(full_index, fill_value=0).reset_index()

    # === Colori coerenti ===
    base_colors = sns.color_palette("tab10", n_colors=len(tech_order))
    color_map = dict(zip(tech_order, base_colors))

    # === Plot ===
    sns.set_style("whitegrid")
    fig, ax = plt.subplots(figsize=(18, 8))

    bar_width = 0.06
    n_tech = len(tech_order)
    n_scenarios = len(scenarios_order)

    for j, scenario in enumerate(scenarios_order):
        scenario_data = df[df["Scenario"] == scenario]
        for i, tech in enumerate(tech_order):
            row = scenario_data[scenario_data["category"] == tech]
            if row.empty:
                continue
            existing = row["Existing"].values[0]
            new = row["New"].values[0]
            xpos = j + (i - n_tech / 2) * bar_width
            ax.bar(xpos, existing, width=bar_width, label=f"{tech} (Existing)", color=color_map[tech])
            ax.bar(xpos, new, width=bar_width, bottom=existing, label=f"{tech} (New)", color=color_map[tech], alpha=0.4)

    # === Layout ===
    ax.set_xticks(np.arange(n_scenarios))
    ax.set_xticklabels(scenarios_order, rotation=45)
    ax.set_ylabel("Installed Capacity [GW]")
    ax.set_title(f"Installed Capacity by Technology — {label.capitalize()} (No Transmission)")

    # Legenda pulita
    handles, labels = ax.get_legend_handles_labels()
    unique = dict()
    for h, l in zip(handles, labels):
        if l not in unique:
            unique[l] = h
    ax.legend(unique.values(), unique.keys(), bbox_to_anchor=(1.02, 1), loc="upper left")

    plt.tight_layout()

    # === Salva ===
    output_path = os.path.join(output_folder, f"capacity_{label}_no_transmission.png")
    plt.savefig(output_path)
    plt.close()
    print(f"📁 Grafico salvato: {output_path}")

# === Esegui per ogni gruppo ===
for label, folder in run_folders.items():
    process_macro_folder(label, folder)
