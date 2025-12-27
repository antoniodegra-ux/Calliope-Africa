import os
os.environ["SHAPE_RESTORE_SHX"] = "YES"

import re
import pandas as pd
import geopandas as gpd

# =========================
# NORMALIZZAZIONE PAESI → ISO3
# =========================
_suffix_re = re.compile(r'_(N|S|E|W|NE|NW|SE|SW|\d+)$')  # rimuove SOLO suffissi finali tipo _N, _1...

def to_iso3(x: str) -> str:
    if pd.isna(x):
        return None
    s = str(x).strip().upper()

    # versione "clean" per i match testuali (SOUTH_SUDAN → SOUTH SUDAN)
    s_clean = s.replace("_", " ").replace("-", " ")

    if s.startswith("COD") or s.startswith("DRC") or "CONGO" in s_clean: return "COD"
    if s.startswith("SSD") or "SOUTH SUDAN" in s_clean: return "SSD"
    if s.startswith("SDN") or s.startswith("SUDAN"): return "SDN"
    if s.startswith("TZA") or s.startswith("TAN") or "TANZANIA" in s_clean: return "TZA"
    if s.startswith("KEN") or "KENYA" in s_clean: return "KEN"
    if s.startswith("ETH") or "ETHIOPIA" in s_clean: return "ETH"
    if s.startswith("ERI") or "ERITREA" in s_clean: return "ERI"
    if s.startswith("RWA") or "RWANDA" in s_clean: return "RWA"
    if s.startswith("BDI") or "BURUNDI" in s_clean: return "BDI"
    if s.startswith("UGA") or "UGANDA" in s_clean: return "UGA"
    if s.startswith("DJI") or "DJIBOUTI" in s_clean: return "DJI"
    if s.startswith("EGY") or "EGYPT" in s_clean: return "EGY"
    if s.startswith("LBY") or s.startswith("LYB") or "LIBYA" in s_clean or "LIBIA" in s_clean: return "LBY"
    if s in {"BDI","COD","DJI","ERI","ETH","KEN","RWA","SSD","SDN","TZA","UGA","EGY","LBY"}: return s

    # prova a rimuovere SOLO un suffisso di zona e ritenta
    s_base = _suffix_re.sub("", s)
    if s_base != s:
        return to_iso3(s_base)

    return s

def assign_color(value):
    if pd.isna(value): return '#D3D3D3'
    if value > 0.75:   return '#D62727'
    if value > 0.5:    return '#FF6F61'
    if value > 0:      return '#F5A3A3'
    if value < -1:     return '#3CB371'
    if value < -0.5:   return '#66CDAA'
    return '#A8E6A3'

# =========================
# SHAPEFILE: carica solo *_0.shp
# =========================
def ensure_country_column(gdf, filename):
    candidates = ['Country', 'COUNTRY', 'NAME', 'NAME_0', 'ADMIN', 'CNTRY_NAME']
    for c in candidates:
        if c in gdf.columns:
            gdf['ISO3'] = gdf[c].apply(to_iso3)
            return gdf[['ISO3', 'geometry']]
    print(f"⚠️ Nessuna colonna paese trovata in {filename}")
    return None

def carica_confini(cartella_base):
    gdf_list = []
    for root, _, files in os.walk(cartella_base):
        for file in files:
            if file.lower().endswith("_0.shp"):
                path_file = os.path.join(root, file)
                gdf = gpd.read_file(path_file)
                gdf = ensure_country_column(gdf, file)
                if gdf is not None:
                    gdf_list.append(gdf)
    gdf = pd.concat(gdf_list, ignore_index=True)
    return gdf.dissolve(by="ISO3", as_index=False)

# =========================
# QML (colori categorizzati + etichette GWh attive)
# =========================
def crea_qml(percorso_shp, colori, campo_colore="color", campo_etichetta="label_text"):
    cats, syms = [], []
    for i, col in enumerate(colori):
        cats.append(f'<category value="{col}" label="{col}" render="true" symbol="{i}"/>')
        syms.append(f"""<symbol name="{i}" type="fill">
  <layer pass="0" class="SimpleFill">
    <prop k="color" v="{col}"/>
    <prop k="outline_color" v="35,35,35,255"/>
    <prop k="outline_width" v="0.26"/>
  </layer>
</symbol>""")

    qml = f"""<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.28" styleCategories="Symbology|Labeling">
  <renderer-v2 type="categorizedSymbol" attr="{campo_colore}">
    <categories>
      {''.join(cats)}
    </categories>
    <symbols>
      {''.join(syms)}
    </symbols>
  </renderer-v2>
  <labeling type="simple">
    <settings>
      <text-style field="{campo_etichetta}" font="Arial" bold="1" size="10" color="0,0,0,255"/>
      <text-buffer bufferDraw="1" bufferSize="1.2" bufferColor="255,255,255,255" bufferOpacity="1"/>
      <placement placement="1" centroidInside="1"/>
    </settings>
  </labeling>
</qgis>
"""
    percorso_qml = percorso_shp.replace(".shp", ".qml")
    with open(percorso_qml, "w", encoding="utf-8") as f:
        f.write(qml)
    print(f"🎨 QML salvato: {percorso_qml}")

