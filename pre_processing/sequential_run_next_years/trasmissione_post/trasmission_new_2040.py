# -*- coding: utf-8 -*-
import os
import copy
import pandas as pd
from ruamel.yaml import YAML

# ====== CONFIG ======
BASE = '/Users/antoniodegrazia/Desktop/run_2035_new_true/run_new_trasmission_2035_true'
SCENARIO_PREFIX = 'new_trasmission_'   # nome cartelle scenario
INPUT_REL = os.path.join('Model_config', 'Transmission_links.yaml')
RESULTS_DIR = 'results'
CAP_CSV = 'results_energy_cap.csv'
DIST_CSV = 'inputs_distance.csv'

# ====== YAML setup ======
yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=4, sequence=4, offset=2)

def list_scenarios(base):
    return [
        d for d in os.listdir(base)
        if d.startswith(SCENARIO_PREFIX) and os.path.isdir(os.path.join(base, d))
    ]

def read_yaml(path):
    with open(path, 'r') as f:
        data = yaml.load(f) or {}
    if 'links' not in data or data['links'] is None:
        data['links'] = {}
    return data

def write_yaml(path, data):
    with open(path, 'w') as f:
        yaml.dump(data, f)

def backup(path):
    i = 1
    bak = path + '.bak'
    while os.path.exists(bak):
        i += 1
        bak = path + f'.bak{i}'
    with open(path, 'r') as src, open(bak, 'w') as dst:
        dst.write(src.read())
    return bak

def parse_loc2(tech_str):
    # 'new_transmission:LOC2' -> 'LOC2'
    return tech_str.split(':', 1)[1].strip() if (isinstance(tech_str, str) and ':' in tech_str) else None

# ====== MAIN ======
scenarios = list_scenarios(BASE)
print(f"Trovati {len(scenarios)} scenari:")
for s in scenarios: print(" -", s)

for scenario in scenarios:
    scen_path = os.path.join(BASE, scenario)
    yaml_path = os.path.join(scen_path, INPUT_REL)
    cap_path  = os.path.join(scen_path, RESULTS_DIR, CAP_CSV)
    dist_path = os.path.join(scen_path, RESULTS_DIR, DIST_CSV)

    print(f"\n🔄 Scenario: {scenario}")

    if not os.path.exists(yaml_path):
        print("  ⚠️  Transmission_links.yaml non trovato:", yaml_path)
        continue
    if not os.path.exists(cap_path):
        print("  ⚠️  results_energy_cap.csv mancante. Salto…")
        continue
    if not os.path.exists(dist_path):
        print("  ⚠️  inputs_distance.csv mancante. Salto…")
        continue

    cap_df = pd.read_csv(cap_path)
    dist_df = pd.read_csv(dist_path)

    # Tieni ESATTAMENTE le righe new_transmission con cap > 0 (no somme)
    cap_rows = cap_df[
        cap_df['techs'].astype(str).str.startswith('new_transmission', na=False)
        & (cap_df['energy_cap'] > 0)
    ].copy()

    if cap_rows.empty:
        print("  ℹ️  Nessuna new_transmission > 0. Salto…")
        continue

    # Costruisci chiave non orientata e preferisci l'orientamento canonico (loc1 <= loc2)
    cap_rows['loc1'] = cap_rows['locs'].astype(str)
    cap_rows['tech'] = cap_rows['techs'].astype(str)
    cap_rows['loc2'] = cap_rows['tech'].apply(parse_loc2)
    cap_rows = cap_rows.dropna(subset=['loc2']).copy()

    # chiave non orientata "A,B" con A<=B
    canon = cap_rows.apply(
        lambda r: ",".join(sorted([r['loc1'], r['loc2']])),
        axis=1
    )
    cap_rows['link_key'] = canon
    cap_rows['is_canonical_orientation'] = cap_rows.apply(lambda r: r['loc1'] <= r['loc2'], axis=1)

    # Ordina in modo che il verso canonico venga prima, poi deduplica per link_key (KEEP=FIRST)
    cap_rows = cap_rows.sort_values(by=['link_key', 'is_canonical_orientation'], ascending=[True, False])
    cap_rows = cap_rows.drop_duplicates(subset=['link_key'], keep='first')

    # Carica YAML dello scenario
    data = read_yaml(yaml_path)
    updated = copy.deepcopy(data)

    # SOVRASCRIVI sempre transmission_2040_installed con il valore della riga selezionata
    for _, r in cap_rows.iterrows():
        link_key = r['link_key']
        loc1 = r['loc1']
        tech = r['tech']
        energy_cap = float(r['energy_cap'])

        # Distanza coerente con la STESSA riga; se mancante, prova l'orientamento opposto
        drow = dist_df[(dist_df['locs'] == loc1) & (dist_df['techs'] == tech)]
        if drow.empty:
            # fallback: prova l'altro verso
            other_loc = r['loc2']
            other_tech = f"new_transmission:{loc1}"
            drow = dist_df[(dist_df['locs'] == other_loc) & (dist_df['techs'] == other_tech)]
        distance = float(drow['distance'].values[0]) if not drow.empty else None

        link = updated['links'].setdefault(link_key, {})
        techs_map = link.setdefault('techs', {})

        entry = {'constraints': {'energy_cap_equals': energy_cap}}
        if distance is not None:
            entry['distance'] = distance

        # OVERWRITE: scrivi sempre (non sommare, non mantenere valori precedenti)
        techs_map['transmission_2040_installed'] = entry

        print(f"  ↻ {link_key}: 2040_installed = {energy_cap} (dist={distance})  [da riga: {loc1}, {tech}]")

    # Backup + scrittura IN PLACE
    bak = backup(yaml_path)
    print(f"  💾 Backup creato: {bak}")
    write_yaml(yaml_path, updated)
    print(f"  ✅ Aggiornato (solo 2040_installed, 2035 intatti): {yaml_path}")

print("\n✅ Completato.")
