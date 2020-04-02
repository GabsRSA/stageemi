import os 
import ipyleaflet as ipyl
import xarray as xr 
import ipywidgets as widg 
import geoviews.util as gu 
import geoviews as gv 
import shapely as sh
from geojson import FeatureCollection,Feature
import matplotlib.cm as cm
from matplotlib.colors import rgb2hex
import numpy as np 
from collections.abc import Iterable
import pandas as pd 

  
def get_valid_polygon(poly): 
    """
    Modifie la geometrie d'entree de telle sorte a avoir un polygone valide en sortie. 
    """
    p = sh.geometry.asPolygon(poly)
    if p.is_valid: 
        return p 
    pb_bis = p.buffer(1e-5).buffer(-1e-5)
    if pb_bis.area>0:
        return pb_bis 

    line_non_simple = sh.geometry.LineString(poly)
    mls = sh.ops.unary_union(line_non_simple)
    polygons = list(sh.ops.polygonize(mls))
    if len(polygons)> 1: 
        "Case with multiple polygons"
        polyf= sh.geometry.Polygon(polygons[0])
        for i in np.arange(1,len(polygons)): 
            polyf=polyf.union(sh.geometry.Polygon(polygons[i]))
        return polyf
    elif polygons != []: 
        "Case with one polygon"
        return  sh.geometry.Polygon(polygons[0])
    else: 
        return sh.geometry.Polygon([])
    return sh.geometry.Polygon([])
    
def change_invalid_polygon(geo_contour):
    import shapely.ops 
    l_poly = []
    if geo_contour.geom_type == 'MultiPolygon':
        for poly in geo_contour.geoms:
            if poly.is_valid:
                l_poly.append(poly)
            else: 
                validpoly = get_valid_polygon(poly.exterior)            
                if validpoly.area > 0 :
                    if validpoly.geom_type == 'MultiPolygon':
                        for poly_p in validpoly.geoms: 
                            l_poly.append(poly_p)
                    else:
                        l_poly.append(validpoly)
    elif geo_contour.geom_type == "Polygon":
        l_poly.append(get_valid_polygon(geo_contour.exterior))
    else:
        raise(ValueError("Case not handled for geomety of type %s"%geo_contour.geom_type))
    valid_multipolygon = sh.geometry.asMultiPolygon(l_poly)
    if valid_multipolygon.is_valid:
        return valid_multipolygon 
    else:
        "It should be cause by the fact that some polygons intersect. So changing them."
        temp_poly = sh.geometry.Polygon([])
        for poly in l_poly: 
            temp_poly = temp_poly.union(poly)
        return temp_poly
    
