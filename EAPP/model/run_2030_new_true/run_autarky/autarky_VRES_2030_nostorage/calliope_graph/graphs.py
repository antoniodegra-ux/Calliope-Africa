# -*- coding: utf-8 -*-
"""
Created on Tue Aug 18 13:53:42 2020

@author: Amin
"""
def style_check(style):
    
    styles = ['default','classic','Solarize_Light2','_classic_test','bmh',
              'dark_background','fast','fivethirtyeight','ggplot','grayscale',
              'seaborn','seaborn-bright','seaborn-colorblind','seaborn-dark',
              'seaborn-dark-palette','seaborn-darkgrid','seaborn-deep',
              'seaborn-muted','seaborn-notebook','seaborn-paper',
              'seaborn-pastel','seaborn-poster','seaborn-talk','seaborn-ticks',
              'seaborn-white','seaborn-whitegrid','tableau-colorblind10']
    
    if style not in styles:
        
        raise ValueError ('{} is not correct. Acceptable styles are : \n {} \n For more information: https://matplotlib.org/3.1.1/gallery/style_sheets/style_sheets_reference.html'.format(style,styles))
        
    return style
    

def date2name(date,name):
    
    l_date=[]
    l_name=[]
    l_date.append(date[0])
    l_name.append(name[0])    
    
    for i in range(1,len(date)):
        if name[i] != name[i-1]:

            l_date.append(date[i])
            l_name.append(name[i])
    
    return l_date,l_name


def node_disp (nodes,fig_format,unit,conversion,style,date_format,title_font,production,imports,exports,figsize,demand,colors,names,rotate,average,sp_techs,sp_nodes,directory,x_ticks):
    
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib import gridspec
    
    from calliope_graph.graphs import style_check  
    from calliope_graph.matrixmaker import prod_imp_exp
    
    style = style_check(style)
    plt.style.use(style)
    
    if average == 'weekly':
        av = '1w'
    elif average == 'daily':
        av = '1d'
    elif average == 'monthly':
        av = '1m'
    elif average == 'hourly':
        av = '1h'
    elif average == 'yearly':
        av = '1y'
        

            
    else:
        raise ValueError ('Incorrect average type.\n Average can be one of the followings: {},{},{},{} and {}'.format('hourly','daily','weekly','monthly','yearly'))
    
    for i in nodes:
        
        data = prod_imp_exp(production,imports,exports,i)
        
        

        dem       = demand[i].resample(av).mean()
        data0     = data[0].resample(av).mean()
        data1     = data[1].resample(av).mean()
        
        
        
        if sp_techs!= None and i in sp_nodes:
            

                
            fig, (axs) = plt.subplots(2, figsize=figsize,sharex=True)
            gs = gridspec.GridSpec(2, 1,height_ratios=[3,1]) 
            
            axs[1] = plt.subplot(gs[1])
            axs[0] = plt.subplot(gs[0],sharex=axs[1])
            
            plt.setp(axs[0].get_xticklabels(), visible=False)
               
            
            axs[0].margins(x=0)
            axs[0].margins(y=0.1)

            axs[1].margins(x=0)
            axs[1].margins(y=0.1)
            
            axs[0].plot(dem.index,dem.values*conversion,'black',alpha=0.5, linestyle = '-', label ='Demand',linewidth=1)
                
            # Drawing positivie numbers
            axs[0].stackplot(data0.index,data0.values.T*conversion,colors=colors[data0.columns],labels=names[data0.columns])
                
            # Drawing negative numbers
            axs[0].stackplot(data1.index,data1.values.T*conversion,colors=colors[data1.columns],labels=names[data1.columns])                
                
            axs[0].legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.,frameon=True)
                
            axs[1].stackplot(data0.index,data0[sp_techs].values.T*conversion,colors=colors[sp_techs])
            
            # xticks properties
            xfmt = mdates.DateFormatter(date_format)
            axs[1].xaxis.set_major_formatter(xfmt)
            axs[1].tick_params(axis='x', rotation=rotate)

            if x_ticks=='name':
                ticks = date2name(list(data0.index),list(data0.index.month_name()))
                plt.xticks(ticks =ticks[0] ,labels = ticks[1], rotation = rotate)
                axs[1].set_xticks(axs[1].get_xticks()[0:12])



        else:
            
            fig,(ax) = plt.subplots(1,figsize=figsize)
            ax.margins(x=0)
            ax.margins(y=0.1)
            
            # Drawing demand line
            plt.plot(dem.index,dem.values*conversion,'black',alpha=0.5, linestyle = '-', label ='Demand',linewidth=1)
            
            # Drawing positivie numbers
            plt.stackplot(data0.index,data0.values.T*conversion,colors=colors[data0.columns],labels=names[data0.columns])
            
            # Drawing negative numbers
            plt.stackplot(data1.index,data1.values.T*conversion,colors=colors[data1.columns],labels=names[data1.columns])
            
            # Legend properties
            plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.,frameon=True)
            
            
            # xticks properties
            xfmt = mdates.DateFormatter(date_format)
            ax.xaxis.set_major_formatter(xfmt)
            plt.xticks(rotation=rotate)
        
            # labels
            plt.xlabel('Date')
            plt.ylabel(unit)
            
            if x_ticks=='name':
                ticks = date2name(list(data0.index),list(data0.index.month_name()))
                plt.xticks(ticks =ticks[0] ,labels = ticks[1], rotation = rotate)
                ax.set_xticks(ax.get_xticks()[0:12])
          
            
        # Title
        plt.title('{} Dispatch'.format(names[i]),fontsize=title_font)
        
        
        # saving 

        fig.savefig('{}\{}_{}_dispatch.{}'.format(directory,i,average,fig_format), dpi=fig.dpi,bbox_inches='tight')
        plt.show()




