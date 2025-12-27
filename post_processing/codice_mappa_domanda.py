# -*- coding: utf-8 -*-
"""
Map (choropleth) dei GWh totali per Paese con:
- Classi per quantili + bin extra P95–max (per far risaltare l'Egitto)
- Colorbar con soglie arrotondate alle centinaia
- Nessuna etichetta dentro i Paesi
- Tabella dei totali in PNG separato

Dipendenze: pandas, geopandas, matplotlib  (opz.: cartopy)
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm
from pathlib import Path

# ========= PATH =========
DEMAND_CSV = Path("/Users/antoniodegrazia/Desktop/run_2030_new_true/run_autarky/common_inputs/Timeseries/Demand.csv")
MAP_PNG    = Path("/Users/antoniodegrazia/Desktop/planning/choropleth_demand_total_GWh_quantiles.png")
TABLE_PNG  = Path("/Users/antoniodegrazia/Desktop/planning/choropleth_demand_totals_table.png")

# ========= CARTOGRAFIA =========
def load_world_with_cartopy():
    from cartopy.io import shapereader as shp
    shp_path = shp.natural_earth(resolution="110m", category="cultural", name="admin_0_countries")
    reader = shp.Reader(shp_path)
    recs = list(reader.records())
    geoms = [r.geometry for r in recs]
    attrs = [r.attributes for r in recs]
    gdf = gpd.GeoDataFrame(attrs, geometry=geoms, crs="EPSG:4326")
    for c in ["NAME_EN", "NAME", "name"]:
        if c in gdf.columns:
            gdf = gdf.rename(columns={c: "NAME_STD"})
            break
    if "NAME_STD" not in gdf.columns:
        raise RuntimeError("Colonna nome paese non trovata.")
    return gdf

def load_world_with_zip_http():
    url = "zip+https://naturalearth.s3.amazonaws.com/110m_cultural/ne_110m_admin_0_countries.zip"
    gdf = gpd.read_file(url)
    for c in ["NAME_EN", "NAME", "name"]:
        if c in gdf.columns:
            gdf = gdf.rename(columns={c: "NAME_STD"})
            break
    if "NAME_STD" not in gdf.columns:
        raise RuntimeError("Colonna nome paese non trovata.")
    return gdf

try:
    world_gdf = load_world_with_cartopy()
except Exception:
    world_gdf = load_world_with_zip_http()

for c in ["CONTINENT", "continent"]:
    if c in world_gdf.columns:
        world_gdf = world_gdf.rename(columns={c: "CONTINENT_STD"})
        break

africa = world_gdf[world_gdf.get("CONTINENT_STD", "").astype(str).str.lower().eq("africa")]
if africa.empty:
    africa = world_gdf.copy()

FOCUS = {
    "Egypt", "Libya", "Sudan", "South Sudan", "Ethiopia", "Eritrea", "Djibouti",
    "Uganda", "Rwanda", "Burundi", "Kenya", "Tanzania",
    "Democratic Republic of the Congo",
}
africa["in_focus"] = africa["NAME_STD"].isin(FOCUS)
focus_gdf = africa[africa["in_focus"]].copy()
other_gdf = africa[~africa["in_focus"]].copy()

# ========= DOMANDA: TOTALE GWh =========
df = pd.read_csv(DEMAND_CSV)

drop_cols = [c for c in df.columns if "Unnamed" in c or "time" in c.lower() or "date" in c.lower()]
df = df.drop(columns=drop_cols, errors="ignore")
df_num = df.select_dtypes(include=[np.number]).copy()

n_rows = len(df_num)
if n_rows in (8760, 8784):
    HOURS_PER_STEP = 1.0
elif n_rows == 365:
    HOURS_PER_STEP = 24.0
else:
    HOURS_PER_STEP = 1.0
    print(f"Attenzione: righe={n_rows}, assumo HOURS_PER_STEP={HOURS_PER_STEP}.")

country_cols = {
    "Egypt":    [c for c in df_num.columns if c.startswith("Egypt_")],
    "Kenya":    [c for c in df_num.columns if c.startswith("KEN_")],
    "Tanzania": [c for c in df_num.columns if c.startswith("TAN_")],
    "DR Congo": [c for c in df_num.columns if c.startswith("DRC_")],
}
if "LYBIA" in df_num.columns or "Lybia" in df_num.columns:
    country_cols["Libya"] = [c for c in ["LYBIA", "Lybia"] if c in df_num.columns]
if "South_Sudan" in df_num.columns:
    country_cols["South Sudan"] = ["South_Sudan"]
for nm in ["Sudan", "Ethiopia", "Eritrea", "Djibouti", "Uganda", "Rwanda", "Burundi"]:
    if nm in df_num.columns and nm not in country_cols:
        country_cols[nm] = [nm]

tot_GWh = {}
for country, cols in country_cols.items():
    if not cols:
        continue
    kW_sum_over_time = df_num[cols].sum(axis=1).abs().sum()
    tot_GWh[country] = kW_sum_over_time * HOURS_PER_STEP / 1e6  # kW*h -> GWh

tot_df = pd.DataFrame({"Country": list(tot_GWh.keys()), "Total_GWh": list(tot_GWh.values())})
tot_df["NAME_JOIN"] = tot_df["Country"].replace({"DR Congo": "Democratic Republic of the Congo"})
focus_gdf = focus_gdf.merge(tot_df, left_on="NAME_STD", right_on="NAME_JOIN", how="left")

# ========= CLASSI: quantili + bin extra P95–max =========
vals = focus_gdf["Total_GWh"].dropna().values
if len(vals) < 3:
    edges = np.linspace(vals.min(), vals.max(), 6)
else:
    q0, q20, q40, q60, q80, q95, q100 = np.quantile(vals, [0, .2, .4, .6, .8, .95, 1.0])
    edges = np.array([q0, q20, q40, q60, q80, q95, q100])
edges = np.unique(edges)
if len(edges) < 6:
    edges = np.linspace(vals.min(), vals.max(), 6)

cmap = plt.get_cmap("YlOrRd")
norm = BoundaryNorm(boundaries=edges, ncolors=256, clip=True)

# ========= FIGURA MAPPA (SOLO MAPPA) =========
fig, ax = plt.subplots(figsize=(12, 9))
if not other_gdf.empty:
    other_gdf.plot(ax=ax, color="#e6e6e6", edgecolor="white", linewidth=0.4)

focus_gdf.plot(
    ax=ax,
    column="Total_GWh",
    cmap=cmap,
    norm=norm,
    linewidth=0.6,
    edgecolor="black",
    missing_kwds={"color": "#f0f0f0", "edgecolor": "white", "hatch": "///"},
)

# Colorbar con etichette arrotondate alle centinaia
sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
sm.set_array([])
cbar = plt.colorbar(sm, ax=ax, fraction=0.035, pad=0.02)
cbar.set_label("Total electricity demand [GWh]", fontsize=11)

# tick alle vere soglie, ma **etichette arrotondate alle centinaia**
edges_rounded = np.round(edges / 100.0) * 100.0
cbar.set_ticks(edges)
cbar.set_ticklabels([f"{int(x):,}".replace(",", " ") for x in edges_rounded])

ax.set_xlim(-20, 55)
ax.set_ylim(-15, 40)
ax.set_title("Total Electricity Demand by Country (GWh)", fontsize=18, pad=14)
ax.axis("off")

MAP_PNG.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(MAP_PNG, dpi=300, bbox_inches="tight")
plt.close(fig)

# ========= FIGURA TABELLA (PNG separato) =========
table_df = (
    tot_df.assign(Country_plot=tot_df["Country"].replace({"DR Congo": "Dem. Rep. Congo"}))
          .sort_values("Total_GWh", ascending=False)[["Country_plot", "Total_GWh"]]
)
fig2, ax2 = plt.subplots(figsize=(4.8, 8))  # stretto e alto
ax2.axis("off")
ax2.set_title("Totals [GWh]", fontsize=13, pad=10)

y0 = 0.98
line_h = 0.06
for i, (_, row) in enumerate(table_df.iterrows()):
    y = y0 - i * line_h
    if y < 0.04:
        break
    ax2.text(0.02, y, f"{row['Country_plot']}", fontsize=11, va="top")
    ax2.text(0.98, y, f"{int(round(row['Total_GWh'])):,}".replace(",", " "), fontsize=11, va="top", ha="right")

plt.tight_layout()
plt.savefig(TABLE_PNG, dpi=300, bbox_inches="tight")
plt.close(fig2)

print("✔ Mappa salvata:", MAP_PNG.resolve())
print("✔ Tabella salvata:", TABLE_PNG.resolve())
