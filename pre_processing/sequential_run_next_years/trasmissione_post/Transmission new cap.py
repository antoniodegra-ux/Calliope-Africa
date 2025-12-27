import pandas as pd
from ruamel.yaml import YAML
import os
import copy

# === YAML setup ===
yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=4, sequence=4, offset=2)

# === Percorsi ===
base_path = '/Users/antoniodegrazia/Desktop/run_2030_new_true/run_new_trasmission_true'
input_yaml_path = os.path.join(base_path, "common_inputs/Model_config/Transmission_links.yaml")

scenario_names = [
    "new_trasmission_VRES_2030_BESS",
    "new_trasmission_VRES_2030_PHES",
    "new_trasmission_VRES_2030_nostorage",
    "new_trasmission_GT+VRES_2030_BESS",
    "new_trasmission_GT+VRES_2030_nostorage",
    "new_trasmission_GT+VRES_2030_PHES"
]

# === Carica YAML base ===
with open(input_yaml_path, 'r') as f:
    base_yaml_data = yaml.load(f)

# === Loop per scenario ===
for scenario in scenario_names:
    print(f"🔄 Scenario: {scenario}")
    scenario_path = os.path.join(base_path, scenario, "results")
    cap_path = os.path.join(scenario_path, "results_energy_cap.csv")
    dist_path = os.path.join(scenario_path, "inputs_distance.csv")

    if not os.path.exists(cap_path) or not os.path.exists(dist_path):
        print(f"⚠️  File mancante per {scenario}")
        continue

    cap_df = pd.read_csv(cap_path)
    dist_df = pd.read_csv(dist_path)

    # Filtra solo new_transmission con capacità > 0
    cap_df_filtered = cap_df[
        cap_df['techs'].str.startswith("new_transmission", na=False) &
        (cap_df['energy_cap'] > 0)
    ]

    updated_yaml = copy.deepcopy(base_yaml_data)
    added_links = set()

    for _, row in cap_df_filtered.iterrows():
        loc1 = row['locs']
        tech = row['techs']
        loc2 = tech.split(":")[1]

        # Normalizza ordine locs
        loc_a, loc_b = sorted([loc1, loc2])
        link_key = f"{loc_a},{loc_b}"
        energy_cap = float(row['energy_cap'])

        if link_key in added_links:
            continue

        if link_key not in updated_yaml['links']:
            updated_yaml['links'][link_key] = {'techs': {}}

        if 'transmission_2035_installed' in updated_yaml['links'][link_key]['techs']:
            continue

        # Prendi la distanza da inputs_distance.csv
        distance_row = dist_df[(dist_df['locs'] == loc1) & (dist_df['techs'] == tech)]
        distance = float(distance_row['distance'].values[0]) if not distance_row.empty else None

        tech_entry = {
            'constraints': {
                'energy_cap_equals': energy_cap
            }
        }

        if distance is not None:
            tech_entry['distance'] = distance

        updated_yaml['links'][link_key]['techs']['transmission_2035_installed'] = tech_entry

        added_links.add(link_key)

    output_yaml_path = os.path.join(scenario_path, "Updated_Transmission.yaml")
    with open(output_yaml_path, 'w') as f:
        yaml.dump(updated_yaml, f)

    print(f"✅ Salvato: {output_yaml_path}")

print("✅ Tutti gli scenari processati.")