def sys_disp (rational,fig_format,unit,conversion,style,date_format,title_font,production,imports,exports,figsize,demand,colors,names,rotate,average,sp_techs,sp_nodes,directory,x_ticks):
    
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib import gridspec
    
    from calliope_graph.graphs import style_check  
    from calliope_graph.matrixmaker import system_matrix
    
    style = style_check(style)
    plt.style.use(style)
    
    if average == 'weekly':
        av = '1w'
    elif average == 'daily':
        av = '1d'
    elif average == 'monthly':
        av = '1m'
    elif average == 'hourly':
        av = '1h'
    elif average == 'yearly':
        av = '1y'
            
    else:
        raise ValueError ('Incorrect average type.\n Average can be one of the followings: {},{},{},{} and {}'.format('hourly','daily','weekly','monthly','yearly')) 
        
    data = system_matrix(production, demand)
    
    demand  = data[0]
    
    if rational == 'techs':
        production = data[1]
        if sp_nodes:
            raise ValueError ('For /techs/ rational, specific nodes cannot be plotted.')
        
    elif rational == 'nodes':
        production = data[2]
        if sp_techs:
            raise ValueError('For /nodes/ rational, specific techs cannot be plotted.')

    else:
        raise ValueError ('rational could be one of the followings: \n 1. techs : plotting the graph based on the technologies. \n 2. nodes: Plotting the graph based on the nodes')
    
    specific = None
    if sp_techs:
        specific = sp_techs
    elif sp_nodes:
        specific = sp_nodes
        

    demand       = demand.resample(av).mean()
    production   = production.resample(av).mean()
 
        
    if specific:
            
        fig, (axs) = plt.subplots(2, figsize=figsize,sharex=True)
        gs = gridspec.GridSpec(2, 1,height_ratios=[3,1]) 
        
        axs[1] = plt.subplot(gs[1])
        axs[0] = plt.subplot(gs[0],sharex=axs[1])
        
        plt.setp(axs[0].get_xticklabels(), visible=False)
           
        
        axs[0].margins(x=0)
        axs[0].margins(y=0.1)

        axs[1].margins(x=0)
        axs[1].margins(y=0.1)
        
        axs[0].plot(demand.index,demand.values*conversion,'black',alpha=0.5, linestyle = '-', label ='Demand',linewidth=0.5)
            
        # Drawing positivie numbers
        axs[0].stackplot(production.index,production.values.T*conversion,colors=colors[production.columns],labels=names[production.columns])
            
        # Drawing negative numbers
        #axs[0].stackplot(data1.index,data1.values.T*conversion,colors=colors[data1.columns],labels=names[data1.columns])                
            
        axs[0].legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.,frameon=True)
            
        axs[1].stackplot(production.index,production[specific].values.T*conversion,colors=colors[specific])
        
        # xticks properties
        xfmt = mdates.DateFormatter(date_format)
        axs[1].xaxis.set_major_formatter(xfmt)
        axs[1].tick_params(axis='x', rotation=rotate)  
        axs[1].set_ylabel(unit)

        if x_ticks=='name':
            ticks = date2name(list(production.index),list(production.index.month_name()))
            plt.xticks(ticks =ticks[0] ,labels = ticks[1], rotation = rotate) 
            axs[1].set_xticks(axs[1].get_xticks()[0:12])
    else:
        
                
        fig,(ax) = plt.subplots(1,figsize=figsize)
        ax.margins(x=0)
        ax.margins(y=0.1)
        
        # Drawing demand line
        plt.plot(demand.index,demand.values*conversion,'black',alpha=0.5, linestyle = '-', label ='Demand',linewidth=3)
        
        # Drawing positivie numbers
        plt.stackplot(production.index,production.values.T*conversion,colors=colors[production.columns],labels=names[production.columns])
        
        # Drawing negative numbers
        #plt.stackplot(data1.index,data1.values.T*conversion,colors=colors[data1.columns],labels=names[data1.columns])
        
        # Legend properties
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.,frameon=True)
        
        
        # xticks properties
        xfmt = mdates.DateFormatter(date_format)
        ax.xaxis.set_major_formatter(xfmt)
        plt.xticks(rotation=rotate)
    
        # labels
        plt.xlabel('Date')

        if x_ticks=='name':
            ticks = date2name(list(production.index),list(production.index.month_name()))
            plt.xticks(ticks =ticks[0] ,labels = ticks[1], rotation = rotate)
            ax.set_xticks(ax.get_xticks()[0:12])
            
    plt.ylabel(unit)
    plt.title('System Dispatch',fontsize=title_font)
    
    fig.savefig('{}\system{}_dispatch.{}'.format(directory,average,fig_format), dpi=fig.dpi,bbox_inches='tight')
    plt.show()        
        
        



