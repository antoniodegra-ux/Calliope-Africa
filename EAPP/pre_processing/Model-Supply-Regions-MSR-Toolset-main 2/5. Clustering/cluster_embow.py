#Li Yunshu, Oct 2021, for IRENA
import pandas as pd
from tslearn.clustering import TimeSeriesKMeans
import matplotlib.pyplot as plt
import numpy as np
import re
import os

# USER INPUTS

ctrl_path = "/Users/antoniodegrazia/Desktop/Model-Supply-Regions-MSR-Toolset-main 2/5. Clustering/ctrl.csv"
ctrl = pd.read_csv(ctrl_path).set_index('ctrl')
f_in = ctrl.loc['f_in']['val']
it = int(ctrl.loc['iterations']['val'])     #number of iterations in the clustering
ctrl_country_in = ctrl.loc['ctrl_country_in']['val']
tech = ctrl.loc['tech']['val']
metric = ctrl.loc['cluster_metric']['val']
ctrl_param_in = ctrl.loc['ctrl_param_in']['val']
ctryf_writeout = ctrl.loc['ctryf_writeout']['val']
use_elbow = ctrl.loc['use_elbow']['val'].lower() == "yes"

raw = pd.read_excel(f_in).set_index('Zone_ID')
ctrl_ctry = pd.read_csv(ctrl_country_in).set_index('country').to_dict()
nclust_all = ctrl_ctry['n_cluster']
ctrl_param = pd.read_csv(ctrl_param_in)
sum_param = ctrl_param[ctrl_param['mode'] == 'sum']['param']
mean_param = ctrl_param[ctrl_param['mode'] == 'mean']['param']
wmean_param = ctrl_param[ctrl_param['mode'] == 'wmean']['param']
max_param = ctrl_param[ctrl_param['mode'] == 'max']['param']
wmean_IEC_param = ctrl_param[ctrl_param['mode'] == 'wmean_IEC']['param']

debug = pd.DataFrame()
out_dir = tech
os.makedirs(out_dir, exist_ok=True)

def elbow_method(raw_trunc, max_k=60):
    inertias = []
    for k in range(1, max_k + 1):
        model = TimeSeriesKMeans(n_clusters=k, metric=metric, max_iter=it, verbose=0)
        model.fit(raw_trunc.T)
        inertias.append(model.inertia_)
    return inertias

for ctry in nclust_all:
    raw_ctry = raw[raw['CtryName'] == ctry]
    if not raw_ctry.empty:
        raw_trans = raw_ctry.T
        raw_trans_ind = raw_trans.index.tolist()
        raw_trans['H'] = [int(re.findall('\d+', i)[0]) if re.findall('H\d+', i) else 'nan' for i in raw_trans_ind]
        raw_trunc = raw_trans[raw_trans['H'] != 'nan'].set_index('H')
        raw_trunc_inv = raw_trans[raw_trans['H'] == 'nan']

        if use_elbow:
            print(f"Eseguo Elbow method per {ctry}...")
            inertias = elbow_method(raw_trunc)
            k_range = range(1, len(inertias)+1)
            
            # Plot e salvataggio
            plt.figure(figsize=(10,6))
            plt.plot(k_range, inertias, marker='o')
            plt.title(f'Elbow Method for {ctry}')
            plt.xlabel('Number of clusters')
            plt.ylabel('Inertia')
            plt.grid(True)
            plt.savefig(out_dir + f"/{ctry}_elbow.png")
            plt.close()

            # Usa un numero fisso temporaneo solo per generare i grafici (modifica a piacere)
            nclust = 5

            print(f"📊 Grafico salvato in {out_dir}/{ctry}_elbow.png. Scegli il numero di cluster dal grafico e aggiorna ctrl_country.csv.")
        else:
            nclust = nclust_all[ctry]

        model = TimeSeriesKMeans(n_clusters=nclust, metric=metric, max_iter=it, verbose=1).fit(raw_trunc.T)
        labels = model.labels_
        saveas = f'{ctry} {tech} zones {nclust}clust_{it}it'

        all_table_ = raw_trunc_inv.T.copy()
        all_table_ = all_table_[all_table_.index != 'H']
        all_table_['cluster'] = labels
        try:
            all_table_all = pd.concat([all_table_all, all_table_])
        except:
            all_table_all = all_table_

        all_table = all_table_.groupby(['cluster'])
        clust_table = pd.DataFrame(index=range(nclust))
        clust_table['Zones count'] = all_table['Area sq.Km'].count()

        for p in sum_param:
            clust_table[p] = all_table[p].sum()
        for p in mean_param:
            clust_table[p] = all_table[p].mean()
        for p in max_param:
            clust_table[p] = all_table[p].max()

        all_table_['weights'] = len(all_table_)
        for c in range(nclust):
            all_table_.loc[all_table_['cluster']==c,'weights'] = all_table_[all_table_['cluster']==c]['Max Capacity MW']/clust_table.loc[c]['Max Capacity MW']

        for p in wmean_param:
            p_ = p + '_'
            all_table_[p + '_'] = all_table_[p] * all_table_['weights']
            clust_table[p] = (all_table_.groupby(['cluster']))[p+'_'].sum()

        try:
            for p in wmean_IEC_param:
                p_ = p + '_'
                all_table_[p + '_'] = all_table_[p].str.replace(r'\D', '').astype(int) * all_table_['weights']
                clust_table[p] = 'Class-' + round((all_table_.groupby(['cluster']))[p+'_'].sum()).astype(int).astype(str)
        except:
            print('WARNING: no parameter using wmean_IEC')

        all_table_profiles = raw_trunc.copy().T.astype(float)
        all_table_profiles = all_table_profiles.multiply(all_table_['weights'], axis=0)
        all_table_profiles['cluster'] = labels
        all_table_profiles = all_table_profiles.groupby(['cluster']).sum()

        plot_count = nclust
        frac = [0, 1/4, 2/4, 3/4]
        plot_hours = [int(8760* i) for i in frac]
        fig, axs = plt.subplots(4, plot_count, figsize=(40, 25))
        if plot_count == 1:
            axs = np.expand_dims(axs, axis=1)

        fig.suptitle('Clusters')
        for label in set(labels):
            column_j = label
            cluster = []
            for i in range(len(labels)):
                if labels[i] == label:
                    for row_i in range(4):
                        axs[row_i, column_j].plot(raw_trunc.iloc[plot_hours[row_i]:plot_hours[row_i]+72,i], c="gray", alpha=0.4)
                        cluster.append(raw_trunc.iloc[:,i])
            if cluster:
                for row_i in range(4):
                    axs[row_i, column_j].plot(range(1+plot_hours[row_i],1+plot_hours[row_i]+72), all_table_profiles.loc[label][plot_hours[row_i]:plot_hours[row_i]+72], c="red")

        fig.savefig(out_dir + '/' + saveas)
        smallT = pd.concat([clust_table, all_table_profiles], axis=1)
        smallT['CtryName'] = ctry
        try:
            bigT = pd.concat([bigT, smallT], axis=0)
        except:
            bigT = smallT

bigT = bigT.rename_axis('Zone_ID')
bigT.index = bigT.index + 1
cols = bigT.columns.tolist()
cols = cols[-1:] + cols[:-1]
bigT = bigT[cols]
bigT.to_csv('bigT.csv')
all_table_all.to_csv('unclustered_zones_all.csv')