# =========================
# SOLO results_carrier_con.csv → net trade balance
# =========================
def compute_net_trade_balance_from_con(results_path):
    con_fp = os.path.join(results_path, 'results_carrier_con.csv')
    if not os.path.isfile(con_fp):
        raise FileNotFoundError(f"Manca {con_fp}")

    df = pd.read_csv(con_fp)

    # solo electricity (se presente)
    if 'carriers' in df.columns:
        df = df[df['carriers'].astype(str).str.lower() == 'electricity']

    # filtra linee di trasmissione
    techs = df['techs'].astype(str)
    mask_trans = techs.str.contains('transmission', case=False, na=False) | techs.str.contains(':', na=False)
    df = df[mask_trans].copy()

    # destinazione da 'techs'
    def parse_dest(t):
        t = str(t)
        return t.split(':')[-1] if ':' in t else None

    df['export_to'] = techs.apply(parse_dest)

    # aggrega annuale
    df['year'] = pd.to_datetime(df['timesteps']).dt.to_period('Y')
    df = df.groupby(['year','locs','export_to'], as_index=False).sum(numeric_only=True)

    energy_col = 'carrier_con' if 'carrier_con' in df.columns else 'value'
    if energy_col not in df.columns:
        raise KeyError("Non trovo la colonna dell'energia (attesa 'carrier_con' o 'value').")
    df.rename(columns={energy_col: 'production'}, inplace=True)

    # ISO3
    df['ISO3_from'] = df['locs'].apply(to_iso3)
    df['ISO3_to']   = df['export_to'].apply(to_iso3)

    # saldo: from += v ; to -= v
    net = {}
    for _, r in df.iterrows():
        a, b, v = r['ISO3_from'], r['ISO3_to'], r['production']
        if pd.isna(a) or pd.isna(b):
            continue
        net[a] = net.get(a, 0.0) + v
        net[b] = net.get(b, 0.0) - v

    return pd.DataFrame(list(net.items()), columns=['ISO3','Net Trade Balance'])

# =========================
# PARAMETRI (adatta i percorsi)
# =========================
cartella_scenari  = r"C:\Users\ilari\OneDrive\Desktop\tesi\2030_false\run_new_trasmission"
percorso_demand   = r"C:\Users\ilari\OneDrive\Desktop\tesi\Demand_2030.xlsx"
cartella_confini  = r"C:\Users\ilari\OneDrive\Desktop\tesi\shapefile"

# =========================
# CONFINI E DOMANDA
# =========================
gdf_confini = carica_confini(cartella_confini)

demand_df = pd.read_excel(percorso_demand)
demand_df['ISO3'] = demand_df['Country'].apply(to_iso3)
demand_df = demand_df.groupby('ISO3', as_index=False)['Demand'].sum()

# =========================
# LOOP SCENARI
# =========================
for scenario in os.listdir(cartella_scenari):
    results_dir = os.path.join(cartella_scenari, scenario, "results")
    if not os.path.isdir(results_dir):
        continue

    print(f"\n⚡ Elaboro scenario: {scenario}")

    # 1) Net trade balance (SOLO da results_carrier_con.csv)
    ntb = compute_net_trade_balance_from_con(results_dir)  # ISO3, Net Trade Balance (assunto in kWh)

    # 2) Merge con domanda + metriche + colori + labels
    df = pd.merge(ntb, demand_df, on='ISO3', how='outer').fillna(0)
    df = df.groupby('ISO3', as_index=False).agg({'Net Trade Balance':'sum','Demand':'sum'})

    def safe_ratio(row):
        return row['Net Trade Balance'] / row['Demand'] if row['Demand'] not in (0, None) and pd.notna(row['Demand']) else pd.NA
    df['Percentage'] = df.apply(safe_ratio, axis=1)
    df['color'] = df['Percentage'].apply(assign_color)

    # ============ Etichetta in GWh ============
    # Assumo Net Trade Balance in kWh → GWh = / 1e6.
    # Se i tuoi risultati sono in MWh, usa 1e3.
    df['NTB_GWh'] = df['Net Trade Balance'] / 1e6
    # formato con segno e 1 decimale (es. +123.4 GWh)
    df['label_text'] = df['NTB_GWh'].map(lambda x: f"{x:+.1f} GWh")

    # 3) Salva CSV (Export_files.csv)
    output_csv = os.path.join(cartella_scenari, scenario, "Export_files.csv")
    df.to_csv(output_csv, index=False)

    # 4) Shapefile
    gdf_finale = gdf_confini.merge(df, on='ISO3', how='left')
    gdf_finale = gdf_finale.dissolve(by="ISO3", aggfunc="first").reset_index()

    output_shp = os.path.join(cartella_scenari, scenario, "Export_map.shp")
    gdf_finale.to_file(output_shp)
    print(f"🗺️ Shapefile salvato: {output_shp}")

    # 5) QML (etichette GWh attive)
    colori_usati = df['color'].dropna().unique().tolist()
    crea_qml(output_shp, colori_usati, campo_colore="color", campo_etichetta="label_text")
    print(f"✅ Creati: {output_csv}, {output_shp} + QML")

print("\n🎉 Tutti gli scenari elaborati.")