def nod_pie(nodes,rational,fig_format,unit,conversion,kind,style,title_font,production,imports,exports,figsize,colors,names,directory,table_font,v_round):
       
    import matplotlib.pyplot as plt

    
    from calliope_graph.graphs import style_check 
    
    from calliope_graph.matrixmaker import pie_prod  
    from calliope_graph.matrixmaker import pie_cons        
        
    style = style_check(style)
    plt.style.use(style)
    
    for i in nodes:
        
        if rational == 'production':
            data = pie_prod(production[i],kind)
        elif rational == 'consumption':
            data = pie_cons(production[i],imports[i],exports[i],kind)
            #print(data)
        else:
            raise ValueError ('rational could be one of the follwoings: \n 1. /production/ \n 2. /consumption/')
            
        if kind == 'absolute':
            data = data*conversion
            
        fig, (ax1, ax2) = plt.subplots( nrows=1, ncols=2, figsize=figsize,gridspec_kw={'width_ratios': [3, 1]})

        
        ax1.pie(data['Production'],shadow=False,colors=colors[data.index],startangle=90)
        
        ax2.patch.set_visible(False)
        ax2.get_xaxis().set_visible(False)
        ax2.get_yaxis().set_visible(False)
    
        l, b, w, h = ax1.get_position().bounds
        ll, bb, ww, hh = ax2.get_position().bounds
        ax2.set_position([ll*0.85, b , w, h])
        ax2.axis('off') 
    
        if kind == 'share':
            tab_label = '%'
            
        else:
            tab_label = unit
        
        data=data.round(v_round)
        
        table = ax2.table(cellText=data.values,
                              rowColours=colors[data.index],
                              rowLabels= names[data.index],
                              colLabels = [tab_label],
                              loc='center',
                              rowLoc ='center',
                              colLoc='center',
                              cellLoc='center')   
    
        table.auto_set_font_size(False)
        
        table.scale(0.4, 3)
        table.set_fontsize(table_font)
        
        fig.suptitle('{} '.format(names[i]), fontsize=title_font)
        
        plt.show()
        fig.savefig('{}\{}_{}_pie.{}'.format(directory,i,kind,fig_format), dpi=fig.dpi,bbox_inches='tight')
        

