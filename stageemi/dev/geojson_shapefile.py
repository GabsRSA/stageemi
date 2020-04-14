"""
Develop by V. Chabot for WeatherForce
"""
import xarray as xr
import numpy as np
import os 

import geojson 
import json 
from stageemi.dev.geojson_from_mpl import contourf_geo

import matplotlib.pyplot as plt

import matplotlib.cm as cm
import matplotlib as mpl
from matplotlib.colors import rgb2hex, to_hex, to_rgba
import logging 
import pandas

from matplotlib.colors import ListedColormap, LinearSegmentedColormap


log = logging.getLogger('geojson_shapefile')
formatter = logging.Formatter('%(asctime)s - %(levelname)s -  %(name)s -%(message)s')
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(formatter)
log.addHandler(consoleHandler)
log.setLevel(logging.INFO)

def apply_style(features):
    for feature in features:
        style = {
            "fillColor": feature["properties"]["fill"],
            "fillOpacity":0.5,
            "opacity": 0.2,
            "color": "#000000",
            "dashArray": '5',
            "weight": 2,
        }
        feature["properties"]["style"] = style

def apply_style_wwmf(features):
    for feature in features:
        style = {
            "fillColor": feature["properties"]["fill"],
            "fillOpacity":0.9,#0.5,
            "opacity": 0.2,
            "color": "#000000",
            "dashArray": '5',
            "weight": 0.2,
        }
        feature["properties"]["style"] = style        
#----------------------------------------------------------    
#            From mat and option return a geojson file 
#
#----------------------------------------------------------
def return_geojson(mat,opt,colorbar_title="colorbar.png",**kwargs):   
    if "type" in opt: 
        type_leaf=opt["type"]
    else:
        type_leaf="Pixel"
    if "cmap" not in opt: 
        opt["cmap"]=cm.RdBu
        
    if type_leaf == "Pixel":
#         print("et ici")
        geof=return_geojson_pixel_wwmf(mat,opt,colorbar_title=colorbar_title,**kwargs)
    elif type_leaf == "Contour": 
        geof=return_geojson_contour(mat,opt,colorbar_title=colorbar_title,**kwargs)
        
    else: 
        print("Le type de plot avec leaflet est uniquement dans ['Contour','Pixel']")
        geof = None 
    return geof

def return_geojson_contour(mat,opt=dict(),colorbar_title='colorbar.png',**kwargs):

    fig = plt.figure(figsize=(6, 8))
    ax = fig.add_subplot(1, 1, 1)

    anob=mat.copy()
    if "cmap" not in opt: 
        opt["cmap"] = cm.RdBu
    
    if "bins" in opt: 
        contour = anob.plot.contourf(ax=ax,levels=opt["bins"], cmap=opt["cmap"],
                                     alpha=0.7,extend="both")
    else:
        contour = anob.plot.contourf(ax=ax,
                                     levels=10, cmap=opt["cmap"],
                                     alpha=0.7,extend="both")
    info = str(contourf_geo(contour,**kwargs))
    plt.close(fig)
    
    if opt.get("save_colorbar",False):
        if "orientation" in opt: 
            define_color_bar_contour(contour,colorbar_title,orientation=opt["orientation"],opt=opt)
        else: 
            define_color_bar_contour(contour,colorbar_title,opt=opt)
    else: 
        log.warning("Colorbar is not defined. Turn save_colorbar option to True to do so")
        
        
    if opt.get("save",False):
        with open("test_contour.json",'w') as fp: 
            fp.write(info)
    return info 
        
