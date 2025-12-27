#%%
#-*- coding: utf-8 -*-
"""
Created on Wed Feb 14 17:05:48 2024

@author: baioc
"""

import calliope
import cal_graph as gg

try:
    calliope.set_log_level('Error')
except:
    calliope.set_log_verbosity('Error')
    
model = calliope.Model('model.yaml')

model.run()

model.to_csv(r'results')


#%%
print('ciao')


#%%
#%% PLOTS


my_graphs = gg.C_Graph(model=model,ex_path=r'Graph_inputs.xlsx',unit='kW')

my_graphs.node_pie(rational = 'consumption',directory='my_graphs')

my_graphs.system_pie(kind='share',directory='my_graphs',v_round=2)

my_graphs.node_dispatch(directory='my_graphs',average='monthly')

my_graphs.sys_dispatch(directory='my_graphs',average='monthly')

my_graphs.ins_cap_plot(unit='kW',directory='my_graphs')


