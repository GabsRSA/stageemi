"""
Develop by V. Chabot for WeahterForce
"""
from matplotlib.colors import rgb2hex
from geojson import Feature
from geojson import FeatureCollection
from skimage.measure import  subdivide_polygon
import shapely as sh 
import matplotlib.path as path
import numpy as np
import shapely.geometry as sh
import shapely.ops 


import logging 
log = logging.getLogger('geojson creation')
formatter = logging.Formatter('%(asctime)s - %(levelname)s -  %(name)s -%(message)s')
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(formatter)
log.addHandler(consoleHandler)
log.setLevel(logging.INFO)




def handle_LineString(bad_geo_list):
    """
        Try to handle error due to LineString 
    """
    bad_list = []
    for elt in range(len(bad_geo_list)):
        try: 
            sh.MultiPolygon([bad_geo_list[elt],])
        except ValueError: 

            bad_geo_list[elt] = remove_LineString(bad_geo_list[elt])
    return sh.MultiPolygon(bad_geo_list)

def remove_LineString(bad_geo):
    temp = bad_geo.__geo_interface__.copy()
    l_remove =[]
    for x in range(len(temp["geometries"])):
        if temp["geometries"][x]["type"] == "LineString":
            l_remove.append(x)
    l_remove.sort()
    for elt in l_remove:
        temp["geometries"].pop(elt)
    if len(temp["geometries"]) == 1:   
        return sh.asShape(temp["geometries"][0])
    else: 
        return sh.asShape(temp)
    
def return_smoother_poly(poly,**kwargs):
    new_poly=poly.copy()
    for _ in range(kwargs.get("level",5)):
        new_poly = subdivide_polygon(new_poly, degree=kwargs.get("degree",2), preserve_ends=True)

    return new_poly


def return_new_mpl_path(pathin,**kwargs):
    end_index = np.where(pathin.codes == pathin.CLOSEPOLY)[0]
    for i in range(len(end_index)):
        if i==0:
            new_vertex = return_smoother_poly(pathin.vertices[0:end_index[i]],**kwargs)
            new_codes = 2*np.ones(len(new_vertex))
            new_codes[0]=1
            new_codes[-1]=79
        else: 
            if end_index[i]-end_index[i-1] >=4:
                temp_vertex = return_smoother_poly(pathin.vertices[end_index[i-1]+1:end_index[i]],**kwargs)
                temp_codes = 2*np.ones(len(temp_vertex))
                temp_codes[0]=1
                temp_codes[-1]=79
                new_vertex =np.concatenate([new_vertex,temp_vertex])
                new_codes = np.concatenate([new_codes,temp_codes])
            else: 
                if kwargs.get("debug",False):
                    print("Taille petite",end_index[i],end_index[i-1])
                    print("Polygone supprimer")
                    
    new_path = path.Path(new_vertex,codes=new_codes)
    return new_path

def get_valid_polygon(poly): 
    p = sh.asPolygon(poly)
    if p.is_valid: 
        return p 
   # else: 
   #     return p.simplify(0.00001,preserve_topology=False)
    
    pb = p.buffer(1e-9)
    if p.area>0:
        d_area = (p.area-pb.area)/p.area
        if abs(d_area) < 1e-5:
            return pb 
    
    line_non_simple = sh.LineString(poly)
    mls = shapely.ops.unary_union(line_non_simple)
    polygons = list(shapely.ops.polygonize(mls))
    if len(polygons)> 1: 
        polyf= sh.Polygon(polygons[0])
        for i in np.arange(1,len(polygons)): 
            polyf=polyf.union(sh.Polygon(polygons[i]))
        return polyf
    elif polygons != []: 
        return  sh.Polygon(polygons[0])
    else: 
        return sh.Polygon([])
    