def fix_for_contour_colorbar(contour_in,ax1,extend,**kwargs):
    
    colors=list()
    for colec in contour_in.collections:
        colors.append(colec.get_facecolor()[0].tolist())

    bounds = contour_in.levels
    if extend == "both":
        bounds_ext =[contour_in.levels[0]-1] + list(bounds) +[contour_in.levels[-1]+1]
        norm = mpl.colors.BoundaryNorm(bounds, len(colors[1:-1]))
        cmap_auto = mpl.colors.ListedColormap(colors[1:-1])
        cmap_auto.set_under(colors[0])
        cmap_auto.set_over(colors[-1])
    elif extend == "min":
        bounds_ext =[contour_in.levels[0]-1] + list(bounds) 
        norm = mpl.colors.BoundaryNorm(bounds, len(colors[1:]))
        cmap_auto = mpl.colors.ListedColormap(colors[1:])        
        cmap_auto.set_under(colors[0])
    elif extend == "max":
        bounds_ext = list(bounds) +[contour_in.levels[-1]+1]
        norm = mpl.colors.BoundaryNorm(bounds, len(colors[:-1]))
        cmap_auto = mpl.colors.ListedColormap(colors[:-1])        
        cmap_auto.set_over(colors[-1])    
         
    ext=np.min([1.0/len(colors),0.08])
    
    g=mpl.colorbar.ColorbarBase(ax1,   
                            cmap =cmap_auto,
                            norm=norm,
                            boundaries=bounds_ext,
                            extend=extend,
                            extendfrac=kwargs.pop("extendfrac",ext),
                           # ticks=bounds,
                            spacing='proportional',
                            orientation=kwargs.get("orientation",'vertical'))
                                
    return g         
        
def define_color_bar_contour(contour,colorbar_title,orientation="vertical",show=False,opt=dict()):        
    if orientation != "vertical":
        fig = plt.figure(figsize = (10,2))
        ax1 = fig.add_axes([0.05, 0.65, 0.9, 0.30])
        if contour.extend != "neither": 
            g =fix_for_contour_colorbar(contour,ax1=ax1,orientation="horizontal",extend=contour.extend)
            
        else:
            g=fig.colorbar(contour,cax=ax1, spacing='proportional',orientation='horizontal') 
            
        g.ax.tick_params(labelsize=20)
        if show: 
            plt.show()
        else:
            plt.savefig(colorbar_title)
        plt.close()
        
    else:
        
        fig = plt.figure(figsize = (2.5,10))
        ax1 = fig.add_axes([0.05, 0.15, 0.2, 0.75])
        
        #print("In define_color_bar_contour",contour.extend)
        
        if contour.extend != "neither":
            g=fix_for_contour_colorbar(contour,ax1=ax1,extend=contour.extend)
        else:
            g=fig.colorbar(contour,cax=ax1, spacing='proportional') 
            
            
        g.ax.tick_params(labelsize=18)
        if "units" in opt:
            g.ax.text(4.2,.5, "(in "+opt["units"]+")",
                  rotation='vertical',rotation_mode='anchor', va='bottom', ha='center', fontsize=22,stretch=1000)
        if "topcolor" in opt: 
            g.ax.text(2.1,1.05,opt["topcolor"], va='bottom', ha='center', fontsize=22,stretch=1000)
        if "botcolor" in opt: 
            g.ax.text(2.1,-0.1,opt["botcolor"], va='bottom', ha='center', fontsize=22,stretch=1000)    
        plt.xticks(rotation=45)
        if show: 
            plt.show()
        else:
            plt.savefig(colorbar_title)
        plt.close()

            


def define_color_bar_pixel_wwmf(cmap,colorbar_title,orientation="vertical",min_value=None,max_value=None,opt=dict()):
    if orientation != "vertical":
        fig = plt.figure(figsize = (10,1))
        ax1 = fig.add_axes([0.05, 0.55, 0.9, 0.40])
        norm = mpl.colors.Normalize(vmin=min_value, vmax=max_value)
        cb=mpl.colorbar.ColorbarBase(ax1,cmap=cmap,orientation='horizontal',norm=norm)        
        cb.ax.tick_params(labelsize=20)
        plt.savefig(colorbar_title)
        plt.close()
    else:
        #print("estce quon passe ici?")
        fig = plt.figure(figsize = (2,10))
        ax1 = fig.add_axes([0.05, 0.02, 0.2, 0.97])
        
        if 'color_bar_type' in opt:            
            #print('on est rentre dans la colorbar discrete')
            if opt["color_bar_type"] == 'discrete':
                if "bins" in opt.keys(): 
                    #print("est-ce qu on rentre la?")                    
                    N=opt['bins']
                    newcmp = ListedColormap(opt["rgb_color"])                    
                    bounds=np.linspace(0,N,N+1)
                    ticks_new=bounds[:-1]+0.5 
                    cb=mpl.colorbar.ColorbarBase(ax1,cmap=newcmp,boundaries=bounds,ticks=ticks_new)      
                    cb.ax.set_yticklabels(np.unique(opt["code_WWMF"]))
                    cb.ax.tick_params(labelsize=13)
                    if "units" in opt:
                        print("units?")
                        cb.ax.text(4,.5, "(in "+opt["units"]+")",
                              rotation='vertical',rotation_mode='anchor', va='bottom', ha='center', fontsize=22,stretch=1000)
                    if "topcolor" in opt: 
                        print("topcolor?")
                        cb.ax.text(2,1.05,opt["topcolor"], va='bottom', ha='center', fontsize=20,stretch=1000)
                    if "botcolor" in opt: 
                        print("botcolor?")
                        cb.ax.text(2,-0.1,opt["botcolor"], va='bottom', ha='center', fontsize=20,stretch=1000)    
                    plt.xticks(rotation=45)
                    plt.savefig(colorbar_title)
                    plt.close()