def get_contour(ds,lat_name ="latitude",lon_name="longitude",levels=10,**kwargs):
    """
    get_contour [summary]
    
    Arguments:
        ds {DataArray} -- A 2D dataArray
    
    Keyword Arguments:
        lat_name {str} -- Dimension name for latitude (default: {"latitude"})
        lon_name {str} -- Dimension name for longitude (default: {"longitude"})
        levels {int,list} -- Number of levels or list of levels for contours  (default: {10})
    """
    if not isinstance(ds,xr.core.dataarray.DataArray): 
        raise(ValueError("In get_geojson_contour, input dataset should be a DataArray. Get :"%type(ds)))
        
    if len(ds.dims) != 2:
        raise(ValueError("Dataset should be 2D"))
        
    if lat_name not in ds.dims or lon_name not in ds.dims: 
        raise(ValueError("Latitude or longitude name are not present. Should get %s %s and get %s"%(lat_name,lon_name,ds.dims)))
    
    gv.extension("bokeh")  
    hv_ds = gv.Dataset(ds,[lon_name,lat_name])
    level_list = np.asarray(levels).astype(np.int)

    contours = gv.operation.contours(hv_ds,filled=True,levels=level_list)
    
    
    #contours = gv.operation.contours(hv_ds,filled=True,levels=levels)
    #print("In geo_contour",contours,type(contours))
    
    
    
    polygon_list=list() 
    dict_poly = gu.polygons_to_geom_dicts(contours)    
    #print("In geo_contour",dict_poly)
    cmap = kwargs.get("cmap",cm.RdBu)
    mini = kwargs.get("mini",list(contours.data[0].values())[0])
    maxi = kwargs.get("maxi",list(contours.data[-1].values())[0])

    for i in range(len(dict_poly)):
        list_poly=[]
        for holes in dict_poly[i]["holes"]: 
            l_p = [sh.geometry.Polygon(x) for x in holes]
            if len(l_p)>0:
                list_poly.extend(l_p)
        if len(list_poly):
            mp_holes = sh.geometry.MultiPolygon(list_poly)
            mp_init = dict_poly[i]["geometry"]
            if not mp_init.is_valid: 
                mp_init = change_invalid_polygon(mp_init)
            if not mp_holes.is_valid: 
                mp_holes = change_invalid_polygon(mp_holes)   
            mp_final = mp_init - mp_holes
        else:
            if not dict_poly[i]["geometry"].is_valid:
                mp_final = change_invalid_polygon(dict_poly[i]["geometry"])
            else:
                mp_final = dict_poly[i]["geometry"]
        
        if kwargs.get("qualitative",False) and not mp_final.is_empty:
            buffer_arg = kwargs.get("buffer",5e-4)
            mp_temp = mp_final.buffer(-buffer_arg).buffer(1.1*buffer_arg)    
            if mp_temp.area > 0:
                mp_diff = (mp_final - mp_temp)
                if mp_diff.area > 0 :
                    mp_final = mp_final - mp_diff
            else:
                mp_final = sh.geometry.Polygon([])
        
        ## On stock le resultat dans un geojson 
        # A voir s'il n'y a pas mieux a faire. 
        if not mp_final.is_empty:
            try:
                res = Feature( geometry = mp_final)
            except Exception: 
                mp_temp = mp_final.buffer(-1e-5).buffer(1.1*1e-5)
                res = Feature(geometry = mp_temp)
 
            if isinstance(levels,Iterable): 
                value = list(contours.data[i].values())[0]
                descending_list = np.sort(levels)[::-1]
                bound_min = descending_list[np.argmax(descending_list < value)]
                bound_max = levels[np.argmax(levels >=value)]
  

                res["properties"] = {
                    "value_min":bound_min*1.0,
                    "value_max":bound_max*1.0,
                    "units":ds.attrs.get('units'),
                    "name":ds.attrs.get("long_name",ds.name)
                }
            else:
                res["properties"] = {
                    "value":list(contours.data[i].values())[0],
                    "units":ds.attrs.get('units'),
                    "name":ds.attrs.get("long_name",ds.name)
                    }
        
            res["properties"]["cmap"] = {
                    "value":list(contours.data[i].values())[0],
                    "mini":mini*1.0,
                    "maxi":maxi*1.0,
                 }
            res["properties"]["style"] = {
                "fillColor": rgb2hex(cmap((list(contours.data[i].values())[0]-mini)/(maxi-mini))),
                "fillOpacity":0.9,
                "opacity": 0.2,
                "color": "#000000",
                "dashArray": '5',
                "weight": 2,
                }
            polygon_list.append(res)
        else:
            print("Empty polygon for ",list(contours.data[i].values())[0])
            
    feature_collection = FeatureCollection(polygon_list)
    return feature_collection 


