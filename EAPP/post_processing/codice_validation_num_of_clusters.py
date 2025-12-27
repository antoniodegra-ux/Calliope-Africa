import os
import pandas as pd
import numpy as np
from scipy.stats import entropy
from scipy.spatial.distance import pdist
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt

# === FUNZIONI PER GLI INDICI ===
def Iavg_wc(X, labels, centroids):
    return np.mean([
        np.linalg.norm(X[labels == i] - centroids[i], axis=1).mean()
        for i in np.unique(labels)
    ])

def Ip_sep(centroids):
    return np.mean(pdist(centroids))

def Icp2cent(X, labels, centroids):
    return np.mean([
        np.min(np.linalg.norm(X[labels == i] - centroids[i], axis=1))
        for i in np.unique(labels)
    ])

def Ientropy(labels):
    c = np.bincount(labels)
    p = c / np.sum(c)
    return entropy(p) / np.log(len(c))

def Iparsimony(n, min_target=5, max_target=15):
    if min_target <= n <= max_target:
        return 1.0
    dist = min(abs(n - min_target), abs(n - max_target))
    return max(0.0, 1 - dist / max_target)

# === PERCORSI DELLE CONFIGURAZIONI ===
configs = {
    "2_cluster":  r"C:\Users\ilari\OneDrive\Desktop\tesi\DRC_S_2cluster",
    "10_cluster": r"C:\Users\ilari\OneDrive\Desktop\tesi\DRC_S_10cluster\DRC_S_10cluster",
    "50_cluster": r"C:\Users\ilari\OneDrive\Desktop\tesi\DRC_S_50cluster\DRC_S_50cluster"
}


results = []

for label, path in configs.items():
    try:
        bigT = pd.read_csv(os.path.join(path, "bigT.csv"))
        unclustered = pd.read_csv(os.path.join(path, "unclustered_zones_all.csv"))
        assignment = pd.read_csv(os.path.join(path, "zones_cluster_assignment.csv"))

        merged = unclustered.merge(assignment, on=["CtryName", "Zone_ID"])
        X = merged[['Latitude', 'Longitude', 'Max Capacity MW']].values
        raw_labels = merged['cluster_y'].values

        unique_ids = bigT['cluster'].unique()
        id2idx = {zid: i for i, zid in enumerate(unique_ids)}
        labels = np.array([id2idx[z] for z in raw_labels])
        centroids = bigT.set_index('cluster').loc[unique_ids][['Latitude', 'Longitude', 'Max Capacity MW']].values

        results.append({
            "config": label,
            "Iavg_wc": Iavg_wc(X, labels, centroids),
            "Ip_sep": Ip_sep(centroids),
            "Icp2cent": Icp2cent(X, labels, centroids),
            "Ientropy": Ientropy(labels),
            "Iparsimony": Iparsimony(len(np.unique(labels)))
        })

    except Exception as e:
        print(f"❌ Errore nella configurazione {label}: {e}")

# === CONVERSIONE A DATAFRAME
df = pd.DataFrame(results)

# === STAMPA VALORI GREZZI
print("\n📉 VALORI GREZZI DEGLI INDICI:\n")
print(df.to_string(index=False))

# === INVERTI GLI INDICI DA MINIMIZZARE
df["Iavg_wc"] *= -1
df["Icp2cent"] *= -1

# === NORMALIZZAZIONE E CALCOLO Iagg
weights = {
    "Iparsimony": 0.35,
    "Icp2cent":  0.25,
    "Iavg_wc":   0.20,
    "Ip_sep":    0.10,
    "Ientropy":  0.10
}
to_normalize = ["Iavg_wc", "Ip_sep", "Icp2cent", "Ientropy"]
df_norm = df.copy()
df_norm[to_normalize] = MinMaxScaler().fit_transform(df[to_normalize])
df_norm["Iparsimony"] = df["Iparsimony"]
df_norm["Iagg"] = df_norm[list(weights)].mul(pd.Series(weights)).sum(axis=1)

# === STAMPA RISULTATI NORMALIZZATI
print("\n📊 RISULTATI NORMALIZZATI + Iagg:\n")
print(df_norm[["config", "Iagg"] + list(weights.keys())].to_string(index=False))

# === GRAFICO
plt.figure(figsize=(7, 4))
plt.bar(df_norm["config"], df_norm["Iagg"], color="mediumseagreen")
plt.title("Indice aggregato Iagg per configurazione")
plt.ylabel("Iagg")
plt.xlabel("Configurazione clustering")
plt.tight_layout()
plt.show()