def colorbar_definition_wwmf(N,name,variable=None):
    """ name is a colormap name (eg viridis) and N is the number of code elements (eg 44 for WWMF)"""
    dirname = os.path.dirname(__file__)
    file_CodesWWMF = os.path.join(dirname, '../utils/CodesWWMF.csv')
    
    df = pandas.read_csv(file_CodesWWMF,usecols = (0,1,2,3,6,7),sep=',')  
        
    if variable is not None:
        if variable == "WWMF":
            code_WWMF    = df['Code WWMF'].to_numpy()
            color_critic ={"15":"skyblue","32":"gold","33":"orange","38":"darkorange","39":"olive","49":"tan","53":"pink","58":"purple",\
                   "59":"yellow","60":"dodgerblue","62":"cyan","63":"fuchsia","70":"pink","73":"grey","77":"grey","78":"gray","80":"silver","83":"springgreen",\
                   "84":"lime","85":"limegreen","90":"red","97":"brown","98":"indianred","99":"black"}
        elif variable == "WME":
            code_WWMF    = np.unique(df['Code WME'].to_numpy())
            color_critic ={"4":"gold","5":"darkorange","7":"tan","9":"pink",\
                   "10":"cyan","11":"fuchsia","14":"pink","13":"grey","15":"silver",\
                   "16":"lime","18":"red","19":"brown"}
        elif variable == "W1":
            code_WWMF    = np.unique(df['Code W1'].to_numpy())  
            color_critic ={"2":"gold","3":"orange","5":"darkorange","6":"olive","8":"tan","11":"pink","14":"purple",\
                   "16":"cyan","17":"fuchsia","19":"pink","20":"grey","22":"silver",\
                   "23":"lime","24":"red","28":"indianred","26":"black"}
    if name==None:
        name='viridis'
    
    cmap=cm.get_cmap(name, N)
        
    newcolors_l = [rgb2hex(x) for x in cmap(range(N))]
    newcolors = xr.DataArray(newcolors_l)
    
    #print("avant color_critic",newcolors) 
    
    newcolors_rgb = [cmap(i) for i in range(N)]
    
    #print("color rgb",newcolors_rgb)
        
    for icode,code in enumerate(color_critic): 
        newcolors = newcolors.where(code_WWMF!=int(code),to_hex(color_critic[code]))
        newcolors_rgb[np.where(code_WWMF==int(code))[0][0]]=to_rgba(color_critic[code])
        
    #print("apres",newcolors) 
    
    return newcolors, newcolors_rgb
    

