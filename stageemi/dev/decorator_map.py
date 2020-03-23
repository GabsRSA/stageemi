"""
Develop by V. Chabot for WeatherForce
"""
from io import BytesIO
from  stageemi.dev.geojson_shapefile import return_geojson, apply_style,apply_style_wwmf
from ipyleaflet import Map,GeoJSON
import ipywidgets as widgets
import shapely.geometry as geom
import json 
import matplotlib.pyplot as plt 
import functools
import xarray as xr 
import numpy as np 
import matplotlib.cm as cm
import pandas

import logging 
log = logging.getLogger('decorator_geojson')
formatter = logging.Formatter('%(asctime)s - %(levelname)s -  %(name)s -%(message)s')
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(formatter)
log.addHandler(consoleHandler)
log.setLevel(logging.INFO)



def crop_country(geodata,country_file):
    """
        History : 
           Handle singular topology error : When croping some topological error could occured. 
           Croped data could exhibit singularity which should be taken into account. 
    """
    with open(country_file) as geojson1:
            poly1_geojson = json.load(geojson1)
        # Selon le type de fichier en entree on n'aura pas toujours ca 
    if "geometry" in poly1_geojson.keys():
            poly1 = geom.asShape(poly1_geojson['geometry'])
    else: 
        for nb in range(len(poly1_geojson["features"])):
            p =  geom.asShape(poly1_geojson["features"][nb]["geometry"])
            if nb >0:
                poly1 = poly1.union(p)
            else: 
                poly1 = p  
            #poly1 = geom.asShape(poly1_geojson["features"][0]["geometry"])

    for n in np.arange(0, len(geodata['features'])):
            old_poly = geom.asShape(geodata['features'][n]["geometry"]).buffer(1e-5)
    
            geodata["features"][n]["geometry"]=old_poly.intersection(poly1).__geo_interface__.copy()

def mpl_visu(func):
    """
    Decorateur permettant de faire une visu mpl a partir d'un dataset 
    Le modifier pour prendre en entree la variable du dataset a plotter. 
    (et mettre un comportement sans argument pour le dataarray)
    """
    @functools.wraps(func)
    def wrapper(*args,**kwargs):
        value = func(*args,**kwargs)
        if isinstance(value,xr.DataArray):
            fig = plt.figure(figsize=(20, 16))
            ax = fig.add_subplot(1, 1, 1)
            value.plot.contourf(ax=ax,levels=10,extend="max")
        return fig
    return wrapper



def gogeojson_wwmf(_func=None,varin="vartoplot",country_file=None,**deco):
    plot_options = {}
    plot_options["vmin"]= -1
    plot_options["vmax"]= 99
    plot_options["bins"]=44
    plot_options["type"]=deco.get("type","Pixel")
    plot_options["cmap"]=deco.get("cmap",cm.viridis)
    plot_options["save_colorbar"]=True
    plot_options["color_bar_type"]= 'discrete'
#     print("plot_options",plot_options)
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args,**kwargs):
            legend_file = BytesIO()
            value = func(*args,**kwargs)
            
            if isinstance(value,xr.Dataset):
#                 print("par ici")
                if np.isnan(value[varin].values).all():
                    return None,None
                else:
                    geojson_str = return_geojson(value[varin], plot_options, legend_file, smoothing=False,simplify=0.001)
            else: 
#                 print("par la")
                if np.isnan(value.values).all():
#                     print("par la, par ici")
                    return None,None
                else:
#                     print("par la, par la")
                    geojson_str = return_geojson(value, plot_options, legend_file,smoothing=False,simplify=0.001)
            geojson_data = json.loads(geojson_str)
            if country_file is not None: 
                crop_country(geojson_data,country_file=country_file)
            apply_style_wwmf(geojson_data["features"])    
            return geojson_data,legend_file
        return wrapper

    if _func is None:
        return decorator                      
    else:
        return decorator(_func)  
    
