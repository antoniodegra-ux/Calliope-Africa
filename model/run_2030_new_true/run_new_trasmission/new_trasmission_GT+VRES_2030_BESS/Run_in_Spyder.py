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

