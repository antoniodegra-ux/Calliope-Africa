# -*- coding: utf-8 -*-

"""
Created on Mon Aug 17 10:25:37 2020

@author: Amin
"""

class C_Graph:    
    
    def __init__(self,model,ex_path,unit):
        
        from calliope_graph.version import __version__
        
        from calliope_graph.matrixmaker import input_read
        from calliope_graph.matrixmaker import prod_matrix
        from calliope_graph.matrixmaker import imp_exp
        from calliope_graph.matrixmaker import dem_matrix
        from calliope_graph.matrixmaker import install_cap
        from calliope_graph.matrixmaker import cap_fac
        from calliope_graph.matrixmaker import levelized_cost

        from calliope_graph.units import unit_check  
        

        
        self.model = model
        self.m_unit = unit_check(unit)
        
        ex_inp = input_read(ex_path)
        
        self.co_techs    = ex_inp[0]
        self.carrier     = ex_inp[1]
        self.nodes       = ex_inp[2]
        self.pr_techs    = ex_inp[3]
        self.colors      = ex_inp[4]
        self.names       = ex_inp[5]
        self.tr_tech     = ex_inp[6]
        self.start       = ex_inp[7]
        self.end         = ex_inp[8]
        self.RES_ind     = ex_inp[9]
        
        self.production             = prod_matrix (model,self.pr_techs,self.nodes,self.carrier)
        self.imports,self.exports   = imp_exp(model,self.nodes,self.production,self.tr_tech,self.carrier)
        self.demand                 = dem_matrix (model,self.co_techs,self.carrier,self.nodes)
        self.install_capacity       = install_cap (model,self.nodes,self.pr_techs)
        self.cap_factor             = cap_fac(model,self.pr_techs,self.nodes,self.carrier,self.production)
        # self.TLC                    = levelized_cost(model)
                        

    def node_dispatch (self,x_ticks='date',nodes='All', fig_format = 'png' , unit= '' , style = 'default' , date_format = '%d/%m/%y , %H:%M', title_font = 15,figsize=(8,6),xtick_rotate=70,average='hourly',sp_techs=None ,sp_nodes= None,directory='my_graphs'):

                
        from calliope_graph.units import unit_check  
        from calliope_graph.units import u_conv 
        
        from calliope_graph.graphs import node_disp   
        
        if unit == '' :
            unit = self.m_unit
        else:
            unit == unit
        
        unit = unit_check(unit)
        conversion = u_conv(self.m_unit,unit)
        
        if nodes == 'All':
            nodes = self.nodes  
        else: 
            nodes = nodes
            
        node_disp (nodes,fig_format,unit,conversion,style,date_format,title_font,self.production,self.imports,self.exports,figsize,self.demand,self.colors,self.names,xtick_rotate,average,sp_techs,sp_nodes,directory,x_ticks)
            
        
    
        
    def sys_dispatch (self, x_ticks='date',rational = 'techs' , fig_format = 'png' , unit= '' , style = 'default' , date_format = '%d/%m/%y , %H:%M', title_font = 15,figsize=(8,6),xtick_rotate=70,average='hourly',sp_techs=None ,sp_nodes= None,directory='my_graphs'):            
        
        from calliope_graph.units import unit_check  
        from calliope_graph.units import u_conv     
        
        from calliope_graph.graphs import sys_disp
        
        
        if unit == '' :
            unit = self.m_unit
        else:
            unit == unit
        
        unit = unit_check(unit)
        conversion = u_conv(self.m_unit,unit)        
        
        sys_disp(rational,fig_format,unit,conversion,style,date_format,title_font,self.production,self.imports,self.exports,figsize,self.demand,self.colors,self.names,xtick_rotate,average,sp_techs,sp_nodes,directory,x_ticks)
        
        
    def node_pie (self,rational='production',nodes='All', fig_format = 'png' , unit= '' , style = 'ggplot' , title_font = 15 , kind = 'share' ,table_font=15,figsize=(16, 8),directory='my_graphs',v_round=3):
       
        from calliope_graph.units import unit_check2  
        from calliope_graph.units import u_conv2 
        from calliope_graph.units import p2e 
        
        from calliope_graph.graphs import nod_pie

        if unit == '' :
            unit = p2e(self.m_unit)
        else:
            unit == unit
        
        unit = unit_check2(unit)
        conversion = u_conv2(p2e(self.m_unit),unit)
        
        if nodes == 'All':
            nodes = self.nodes  
        else: 
            nodes = nodes  
            
        nod_pie(nodes,rational,fig_format,unit,conversion,kind,style,title_font,self.production,self.imports,self.exports,figsize,self.colors,self.names,directory,table_font,v_round)
        
        
        
    def ins_cap_plot (self,kind='table',fig_format = 'png' , unit= '', style = 'default',title_font = 15 ,table_font=15,figsize=(8,6),directory='my_graphs',v_round=0,cap_f = False):
        
        from calliope_graph.units import unit_check  
        from calliope_graph.units import u_conv 
        from calliope_graph.graphs import tab_install 
        
        if unit == '' :
            unit = self.m_unit
        else:
            unit == unit
        
        unit = unit_check(unit)
        conversion = u_conv(self.m_unit,unit)        
        
        tab_install (figsize,self.install_capacity,self.colors,self.names,self.nodes,table_font,title_font,directory,conversion,style,v_round,fig_format,kind,unit)
        
        
    def cap_f_plot (self,kind='table',nodes='All', fig_format = 'png' , style = 'default' , title_font = 15,figsize=(8,6),directory='my_graphs',table_font=15,v_round=4):
        

        from calliope_graph.graphs import cap_f_bar 
        if nodes == 'All':
            nodes = self.nodes  
        else: 
            nodes = nodes 
                
        cap_f_bar(nodes,fig_format,style,title_font,figsize,directory,self.cap_factor,self.colors,self.names,kind,table_font,v_round)
            


    def system_pie(self,rational='production', fig_format = 'png' , unit= '' , style = 'ggplot' , title_font = 15 , kind = 'share' ,table_font=15,figsize=(16, 8),directory='my_graphs',v_round=0):
        
        from calliope_graph.units import unit_check2  
        from calliope_graph.units import u_conv2 
        from calliope_graph.units import p2e 
        
        from calliope_graph.graphs import sys_pie

        if unit == '' :
            unit = p2e(self.m_unit)
        else:
            unit == unit
        
        unit = unit_check2(unit)
        conversion = u_conv2(p2e(self.m_unit),unit)
   
        sys_pie(rational,fig_format,unit,conversion,kind,style,title_font,self.production,self.imports,self.exports,figsize,self.colors,self.names,directory,table_font,v_round,self.demand)
        
        
        
        
        
        

        

