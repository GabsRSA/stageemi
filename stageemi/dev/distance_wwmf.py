import os 
import pandas as pd 
import xarray as xr 
import numpy as np


def to_categorical(y, num_classes=None, dtype='float32'):
  """
  Fonction piquée dans Tensorflow (mais bon ça vaut pas le coup d'importer tf pour ça)
   
  
  
  Converts a class vector (integers) to binary class matrix.
  E.g. for use with categorical_crossentropy.
  Arguments:
      y: class vector to be converted into a matrix
          (integers from 0 to num_classes).
      num_classes: total number of classes.
      dtype: The data type expected by the input. Default: `'float32'`.
  Returns:
      A binary matrix representation of the input. The classes axis is placed
      last.
  """
  y = np.array(y, dtype='int')
  input_shape = y.shape
  if input_shape and input_shape[-1] == 1 and len(input_shape) > 1:
    input_shape = tuple(input_shape[:-1])
  y = y.ravel()
  if not num_classes:
    num_classes = np.max(y) + 1
  n = y.shape[0]
  categorical = np.zeros((n, num_classes), dtype=dtype)
  categorical[np.arange(n), y] = 1
  output_shape = input_shape + (num_classes,)
  categorical = np.reshape(categorical, output_shape)
  return categorical

def conversion(ds,name):
    """convert wwmf into wme (compas) or w1 (agat) code"""
    dirname = os.path.dirname(__file__)
    file_CodesWWMF = os.path.join(dirname,'../utils/CodesWWMF.csv')

    df_WWMF = pd.read_csv(file_CodesWWMF,usecols = (0,1,2,3,6,7),sep=',')
    if name=="compas":
        var_name="wme_arr"
        col_name="Code WME"
        ds[var_name]=ds.unknown
    elif name=="agat":
        var_name="w1_arr"
        col_name="Code W1"
        ds[var_name]=ds.unknown       
        
    elif name=="compas_asym":
        var_name="wme_asym_arr"
        col_name="Code WME"
        ds[var_name]=ds.unknown      
    elif name=="agat_asym":
        var_name="w1_asym_arr"
        col_name="Code W1"
        ds[var_name]=ds.unknown 

    for iwwmf,wwmf in enumerate(df_WWMF["Code WWMF"]):
        ds[var_name]=ds[var_name].where(ds.unknown!=wwmf,df_WWMF[col_name][iwwmf])
    return ds

def xarray_cat(da,mask=None):
    """
    Fait du categoriel avec xarray. 
    Suppose que les entrées sont des entiers positifs. 
    Attention :les nan sont des 0. 
    """
    y = da.astype(np.uint8).values
    cat = to_categorical(y)
    sh = cat.shape 
    dout = xr.Dataset()
    dout[da.name] = (tuple(list(da.dims) + ["wwmf"]),cat)
    for dim in da.dims: 
        dout[dim] = da[dim]
    dout["wwmf"] = range(sh[-1])
    #dout = dout.sel(wwmf=slice(1,sh[-1]))# On vire l'indice 0
    return dout 
    
def get_matrix(name):
    """
    Retourne la matrice de distance sous forme de xarray 
    """
    dirname = os.path.dirname(__file__)
    if name == "compas":
        fname_dist = os.path.join(dirname,'../utils/distance_compas.csv')
        df_dist = pd.read_csv(fname_dist,sep=',')
        var_name="wme_arr"
        varsh="wme_c_"
        
    elif name == "agat":
        fname_dist = os.path.join(dirname,'../utils/distance_agat.csv')
        df_dist = pd.read_csv(fname_dist,sep=',')  
        var_name="w1_arr"
        varsh="w1_c_"
        
    elif name == "compas_asym":
        fname_dist = os.path.join(dirname,'../utils/distance_compas_asym.csv')
        df_dist = pd.read_csv(fname_dist,sep=',')
        var_name="wme_asym_arr"
        varsh="wme_asym_c_"
        
    elif name == "agat_asym":
        fname_dist = os.path.join(dirname,'../utils/distance_agat_asym.csv')
        df_dist = pd.read_csv(fname_dist,sep=',')  
        var_name="w1_asym_arr"
        varsh="w1_asym_c_"

    col_name = df_dist.columns[0]
    index = df_dist[col_name]
    values = df_dist.set_index(col_name).values
    mat = xr.Dataset()
    mat["distance"] = (("wwmf","wwmf_2"),values)
    mat["wwmf"] = index.values
    mat["wwmf_2"] = index.values
    mat["distance"].attrs["var_name"] = var_name
    return mat["distance"]

def get_pixel_distance_dept(ds_dept,name):
    " On donne en entree le dataset du departement et le nom de la distance considérée "
    dconvert = conversion(ds_dept,name)
    distance_matrix = get_matrix(name)
    dcat = xarray_cat(dconvert[distance_matrix.var_name])
    return dcat[distance_matrix.var_name].dot(distance_matrix)