def gogeojson(_func=None,varin="vartoplot",country_file=None,**deco):
    plot_options = {}
    plot_options["bins"]=deco.get("bins",10)
    plot_options["type"]=deco.get("type","Contour")
    plot_options["cmap"]=deco.get("cmap",cm.RdBu_r)
    plot_options["save_colorbar"]=True
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args,**kwargs):
            legend_file = BytesIO()
            value = func(*args,**kwargs)
            
            if isinstance(value,xr.Dataset):
                if np.isnan(value[varin].values).all():
                    return None,None
                else:
                    geojson_str = return_geojson(value[varin], plot_options, legend_file, smoothing=False,simplify=0.001)
            else: 
                if np.isnan(value.values).all():
                    return None,None
                else:
                    geojson_str = return_geojson(value, plot_options, legend_file,smoothing=False,simplify=0.001)
            geojson_data = json.loads(geojson_str)
            if country_file is not None: 
                crop_country(geojson_data,country_file=country_file)
            apply_style(geojson_data["features"])    
            return geojson_data,legend_file
        return wrapper

    if _func is None:
        return decorator                      
    else:
        return decorator(_func)         

def overwrite_parameters(old,new):
    """
    Fonction permettant de mettre a jours les parametres 
    """
    for key in new:
        if key in old: 
            log.warning("Changing key %s from %s to %s"%(key,old[key],new[key]))
            old[key]=new[key]
            
            
def do_ipy_map(_func=None,**kwargs_dec):
    """
      Enable to plot with ipyleaflet an xarray variable. 
      Some options can be filled when decorating a function : 
         - bins 
         - cmap (colormap)
         - simplify (float)
         - smoothing (Boolean)
      This options can be overwritten by kwargs argument of the decorated function. 
    """
    
    plot_options = {}
    plot_options["bins"]=kwargs_dec.get("bins",10)
    plot_options["type"]=kwargs_dec.get("type","Contour")
    plot_options["cmap"]=kwargs_dec.get("cmap",cm.RdBu_r)
    plot_options["save_colorbar"]=kwargs_dec.get("save_colorbar",False)
    other_options={}
    other_options["simplify"]=kwargs_dec.get("simplify",0.01)
    other_options["smoothing"]=kwargs_dec.get("smoothing",True) 
        
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args,**kwargs):
            legend_file = BytesIO()
            
            value = func(*args,**kwargs)
            
            overwrite_parameters(other_options,kwargs)
            overwrite_parameters(plot_options,kwargs)
            
           
            if isinstance(value,xr.Dataset):
                if "varin" not in kwargs_dec:
                    print("Error")
                geojson_str = return_geojson(value[kwargs_dec.get("varin")],
                                             plot_options, legend_file,**other_options)
                name = kwargs_dec.get("varin")
            else: 
                name = value.name 
                geojson_str = return_geojson(value, plot_options, legend_file,**other_options)
                
            geojson_data = json.loads(geojson_str)
            
            apply_style(geojson_data["features"]) 
            #if "country_file" in kwargs_dec: 
            #    crop_country(geojson_data,country_file=kwargs_dec.get("country_file"))            
            
            geojson_layer = GeoJSON(data=geojson_data,name=name)
            map_out = Map(zoom=6,center=(float(value.latitude.mean().values),float(value.longitude.mean().values)))
            map_out.add_layer(geojson_layer)
            
            if kwargs_dec.get("borders",False):
                if "country_file" in kwargs_dec: 
                    bord = Borders(fname=kwargs_dec.get("country_file"),color="black")
                    map_out.add_layer(bord)
            if plot_options["save_colorbar"]:      
                legend_file.seek(0)
                legend = widgets.Image(layout=widgets.Layout(height="430px"))
                legend.value = legend_file.read()            
                widg_out = widgets.HBox([map_out,legend])
            else: 
                widg_out = map_out 
            return widg_out
        return wrapper

    if _func is None:
        return decorator                      
    else:
        return decorator(_func) 