def return_geojson_pixel_wwmf(mat,opt=dict(),colorbar_title="colorbar.png",**kwargs):
    """
        Return a geojson (by pixel) from a data_array. 
        Make the hypothesis of a regular lat/lon grid. 
        
        Keywords : 
            mat : a data_array with latitude and longitude as dimension. Otherwise an error is raised.
            opt : a dictionnary of options ['save','save_colorbar','colorbar_title'....]
            geojson_title = 'test.json' : output file (if 'save' is True in opt)
            
        Hitory : 
            - Creation 2018/05 (Vincent Chabot )
            - Modif  2018/09 (Vincent Chabot) : Add an ax in order to be ok for external purposes. Backward compatibility not checked. 
            - Modif 2019/08 (V. Chabot) : Change everything to rely more on geojson. 
                              Performance increase : From 5.24 s to 300 ms on a small file (0.25 grid over France)
                                                     From 3m18 to 3.4s on a large file (0.5 grid over part of Europe)
                              
    """
 #   print("opt",opt)

    min_value = mat.min()  # Lowest value
    max_value = mat.max() 
    cmap=cm.RdBu
    if "vmin" in opt.keys(): 
        min_value=opt["vmin"]
    if "vmax" in opt.keys(): 
        max_value=opt['vmax'] 
    if "cmap" in opt.keys(): 
        cmap=opt['cmap']  
    if "bins" in opt.keys(): 
        N=opt['bins']
        
    dirname = os.path.dirname(__file__)
    file_CodesWWMF = os.path.join(dirname, '../utils/CodesWWMF.csv')    
    df = pandas.read_csv(file_CodesWWMF,usecols = (0,1,2,3,6,7),sep=',')   
        
        
    # Definition des couleurs 
    #print("In return_geojson_pixel_wwmf is %s"%kwargs.get("variable"))
    if kwargs.get("variable") is not None:
        if kwargs.get("variable") == "WWMF":
            code_WWMF=df['Code WWMF'].to_numpy()  
        elif kwargs.get("variable") == "WME":
            code_WWMF=np.unique(df['Code WME'].to_numpy())
        elif kwargs.get("variable") == "W1":
            code_WWMF=np.unique(df['Code W1'].to_numpy())            
        N=len(np.unique(code_WWMF))
        opt['bins']=N 
        newcolors, newcolors_rgb = colorbar_definition_wwmf(N,'viridis',variable=kwargs.get("variable"))
    else: 
        newcolors, newcolors_rgb = colorbar_definition_wwmf(N,'viridis')
    
    opt["code_WWMF"]= code_WWMF
    opt["rgb_color"] = newcolors_rgb    
    
    colors=np.ndarray(np.shape(mat), dtype=str)
    colhex=xr.DataArray(colors)   
    
    mat0 = mat.values.copy()
    mat0[np.isnan(mat0)] = -1
    
    for k in range(N):
        colhex = colhex.where(mat0!=code_WWMF[k],newcolors[k])      
    
    ds_c = xr.Dataset()
    ds_c["colors"] = (("latitude","longitude"),colhex)
    ds_c["latitude"] = mat.latitude
    ds_c["longitude"] = mat.longitude
    ds_c["values"]=(("latitude","longitude"),mat.values)
    
    # Make hyphothesis of a regular grid 
    stepX=(mat.latitude.values[0]-mat.latitude.values[1])/2.0
    stepY=(mat.longitude.values[0]-mat.longitude.values[1])/2.0
    
    df = ds_c.to_dataframe().dropna(axis=0)
    col_to_drop = list(set(df.columns)-set(["colors","values"]))
    df = df.drop(columns=col_to_drop)
    
    l_feature=[]
    for coord in df.reset_index().values:         
   
        l_feature.append(geojson.Feature(geometry=geojson.MultiPolygon([([([(coord[1]-stepY,coord[0]-stepX),
                                                                        (coord[1]-stepY,coord[0]+stepX),
                                                                        (coord[1]+stepY,coord[0]+stepX),
                                                                        (coord[1]+stepY,coord[0]-stepX),
                                                                        (coord[1]-stepY,coord[0]-stepX),]),])]),
                                         properties={"fill":coord[2],
                                                     "fill-opacity":0.7,
                                                     "stroke":coord[2],
                                                     "value":coord[3]}))    
    res = geojson.FeatureCollection(l_feature)
    if opt.get("save_colorbar",False):
        if "orientation" in opt:
            define_color_bar_pixel(cmap,colorbar_title,min_value=min_value,
                                 max_value=max_value,orientation=opt["orientation"],opt=opt)
        else: 
            #print("on rentre ici?")            
            define_color_bar_pixel_wwmf(cmap,colorbar_title,min_value=min_value,max_value=max_value,opt=opt)
    else: 
        log.info("We do not save colorbar. If you want to do so, set save_colorbar option to True")
  
    if opt.get("save",False):
        with open("test_contour.json",'w') as fp: 
            geojson.dump(res,fp) 
    
    return str(res)

#------------------------------------------------------------------------
#                    Fin de la définition du geojson
#------------------------------------------------------------------------
