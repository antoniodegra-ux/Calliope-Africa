import pandas as pd
import numpy as np
from sklearn.metrics import silhouette_score, silhouette_samples

# =========================
# USER INPUT: PERCORSI FILE
# =========================

# File EXCEL originale dei profili orari (quello usato nel clustering)
f_in = "/Users/antoniodegrazia/Desktop/Model-Supply-Regions-MSR-Toolset-main 2/SolarPV_BestMSRsToCover5%CountryArea.xlsx"

# File CSV di assegnazione cluster
zones_cluster_file = "/Users/antoniodegrazia/Desktop/Model-Supply-Regions-MSR-Toolset-main 2/5. Clustering/results/zones_cluster_assignment.csv"

# Output silhouette medio
out_path = "/Users/antoniodegrazia/Desktop/Model-Supply-Regions-MSR-Toolset-main 2/5. Clustering/results/silhouette_original_profiles.csv"

# Output silhouette dettagliato (tutti i punti)
out_path_details = "/Users/antoniodegrazia/Desktop/Model-Supply-Regions-MSR-Toolset-main 2/5. Clustering/results/silhouette_details_all_countries.csv"

# =========================
# LETTURA DATI
# =========================

print("Leggo il file Excel originale...")

# Legge il file excel
raw = pd.read_excel(f_in)

# imposta Zone_ID come indice
raw = raw.set_index("Zone_ID")

print("Leggo il file di assegnazione cluster...")

# Legge assegnazione cluster
zones_cluster = pd.read_csv(zones_cluster_file)

# Togli eventuali spazi nei nomi colonne
zones_cluster.columns = zones_cluster.columns.str.strip()

# =========================
# CALCOLO SILHOUETTE
# =========================

results = []
all_silhouette = []

countries = zones_cluster["CtryName"].dropna().unique()

for country in countries:
    print(f"\nElaboro il paese: {country}")
    
    # Filtra solo zone di quel paese
    zones_in_country = zones_cluster[zones_cluster["CtryName"] == country]
    
    # Prendi gli ID
    zone_ids = zones_in_country["Zone_ID"].values
    
    # Filtra righe dal raw originale
    raw_country = raw.loc[zone_ids]
    
    # Filtra solo colonne orarie (H1...H8760)
    time_cols = [col for col in raw_country.columns if str(col).startswith("H")]
    
    if len(time_cols) == 0:
        print(f" - Nessuna colonna oraria trovata per {country}. Skip.")
        continue
    
    # Crea matrice profili
    X = raw_country[time_cols].values
    
    # Prendi etichette cluster
    cluster_labels = zones_in_country.set_index("Zone_ID").loc[raw_country.index, "cluster"].values
    
    # se c'è solo un cluster → silhouette non calcolabile
    if len(np.unique(cluster_labels)) < 2:
        print(f" - Solo un cluster presente per {country}. Silhouette non calcolabile.")
        sil_score = np.nan
        
        # crea comunque silhouette dettagliato con valori nulli
        silhouette_values = np.full(X.shape[0], np.nan)
    else:
        try:
            # silhouette medio
            sil_score = silhouette_score(X, cluster_labels, metric='euclidean')
            print(f" - Silhouette score medio: {sil_score:.4f}")
            
            # silhouette per ogni MSR
            silhouette_values = silhouette_samples(X, cluster_labels, metric='euclidean')
            
        except Exception as e:
            print(f" - Errore calcolo silhouette: {e}")
            sil_score = np.nan
            silhouette_values = np.full(X.shape[0], np.nan)
    
    # salva silhouette medio nel summary
    results.append({
        "Country": country,
        "Num_clusters": len(np.unique(cluster_labels)),
        "Silhouette_score": sil_score
    })
    
    # crea DataFrame dettagliato
    silhouette_df = pd.DataFrame({
        "Zone_ID": raw_country.index,
        "Country": country,
        "Cluster": cluster_labels,
        "Silhouette_s(i)": silhouette_values
    })
    
    all_silhouette.append(silhouette_df)

# =========================
# SALVATAGGIO FILE RISULTATI
# =========================

# salva summary silhouette medio
pd.DataFrame(results).to_csv(out_path, index=False)

# salva tutti i dettagli dei punti
final_silhouette = pd.concat(all_silhouette, ignore_index=True)
final_silhouette.to_csv(out_path_details, index=False)

print("\n✅ Calcolo terminato.")
print(f"Risultati silhouette medi salvati in:\n{out_path}")
print(f"Dettaglio silhouette di tutti i punti salvato in:\n{out_path_details}")
