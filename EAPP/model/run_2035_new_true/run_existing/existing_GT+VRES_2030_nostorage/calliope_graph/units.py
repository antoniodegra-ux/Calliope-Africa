# -*- coding: utf-8 -*-
"""
Created on Tue Aug 18 13:22:27 2020

@author: Amin
"""



def unit_check(unit):
    
    units = ['W','kW','MW','GW','TW']
    
    if unit not in units:
        raise ValueError ('{} is not correct. Unit should be one of the followings: \n {}'.format(unit,units))
        
    return unit
        
def unit_check2(unit):
    
    units = ['Wh','kWh','MWh','GWh','TWh']
    
    if unit not in units:
        raise ValueError ('{} is not correct. Unit should be one of the followings: \n {}'.format(unit,units))
        
    return unit

def u_conv (unit1,unit2):
    
    converter = {'W':1,'kW':10**3,'MW':10**6,'GW':10**9,'TW':10**12}
    
    
    return converter[unit1]/converter[unit2]   
            
def u_conv2 (unit1,unit2):
    
    converter = {'Wh':1,'kWh':10**3,'MWh':10**6,'GWh':10**9,'TWh':10**12}

    return converter[unit1]/converter[unit2]  

def p2e(p):
    converter = {'W':'Wh','kW':'kWh','MW':'MWh','GW':'GWh','TW':'TWh'}
    
    return converter[p]
            
            
            
            
            