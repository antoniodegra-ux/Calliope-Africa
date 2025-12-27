#%%
# -*- coding: utf-8 -*-
"""
Run multipli scenari Calliope 2030 - PLANNING EAPP
"""

import calliope
import os
import shutil
import gc

# Imposta la verbosità
try:
    calliope.set_log_level('error')
except:
    calliope.set_log_verbosity('error')

# === CONFIGURAZIONE ===

# Mappa: nome cartella scenario → nome file Location_Constraints
scenarios = {
    "autarky_VRES_2030_BESS": "Location_Constraints_autarky_VRES_2030_BESS.yaml",
    "autarky_VRES_2030_PHES": "Location_Constraints_autarky_VRES_2030_PHES.yaml",
    "autarky_VRES_2030_nostorage": "Location_Constraints_autarky_VRES_2030_nostorage.yaml",
    "autarky_CG+VRES_2030_BESS": "Location_Constraints_autarky_CG+VRES_2030_BESS.yaml",
    "autarky_CG+VRES_2030_nostorage": "Location_Constraints_autarky_CG+VRES_2030_nostorage.yaml",
    "autarky_GT+VRES_2030_PHES": "Location_Constraints_autarky_GT+VRES_2030_PHES.yaml"
}

# Cartelle principali
BASE_DIR = "."  # Dove lanci lo script
MODEL_FILE = os.path.join(BASE_DIR, "model.yaml")
LOCATIONS_DIR = os.path.join(BASE_DIR, "LocationSets2030")

# === RUN ===

for scenario, loc_file in scenarios.items():
    print(f"\n🚀 Lancio scenario: {scenario}")

    scenario_path = os.path.join(BASE_DIR, scenario)
    model_dst = os.path.join(scenario_path, "model.yaml")
    location_dst = os.path.join(scenario_path, "Model_config", "Location_Constraints.yaml")
    location_src = os.path.join(LOCATIONS_DIR, loc_file)
    results_path = os.path.join(scenario_path, "results")

    # Copia il file model.yaml e Location_Constraints.yaml nello scenario
    shutil.copy(MODEL_FILE, model_dst)
    shutil.copy(location_src, location_dst)

    try:
        # Costruzione e run del modello
        model = calliope.Model(model_dst)
        model.run()

        # Esporta i risultati
        model.to_csv(results_path, dropna=True)
        model.backend_model.dispose()
        print(f"✅ Scenario completato: {scenario}")
    except Exception as e:
        print(f"❌ Errore nel run di {scenario}: {e}")
    finally:
        del model
        gc.collect()

#%%
print("🏁 Tutti gli scenari sono stati processati.")