def colorbar_definition_wwmf(N,name,variable=None):
    from matplotlib.colors import rgb2hex, to_hex, to_rgba
    """ name is a colormap name (eg viridis) and N is the number of code elements (eg 44 for WWMF)"""
    dirname = os.path.dirname(__file__)
    file_CodesWWMF = os.path.join(dirname, '../utils/CodesWWMF.csv')
    
    df = pd.read_csv(file_CodesWWMF,usecols = (0,1,2,3,6,7),sep=',')  
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
    if name == None:
        name='viridis'
    cmap=cm.get_cmap(name, N)
    newcolors_l = [rgb2hex(x) for x in cmap(range(N))]
    newcolors = xr.DataArray(newcolors_l)
    
    newcolors_rgb = [cmap(i) for i in range(N)]
    for icode,code in enumerate(color_critic): 
        newcolors = newcolors.where(code_WWMF!=int(code),to_hex(color_critic[code]))
        newcolors_rgb[np.where(code_WWMF==int(code))[0][0]]=to_rgba(color_critic[code])
    return newcolors, newcolors_rgb

def get_index(code,value):
    index = np.argmax(code == int(value))
    if index == 0:
        sum_1 = np.sum(code==int(value)) * True
        if not sum_1.astype(np.bool):
            " Le nombre n'est pas présent"
            return None 
    else:
        return index#hex_color[index].values.tolist()

def generate_discrete_colorbar(rgb_color,code,colorbar_title):
    from matplotlib.colors import ListedColormap
    import matplotlib as mpl
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize = (2,10))
    ax1 = fig.add_axes([0.05, 0.12, 0.2, 0.87])
    N = len(rgb_color)
    newcmp = ListedColormap(rgb_color)                    
    bounds=np.linspace(0,N,N+1)
    ticks_new=bounds[:-1]+0.5 
    cb=mpl.colorbar.ColorbarBase(ax1,cmap=newcmp,boundaries=bounds,ticks=ticks_new)      
    cb.ax.set_yticklabels(code)
    cb.ax.tick_params(labelsize=13)
    plt.xticks(rotation=45)
    plt.savefig(colorbar_title)
    plt.close()

def get_WeatherType_contour(da,variable,lat_name ="latitude",lon_name="longitude",colorbar_title="my_colorbar.png",**kwargs):
    
    dirname = os.path.dirname(__file__)
    file_CodesWWMF = os.path.join(dirname, '../utils/CodesWWMF.csv')    
    df = pd.read_csv(file_CodesWWMF,usecols = (0,1,2,3,6,7),sep=',') 
    if variable == "WWMF":
        df_crop = df[["Code WWMF","Legende WWMF"]].set_index("Code WWMF").rename(columns={"Legende WWMF":"Legende"})
    elif variable == "WME":
        df_crop = df[["Code WME","Legende WME"]].set_index("Code WME").drop_duplicates().rename(columns={"Legende WME":"Legende"})
    elif variable == "W1":
        df_crop = df[["Code W1","Legende W1"]].set_index("Code W1").drop_duplicates().rename(columns={"Legende W1":"Legende"})   
    else:
        raise(ValueError("Variable unkonwn : %s "%variable))
    ## On recupere les codes uniques de ce type de temps sensible         
    N = df_crop.size
    code_WWMF = df_crop.index.to_numpy().astype(np.int)
    code_WWMF.sort()
    
    hex_color, rgb_color = colorbar_definition_wwmf(N,'viridis',variable=variable)
     
    list_level = np.concatenate([np.asarray([code_WWMF[0]-1,]),np.unique(da.fillna(0)),np.asarray([code_WWMF[-1]+1,])]).astype(np.int)
    list_level.sort()
  
    
    da.name = "test"
    geo_contour = get_contour(da,levels=list_level,qualitative=True,buffer=2e-4)

    for contour in geo_contour["features"]:
        max_val = contour["properties"]["value_max"]
        index = get_index(code_WWMF,max_val)
        if index is not  None:
            contour["properties"]["style"]["fillColor"] = hex_color[index].values.tolist()
            contour["properties"]["legend"] = df_crop.loc[int(max_val),"Legende"]
        else:
            print("Index not found %s for this variable %s"%(max_val,variable))
            print(df_crop)
    generate_discrete_colorbar(rgb_color,code_WWMF,colorbar_title)
    # On va maintenant modifier les couleurs pour etre en accord avec la colorbar. 
    return geo_contour