def polygon_frompath(path_in,**kwargs):
    poly_in = path_in.to_polygons()
    
    if len(poly_in)<=0:
        return None 
    
    if kwargs.get("smoothing",False):
        path_ex=return_new_mpl_path(path_in,**kwargs)
    else:
        path_ex = path_in 
        
    poly=path_ex.to_polygons()
    if len(poly)>0 and len(poly[0]) > 3:
        # Enable to get rid of singular polygons (points)
        poly_final=get_valid_polygon(poly[0])
        for p in range(0,len(poly)-1):
            if len(poly[p+1])>3:
                # Permet d'eviter les lignes
                poly1 = get_valid_polygon(poly[p+1])
                if poly_final.contains(poly1):
                    poly_final = poly_final.difference(poly1)
                else:
                    poly_final = poly_final.union(poly1)
    else: 
        poly_final = None 
        
    
    return poly_final


        
def polygon_fromcollection(collection,**kwargs):
    """
        Return a MultiPolygon
    """
    poly_list=[]
   
    path_nb=0
    for path_ex in collection.get_paths():
        if kwargs.get("debug",False):
            path_nb +=1
        new_polygon = polygon_frompath(path_ex,**kwargs)
        if new_polygon != None:
            poly_list.append(new_polygon)
        else:  
            log.debug("Deleting empty polygon")
    try:
        r = sh.MultiPolygon(poly_list)
    except Exception as e: 
        r = handle_LineString(poly_list)
        
    res = Feature(geometry=sh.mapping(r.simplify(kwargs.get("simplify",0.01))))
    res["properties"] = {"fill":rgb2hex(collection.get_facecolor()[0])}
    if "message" in kwargs:
        res["properties"]["message"] = kwargs.get("message")
            
    return res 

def message_for_contours(contours,nb):
    levels = contours.levels
    if contours.extend == "both" or contours.extend == "min":
        levels = np.concatenate([np.asarray([-np.nan]),contours.levels])

    nb_contour = len(contours.levels)
    if contours.extend == "max":
        nb_contour = nb_contour-1
    
    if nb == 0 and (contours.extend == "both" or contours.extend == "min"):
        message = "Inferior at "+str(levels[nb+1])
    elif (nb >= nb_contour and contours.extend == "both") or (nb >= nb_contour and contours.extend == "max"):
        message = "Superior at " +str(levels[nb_contour])
    else: 
        message = "Between "+str(levels[nb])+" and " + str(levels[nb+1])
    return message


contour_async = []
def collect_results(res):
    if res is not None:
        contour_async.append(result)



def contourf_geo_normal(contourf,**kwargs): 
    polygon_list=list()             
    col=0   
    for collection in contourf.collections:
        log.debug("Collection is %s"%col)
        message = message_for_contours(contourf,col)   
        col +=1
        kwargs["message"]=message
        feature = polygon_fromcollection(collection,**kwargs)
        if isinstance(feature,list):
            log.error("Not normal mode. For test only.")
            return feature 
        polygon_list.append(feature)
    
    feature_collection = FeatureCollection(polygon_list)
    return feature_collection

def contourf_geo(contourf,**kwargs):
    """
    From a mpl contourf, provides a Geojson. 
    Options are : 
       - smoothing (bool:False)
       - degree (int:2): if smoothing, degree of the BSpline employed
       - level (int:5): if smoothing number of level of smoothing 
       - simplify (float:0.01) : simplification of the polygon to apply. A higher number means more simplification
    """
#    final = contourf.collections.copy()
#    for x in contourf.collections:
#        if x.get_paths() == list(): 
#            final.remove(x)
#    contourf.collections=final
#    print("contour_geo : ",len(final))
#    if mp_valid and len(contourf.collections)>2:
#        return contourf_geo_mp(contourf,**kwargs)
#    else: 
    #if kwargs.pop("parallel",True):
    #    print("Doing parallel")
    #    return contourf_geo_mp(contourf,**kwargs)
    #else:
    return contourf_geo_normal(contourf,**kwargs)
    