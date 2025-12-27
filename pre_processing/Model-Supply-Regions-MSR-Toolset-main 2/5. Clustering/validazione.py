# ===============================
# CLUSTERING VALIDATION SCRIPT
# ===============================

import pandas as pd
from tslearn.clustering import TimeSeriesKMeans
import numpy as np
import re
import os
from sklearn.metrics import pairwise_distances
from scipy.stats import entropy

# ============
# USER INPUTS
# ============

ctrl_path = "/Users/antoniodegrazia/Desktop/Model-Supply-Regions-MSR-Toolset-main 2/5. Clustering/ctrl.csv"
ctrl = pd.read_csv(ctrl_path).set_index('ctrl')
f_in = ctrl.loc['f_in']['val']
it = int(ctrl.loc['iterations']['val'])     # number of iterations in the clustering
ctrl_country_in = ctrl.loc['ctrl_country_in']['val'] # input path for countries file
tech = ctrl.loc['tech']['val']  # tech the run is about
metric = ctrl.loc['cluster_metric']['val']  # default is euclidean
ctrl_param_in = ctrl.loc['ctrl_param_in']['val']  # parameters' mode of aggregation

country_selected = "DRC_S"         # <--- MODIFICA QUI IL TUO COUNTRY
K_range = range(1, 51)             # numero cluster da testare
K_target = 10                      # target preferito di cluster

# ============
# PESI DEGLI INDICI
# ============

# Somma totale non deve superare 1.0
weights = {
    "Iavg_wc": 0.3,
    "Ip_sep": 0.3,
    "Ientropy": 0.2,
    "Iparsimony": 0.2,
    # "Iwidestgap": 0.0    # se vuoi usarlo puoi metterlo
}

# ============
# FUNZIONI
# ============

def compute_validation_indices(X, labels, centroids, n_clusters, K_target=10):
    """
    Calcola gli indici di validazione
    """
    # Intra-cluster distances
    intra_dists = []
    for c in range(n_clusters):
        cluster_points = X[labels == c]
        if cluster_points.shape[0] > 1:
            delta = cluster_points - centroids[c].reshape(1, -1)
            dist = np.linalg.norm(delta, axis=1)
            intra_dists.extend(dist)
        elif cluster_points.shape[0] == 1:
            intra_dists.append(0.0)

    Iavg_wc = np.mean(intra_dists) if len(intra_dists) > 0 else 0.0

    # Inter-cluster distances
    inter_dists = []
    for i in range(n_clusters):
        for j in range(i+1, n_clusters):
            dist = np.linalg.norm(centroids[i] - centroids[j])
            inter_dists.append(dist)
    Ip_sep = np.mean(inter_dists) if len(inter_dists) > 0 else 0.0

    # Entropy of cluster sizes
    cluster_sizes = np.array([(labels == c).sum() for c in range(n_clusters)])
    probs = cluster_sizes / cluster_sizes.sum()
    H = entropy(probs) / np.log(n_clusters) if n_clusters > 1 else 1.0
    Ientropy = H

    # Parsimony → solo 1.0 se K è uguale a K_target, 0.0 altrimenti
    Iparsimony = 1.0 if n_clusters == K_target else 0.0

    # Widest gap (approximated by max intra-cluster std dev)
    cluster_stds = []
    for c in range(n_clusters):
        cluster_points = X[labels == c]
        if cluster_points.shape[0] > 0:
            cluster_stds.append(np.std(cluster_points))
    Iwidestgap = 1.0 / (1.0 + max(cluster_stds)) if len(cluster_stds) > 0 else 1.0

    return {
        "Iavg_wc": Iavg_wc,
        "Ip_sep": Ip_sep,
        "Ientropy": Ientropy,
        "Iparsimony": Iparsimony,
        "Iwidestgap": Iwidestgap
    }

def compute_Iagg(indices, weights):
    """
    Calcola l'indice composito aggregato
    """
    indices_norm = indices.copy()

    # Normalizzazioni: invertiamo quelli dove valore basso è meglio
    indices_norm["Iavg_wc"] = 1.0 / (1.0 + indices["Iavg_wc"]) if indices["Iavg_wc"] > 0 else 1.0
    indices_norm["Ip_sep"] = indices["Ip_sep"] / (indices["Ip_sep"] + 1.0) if indices["Ip_sep"] > 0 else 0.0
    # gli altri sono già [0,1] (entropy, parsimony, widestgap)

    Iagg = sum(indices_norm[k] * weights.get(k,0) for k in indices_norm)
    return Iagg, indices_norm

# ============
# CARICAMENTO DATI
# ============

raw = pd.read_excel(f_in)
raw = raw.set_index('Zone_ID')

# Filtra solo il country selezionato
raw_ctry = raw[raw['CtryName'] == country_selected]

if raw_ctry.empty:
    print(f"ATTENZIONE: Nessun dato trovato per il country {country_selected}")
    exit()

# Prepara i dati orari
raw_trans = raw_ctry.T
raw_trans_ind = raw_trans.index.tolist()
raw_trans['H'] = [int(re.findall('\d+', i)[0]) if re.findall('H\d+', i) else 'nan' for i in raw_trans_ind]
raw_trunc = raw_trans[raw_trans['H'] != 'nan'].set_index('H')
raw_trunc_inv = raw_trans[raw_trans['H'] == 'nan']

X_full = raw_trunc.T.values  # array zone x time

results = []

# ============
# CICLO SU K
# ============

for nclust in K_range:
    try:
        # Clustering
        model = TimeSeriesKMeans(
            n_clusters=nclust,
            metric=metric,
            max_iter=it,
            verbose=0
        ).fit(X_full)

        labels = model.labels_
        centroids = model.cluster_centers_.squeeze(-1)   # FIX SHAPE qui!

        # Calcola indici
        indices = compute_validation_indices(X_full, labels, centroids, nclust, K_target=K_target)
        Iagg, indices_norm = compute_Iagg(indices, weights)

        res_row = {
            "K": nclust,
            "Iagg": Iagg,
            **indices,
            **{f"{k}_norm": v for k, v in indices_norm.items()}
        }
        results.append(res_row)

        print(f"K={nclust} → Iagg={Iagg:.4f}")

    except Exception as e:
        print(f"Errore a K={nclust}: {e}")

# ============
# SALVA RISULTATI
# ============

results_df = pd.DataFrame(results)
output_path = f"/Users/antoniodegrazia/Desktop/Model-Supply-Regions-MSR-Toolset-main 2/5. Clustering/results/validation_indices_{country_selected}.csv"
results_df.to_csv(output_path, index=False)

print(f"✅ File salvato: {output_path}")
