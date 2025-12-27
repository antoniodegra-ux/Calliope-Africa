import os
import pandas as pd
import re
from ruamel.yaml import YAML
import copy

# === CONFIGURAZIONE ===
base_folder = '/Users/antoniodegrazia/Desktop/run_2035_new_true/run_autarky'
yaml_filename_pattern = 'Location_Constraints'
yaml_subfolder = 'Model_config'

yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=4, sequence=4, offset=2)

for scenario_name in os.listdir(base_folder):
    scenario_path = os.path.join(base_folder, scenario_name)
    if not os.path.isdir(scenario_path):
        continue

    model_config_path = os.path.join(scenario_path, yaml_subfolder)
    if not os.path.isdir(model_config_path):
        print(f"Sottocartella 'Model_config' mancante per {scenario_name}")
        continue

    yaml_files = [f for f in os.listdir(model_config_path) if yaml_filename_pattern in f and f.endswith('.yaml')]
    if not yaml_files:
        print(f"Nessun file YAML trovato nella Model_config per {scenario_name}")
        continue
    input_yaml_path = os.path.join(model_config_path, yaml_files[0])

    csv_path = os.path.join(scenario_path, 'results', 'results_energy_cap.csv')
    if not os.path.exists(csv_path):
        print(f"CSV mancante per {scenario_name}")
        continue

    df = pd.read_csv(csv_path)
    df = df[df['energy_cap'] != 0]

    df_ocgt = df[df['techs'].str.contains('OCGT_NG_new', na=False)]
    df_bess = df[df['techs'].str.contains('BESS', na=False)]
    df_phes = df[df['techs'].str.contains('PHES', na=False)]
    df_msr = df[df['techs'].str.contains('MSR', na=False)]

    if df_ocgt.empty and df_bess.empty and df_phes.empty and df_msr.empty:
        print(f"Nessuna tecnologia rilevante in {scenario_name}")
        continue

    with open(input_yaml_path, 'r') as f:
        data = yaml.load(f)

    data_new = copy.deepcopy(data)

    # === OCGT ===
    for _, row in df_ocgt.iterrows():
        loc = row['locs']
        tech = row['techs']
        cap = float(row['energy_cap'])
        new_tech = f"{tech}_2040_installed"
        if loc in data_new.get('locations', {}):
            techs_dict = data_new['locations'][loc].setdefault('techs', {})
            if new_tech not in techs_dict:
                techs_dict[new_tech] = {'constraints': {'energy_cap_equals': cap}}

    # === BESS ===
    for loc in df_bess['locs'].unique():
        cap_sum = float(df_bess[df_bess['locs'] == loc]['energy_cap'].sum())
        if loc in data_new.get('locations', {}):
            techs_dict = data_new['locations'][loc].setdefault('techs', {})
            techs_dict['BESS_2040_installed'] = {
                'constraints': {
                    'energy_cap_equals': cap_sum,
                    'energy_cap_per_storage_cap_equals': 0.25
                }
            }

    # === PHES ===
    for loc in df_phes['locs'].unique():
        cap_sum = float(df_phes[df_phes['locs'] == loc]['energy_cap'].sum())
        if loc in data_new.get('locations', {}):
            techs_dict = data_new['locations'][loc].setdefault('techs', {})
            techs_dict['PHES_2040_installed'] = {
                'constraints': {
                    'energy_cap_equals': cap_sum,
                    'energy_cap_per_storage_cap_equals': 0.16666666667
                }
            }
            if 'PHES' in techs_dict and 'constraints' in techs_dict['PHES']:
                if 'energy_cap_max' in techs_dict['PHES']['constraints']:
                    original = techs_dict['PHES']['constraints']['energy_cap_max']
                    techs_dict['PHES']['constraints']['energy_cap_max'] = max(0, float(original) - cap_sum)

    # === MSR ===
    for _, row in df_msr.iterrows():
        loc = row['locs']
        tech = row['techs']
        cap = float(row['energy_cap'])
        new_tech = f"{tech}_2040_installed"

        # Tipo tecnologia
        res_type = "Solar" if "PV" in tech else "Wind"
        resource_file = f"{res_type}_EAPP_MSR.csv"

        # Rimuovi prefisso "PV_" o "Wind_" e suffisso "_MSR" per ottenere il nome della risorsa
        if res_type == "Solar":
            resource_name = tech.replace("PV_", "")
        else:
            resource_name = tech.replace("Wind_", "")
        resource_name = resource_name.replace("_MSR", "").replace("__", "_")

        if loc in data_new.get('locations', {}):
            techs_dict = data_new['locations'][loc].setdefault('techs', {})
            techs_dict[new_tech] = {
                'constraints': {
                    'energy_cap_equals': cap,
                    'resource': f'file={resource_file}:{resource_name}',
                    'resource_unit': 'energy_per_cap'
                }
            }
            if tech in techs_dict and 'constraints' in techs_dict[tech]:
                if 'energy_cap_max' in techs_dict[tech]['constraints']:
                    original = techs_dict[tech]['constraints']['energy_cap_max']
                    techs_dict[tech]['constraints']['energy_cap_max'] = max(0, float(original) - cap)

    # === Scrivi YAML ===
    output_path = os.path.join(model_config_path, f'loc2040_{scenario_name}.yaml')
    with open(output_path, 'w') as f:
        yaml.dump(data_new, f)

    print(f"✔️  Creato: {output_path}")

print("✅ Completato per tutti gli scenari.")
