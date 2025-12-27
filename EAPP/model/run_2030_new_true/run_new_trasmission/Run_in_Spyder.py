#%%
# -*- coding: utf-8 -*-
"""
Run multipli scenari Calliope 2030 - PLANNING EAPP con monitoraggio RAM
"""

import calliope
import os
import shutil
import gc
#import psutil

# Imposta la verbosità
try:
    calliope.set_log_level('error')
except:
    calliope.set_log_verbosity('error')

# === CONFIGURAZIONE ===

# Mappa: nome cartella scenario → nome file Location_Constraints
scenarios = {
    "new_trasmission_VRES_2030_BESS": "Location_Constraints_autarky_VRES_2030_BESS.yaml",
    "new_trasmission_VRES_2030_PHES": "Location_Constraints_autarky_VRES_2030_PHES.yaml",
    "new_trasmission_VRES_2030_nostorage": "Location_Constraints_autarky_VRES_2030_nostorage.yaml",
    "new_trasmission_CG+VRES_2030_BESS": "Location_Constraints_autarky_CG+VRES_2030_BESS.yaml",
    "new_trasmission_CG+VRES_2030_nostorage": "Location_Constraints_autarky_CG+VRES_2030_nostorage.yaml",
    "new_trasmission_GT+VRES_2030_PHES": "Location_Constraints_autarky_GT+VRES_2030_PHES.yaml"
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

    # Copia i file
    try:
        shutil.copy(MODEL_FILE, model_dst)
        shutil.copy(location_src, location_dst)
    except Exception as copy_err:
        print(f"❌ Errore nella copia dei file per {scenario}: {copy_err}")
        continue

    try:
        # 📊 RAM prima del modello
       #ram_before = psutil.Process().memory_info().rss / 1e6
        #print(f"💾 RAM prima del run: {ram_before:.2f} MB")

        # Run modello
        model = calliope.Model(model_dst)
        model.run()

        # Esporta risultati
        model.to_csv(results_path, dropna=True)
        print(f"✅ Scenario completato: {scenario}")

        # 📊 RAM dopo il run
        #ram_after = psutil.Process().memory_info().rss / 1e6
        #print(f"💾 RAM dopo il run: {ram_after:.2f} MB")

    except Exception as e:
        print(f"❌ Errore nel run di {scenario}: {e}")

    finally:
        try:
            if hasattr(model, 'backend_model') and model.backend_model is not None:
                model.backend_model.dispose()
        except:
            print(f"⚠️ backend_model non disponibile per {scenario}")

        if 'model' in locals():
            del model
        gc.collect()

        # 📊 RAM dopo cleanup
        #ram_cleanup = psutil.Process().memory_info().rss / 1e6
        #print(f"🧹 RAM dopo cleanup: {ram_cleanup:.2f} MB")

#%%
print("🏁 Tutti gli scenari sono stati processati.")