def sys_pie(rational,fig_format,unit,conversion,kind,style,title_font,production,imports,exports,figsize,colors,names,directory,table_font,v_round,demand):
       
    import matplotlib.pyplot as plt

    
    from calliope_graph.graphs import style_check 
    
    from calliope_graph.matrixmaker import pie_prod  
    from calliope_graph.matrixmaker import pie_cons 
    from calliope_graph.matrixmaker import system_matrix       
        
    style = style_check(style)
    plt.style.use(style)       

    production = system_matrix(production, demand)
    production = production[1]
    
    data = pie_prod(production,kind)

        
    if kind == 'absolute':
        data = data*conversion
        
    fig, (ax1, ax2) = plt.subplots( nrows=1, ncols=2, figsize=figsize,gridspec_kw={'width_ratios': [3, 1]})

    
    ax1.pie(data['Production'],shadow=False,colors=colors[data.index],startangle=90)

    ax2.patch.set_visible(False)
    ax2.get_xaxis().set_visible(False)
    ax2.get_yaxis().set_visible(False)

    l, b, w, h = ax1.get_position().bounds
    ll, bb, ww, hh = ax2.get_position().bounds
    ax2.set_position([ll*0.85, b , w, h])
    ax2.axis('off') 

    if kind == 'share':
        tab_label = '%'
        
    else:
        tab_label = unit
    
    data=data.round(v_round)
    
    table = ax2.table(cellText=data.values,
                          rowColours=colors[data.index],
                          rowLabels= names[data.index],
                          colLabels = [tab_label],
                          loc='center',
                          rowLoc ='center',
                          colLoc='center',
                          cellLoc='center')    

    table.auto_set_font_size(False)
    
    table.scale(0.4, 3)
    table.set_fontsize(table_font)
    
    fig.suptitle('System', fontsize=title_font,horizontalalignment='left')
    
    plt.show()
    fig.savefig('{}\system_{}_pie.{}'.format(directory,kind,fig_format), dpi=fig.dpi,bbox_inches='tight')       
        

def tab_install (figsize,install_cap,colors,names,nodes,table_font,title_font,directory,conversion,style,v_round,fig_format,kind,unit):
    
    import matplotlib.pyplot as plt
    
    from calliope_graph.graphs import style_check 
    

    style = style_check(style)
    plt.style.use(style)   

    install_cap = install_cap * conversion
    install_cap = install_cap.round(v_round)
    
    
    
    if kind == 'table':
        
        fig,(ax) = plt.subplots(1,figsize=figsize)
        table = plt.table(cellText=install_cap.values,
                                  rowColours=colors[install_cap.index],
                                  rowLabels= names[install_cap.index],
                                  colLabels = nodes,
                                  loc='upper center',
                                  rowLoc ='center',
                                  colLoc='center',
                                  cellLoc='center')    
        
        
        table.set_fontsize(table_font)
        table.scale(1, 2)
        plt.box(on=None)
        ax = plt.gca()
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)
        
    elif kind == 'bar':
        
        install_cap.columns = install_cap.columns.to_list()
        install_cap.T.plot(kind='bar',stacked=True,color=colors[install_cap.index],figsize=figsize)
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.,frameon=True,labels=names[install_cap.index])
        
        plt.xlabel('Nodes')
        plt.ylabel(unit)
        

    else:
        raise ValueError('/kind/ should be one of the followings: \n 1. /table/ \n 2. /bar/')
        



    plt.title('Installed Capacity',fontsize=title_font)
        
    
    
    plt.savefig('{}\{}_installed_cap.{}'.format(directory,kind,fig_format),bbox_inches='tight',dpi=150)
            
    
    
def cap_f_bar(nodes,fig_format,style,title_font,figsize,directory,cap_f_inp,colors,names,kind,table_font,v_round):
    
    import matplotlib.pyplot as plt
    from calliope_graph.graphs import style_check 
    
    cap_f = cap_f_inp.copy()
    style = style_check(style)
    plt.style.use(style) 
    
    colors = colors[cap_f.index]
    cap_f.index = names[cap_f.index]
    cap_f = cap_f.round(v_round)
    
    if kind == 'bar':
    
        for i in nodes:
            
            cap_f[i].plot(kind='bar',stacked=True,color=colors,figsize=figsize,legend=False)
          
            
            
            plt.title('{} capacity factor'.format(names[i]),fontsize=title_font)
            plt.savefig('{}\{}capacity_factor.{}'.format(directory,i,fig_format),bbox_inches='tight',dpi=150)
            plt.show()
        
    elif kind == 'table':
        
        fig,(ax) = plt.subplots(1,figsize=figsize)
        table = plt.table(cellText=cap_f.values,
                                  rowColours= colors,
                                  rowLabels= cap_f.index,
                                  colLabels = nodes,
                                  loc='upper center',
                                  rowLoc ='center',
                                  colLoc='center',
                                  cellLoc='center')    
        
        
        table.set_fontsize(table_font)
        table.scale(1, 2)
        plt.box(on=None)
        ax = plt.gca()
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)  
        
        plt.title('Capacity Factor',fontsize=title_font)
        
        plt.savefig('{}\system_capacity_factor.{}'.format(directory,fig_format),bbox_inches='tight',dpi=150)
        
    
    else:
        raise ValueError('/kind/ should be one of the followings: \n 1. /table/ \n 2. /bar/')    
    
    
    
    
    
    
    
    
    
    
    
    
    
        
        
        
        
        
        
        
        