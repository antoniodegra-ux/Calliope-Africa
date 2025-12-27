# -*- coding: utf-8 -*-
import pandas as pd
import matplotlib.pyplot as plt
import os

# === CONFIG ===
CSV_PATH = "/Users/antoniodegrazia/Desktop/run_2040_new_true/run_autarky/common_inputs/Timeseries/Demand.csv"
OUT_DIR = "/Users/antoniodegrazia/Desktop/planning"

# Dictionary to aggregate subregions into main countries
AGGREGATIONS = {
    "Egypt": ["Egypt_UE", "Egypt_ME", "Egypt_NE", "Egypt_AL", "Egypt_CR", "Egypt_CN"],
    "Kenya": ["KEN_NR", "KEN_WR", "KEN_MKR", "KEN_CR"],
    "DRC": ["DRC_E", "DRC_S", "DRC_W"],
    "Tanzania": ["TAN_LR", "TAN_NR", "TAN_ER", "TAN_SR", "TAN_SWR", "TAN_WR", "TAN_CR"],
}

# === 1. Load CSV ===
df = pd.read_csv(CSV_PATH)
df["time"] = pd.to_datetime(df["Unnamed: 0"], dayfirst=False)
df = df.drop(columns=["Unnamed: 0"])


def get_demand(country: str):
    """
    Return demand series for a given country (aggregated if needed).
    """
    if country in AGGREGATIONS:
        cols = AGGREGATIONS[country]
    elif country in df.columns:
        cols = [country]
    else:
        raise ValueError(f"Country {country} not recognized.")
    return df[cols].sum(axis=1)


def plot_demand(countries, day: str):
    """
    Plot demand curve for one or more countries in a given day and save it as PNG.
    """
    if isinstance(countries, str):
        countries = [countries]

    fig, ax = plt.subplots(figsize=(10, 5))

    for country in countries:
        demand_series = get_demand(country)
        mask = df["time"].dt.strftime("%Y-%m-%d") == day
        demand_day = demand_series[mask]
        hours = df.loc[mask, "time"].dt.hour

        # Disegno sempre in azzurro con linea più spessa
        ax.plot(hours, -demand_day/1e6, color="#87CEEB", linewidth=3.5)

    # === STILE ===
    ax.set_title(f"Egypt's Electricity Demand on {day}", 
                 fontfamily="serif", fontsize=16, pad=18)  # titolo più grande
    ax.set_xlabel("Hour of the day", fontfamily="serif", fontsize=11)
    ax.set_ylabel("Demand [GW]", fontfamily="serif", fontsize=11)

    ax.tick_params(axis="both", labelsize=10)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontfamily("serif")

    # Limite Y fisso
    ax.set_ylim(50, 85)

    # Spines: solo sinistro e basso
    ax.spines["right"].set_visible(False)
    ax.spines["top"].set_visible(False)
    ax.spines["left"].set_visible(True)
    ax.spines["bottom"].set_visible(True)

    # ❌ niente quadratini di sfondo
    ax.grid(False)

    ax.set_xticks(range(0, 24))

    # === niente legenda / quadratini ===

    plt.tight_layout()

    # Salvataggio immagine
    os.makedirs(OUT_DIR, exist_ok=True)
    outfile = os.path.join(OUT_DIR, f"demand_{day}.png")
    plt.savefig(outfile, dpi=300)
    plt.close()
    print(f"✅ Grafico salvato in: {outfile}")


# === EXAMPLES ===
# Single country
plot_demand("Egypt", "2040-07-03")
