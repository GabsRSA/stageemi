#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 24 17:43:12 2020

@author: borderiesm

fonctions utiles pour le zonage

"""

import numpy as np
import xarray as xr
import pandas
import sklearn.metrics

def read_xarray(file): 
    data = xr.open_dataset(file)
    data["latitude"]  = data["latitude"].round(5)
    data["longitude"] = data["longitude"].round(5)
    data.close()
    return data

def conversion(ds,name):
    """convert wwmf into wme (compas) or w1 (agat) code"""
    
    file_CodesWWMF= '../utils/CodesWWMF.csv'
    df_WWMF = pandas.read_csv(file_CodesWWMF,usecols = (0,1,2,3,6,7),sep=',')
        
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
        #print(wwmf,df_WWMF["Code WME"][iwwmf])
        ds[var_name]=ds[var_name].where(ds.unknown!=wwmf,df_WWMF[col_name][iwwmf])
        
    return ds

'''
    fonctions de score
    https://www.nws.noaa.gov/oh/rfcdev/docs/Glossary_Verification_Metrics.pdf
'''
def hss(y_true, y_pred): 
    ''' Heidke Skill Score '''    
    tn, fp, fn, tp = sklearn.metrics.confusion_matrix(y_true,y_pred).ravel()
    
    if (fp+fn)*(tn+fp+fn+tp)+2*(tn*tp-fp*fn)>0:
        return 2*(tn*tp-fp*fn)/((fp+fn)*(tn+fp+fn+tp)+2*(tn*tp-fp*fn))
    else:
        return np.nan 

def f1(y_true, y_pred):
    ''' f1 score '''
    tn, fp, fn, tp = sklearn.metrics.confusion_matrix(y_true,y_pred).ravel()
    if (fp+tp) >0 and (tp+fn) >0: 
        precision = tp /(fp + tp)
        pod       = tp/(tp+fn) # = recall 
        return 2*precision * pod/(precision + pod)
    else:
        return np.nan
    
def pod(y_true,y_pred) : 
    ''' pod score '''
    tn, fp, fn, tp = sklearn.metrics.confusion_matrix(y_true,y_pred).ravel()
    if (tp+fn >0):
        return tp/(tp+fn)
    else:
        return np.nan
    
def far(y_true,y_pred): 
    ''' false alarm ratio: the number  of false alarms divided by the total number of events forecast '''
    tn, fp, fn, tp = sklearn.metrics.confusion_matrix(y_true,y_pred).ravel()
    if (fp+tp>0):
        return fp/(fp+tp)
    else:
        return np.nan
    
def pofd(y_true, y_pred): 
    ''' Prob of False Detection (false alarm divided by total number of event observed) '''
    tn, fp, fn, tp = sklearn.metrics.confusion_matrix(y_true,y_pred).ravel()
    if (fp + tn)>0:
        return fp/(fp + tn)
    else : 
        return np.nan 
        
def precision(y_true,y_pred):
    tn, fp, fn, tp = sklearn.metrics.confusion_matrix(y_true,y_pred).ravel()
    if (fp + tp > 0): 
        return tp/(fp + tp)
    else:
        return np.nan




'''
    fonctions qui permettent de comparer plusieurs masks et de créer des combinaisons de zones sympos
'''



def find_neighbours(mask_ref,listMasks): 
    '''  return: liste contenant les id des zones voisines à la zone définit par mask_ref '''
    lst_neighbours = []
    for  mask2compare in listMasks:
        if mask_ref.identical(mask2compare): 
            continue 
        else: 
            # Somme permet de savoir si des masques se touchent (car les zones voisines ont des pixels communs)
            somme          = np.sum((mask_ref.mask.values == 1) & (mask2compare.mask.values == 1))
            # tailleRef et taille2compare permettent de checker si un des deux masks n'est pas déjà inclu dans l'autre
            tailleRef      = np.sum(~np.isnan(mask_ref.mask.values ))
            taille2compare = np.sum(~np.isnan(mask2compare.mask.values ))
            if somme > 0 and somme!=tailleRef and somme!=taille2compare: 
                lst_neighbours.append(str(mask2compare.id.values))  
    return(lst_neighbours)

    
def check_existing_mask_v2(mask_temp,ds_mask):
    '''
        check if mask_temp already exists in ds_mask
        return: flag (= True is mask_temp already exists in ds_mask)       
    '''
    list_str = ds_mask.id.values
    for id in list_str:
        mask2compare = ds_mask.mask.sel(id = id)   
        #  A verifier si on a pas une condition plus simple du type    mask_temp.values ==  mask2compare.values
        somme = np.sum(mask_temp.values ==  mask2compare.values)
        norme = np.sum((~np.isnan(mask_temp.values)) + (~np.isnan(mask2compare.values)))
        if somme/norme==1:
            flag = True
            break
        else:
            flag = False
    return flag    


def create_new_mask(ds_mask, id_ref,listMasks):
    '''
        Pour chaque voisin de id_ref, on cree un mask contenant id_ref + le masque voisin. 
        listMask : Fourni la liste (dataset) des masques voisins. 
        id_ref : c'est une zone qui existe deja 
        # on ajoute à ds_mask(id_ref) un mask egal a mask_ref + les masks voisins qui sont dans la liste des masks voisins listMasks
    '''
    mask_ref = ds_mask.sel(id = id_ref).copy(deep=True)

    for  mask2compare in listMasks:
        new_id = str(mask_ref.mask.id.values) +'+'+ str(mask2compare.mask.id.values) 
        mask_ref = ds_mask.sel(id = id_ref).copy(deep=True)
        ds_temp = mask_ref.copy(deep=True)
        ind = np.where((mask_ref.mask == 1 ) + (mask2compare.mask == 1))
        ds_temp.mask.values[ind] = 1
        flag = check_existing_mask_v2(ds_temp.mask, ds_mask) 
        if (not flag) and (new_id not in ds_mask.id.values): 
            # check if mask already exists
            ds_temp = ds_temp.assign_coords(id =[new_id]) 
            ds_mask  = xr.concat([ds_mask,ds_temp],dim = 'id')
        else: 
            pass
    return ds_mask  

def create_nc_mask_NSEO(dep_file,fname_mask_NSEO,plot_dep=False):
    '''
        fonction qui divise le mask (dep_file) en une vingtaine de sous-zones géographiques (nord,sud, nord  + est, etc...)
        et sauvegarde ce nouveau mask en ncdf. 
        in : 
            - dep_file: fichier ncdf contenant le mask du département
            - fname_mask_NSEO: fichier de sortie dans lequel seront stockés les nouveaux masks
        out: le mask avec les sous-zones qui sont idenfiées par id. l'indentifiant géographique (id_geo) est dans une variable (à chaque id un id_geo)
        
    '''
    ds_dep    = read_xarray(dep_file) 
    lat1_3,lat2_3 = ds_dep["latitude"].quantile([1/3,2/3])
    lon1_3,lon2_3 = ds_dep["longitude"].quantile([1/3,2/3]) 

    ds_mask = ds_dep.copy().squeeze("id",drop=True) # création d'un dataset contenant les masks N, S, E, O

    latmin_dict = {'nord':float(lat2_3.values),'sud':ds_mask.latitude.values.min()
                   ,'ouest':ds_mask.latitude.values.min(),'est':ds_mask.latitude.values.min()}

    latmax_dict = {'nord':ds_mask.latitude.values.max(),'sud':float(lat1_3.values)
                   ,'ouest':ds_mask.latitude.values.max(),'est':ds_mask.latitude.values.max()}

    lonmin_dict = {'nord':ds_mask.longitude.values.min(),'sud':ds_mask.longitude.values.min()
                   ,'ouest':ds_mask.longitude.values.min(),'est':float(lon2_3.values)}

    lonmax_dict = {'nord':ds_mask.longitude.values.max(),'sud':ds_mask.longitude.values.max()
                   ,'ouest':float(lon1_3.values),'est':ds_mask.longitude.values.max()}

    # definition des masks centraux
    for id_geo in ['nord','sud','est','ouest']:
        ds_mask[id_geo] = ds_mask.mask * 0
        ind    = np.where((ds_mask.latitude>=latmin_dict[id_geo]) & (ds_mask.latitude<=latmax_dict[id_geo])
                 & (ds_mask.longitude >= lonmin_dict[id_geo]) & (ds_mask.longitude<=lonmax_dict[id_geo]))
        ds_mask[id_geo].values[ind] = 1
        ds_mask[id_geo].values[np.isnan(ds_dep.squeeze("id").mask.values)] = np.nan

    # definition des masks croises
    dict_id_geo_id = {}
    i=0
    for var1 in ['est','ouest']:
        for var2 in ['nord','sud']: 
            id_geo = var2 + '-'+var1
            ds_mask[id_geo] = ds_mask[var1]* ds_mask[var2] # egal a 1 quand les deux valent 1, sinon 0 
            dict_id_geo_id[id_geo]  = str(i)
            i+=1
    
    # definition des milieux (nord-centre, sud-centre) et (est-centre, ouest-centre) 
    id_geo_extremitees={
        'nord-centre' : ['nord-est','nord-ouest'],
        'sud-centre' : ['sud-est','sud-ouest'],
        'est-centre' : ['nord-est','sud-est'],
        'ouest-centre':['nord-ouest','sud-ouest']
    }

    for id_geo in id_geo_extremitees.keys():
        id_ref = id_geo.split('-')[0]
        ds_mask[id_geo] = ds_mask[id_ref] - ds_mask[id_geo_extremitees[id_geo][0]] - ds_mask[id_geo_extremitees[id_geo][1]] 
        dict_id_geo_id[id_geo]  = str(i)

        i+=1
    # import sys;sys.exit()    
    # definition du centre 
    id_geo = 'centre'
    ds_mask[id_geo] = ds_mask.mask.copy()
    ds_mask[id_geo].values[(ds_mask.nord ==1 ) + (ds_mask.sud ==1 ) 
                            + (ds_mask.est ==1 ) + (ds_mask.ouest ==1 )] = 0
    dict_id_geo_id[id_geo]  = str(i)

    # les id des 9 masques centraux
    lst_ini_id_geo = [key for key in dict_id_geo_id if len(key.split('+'))==1 and key not in ['nord','est','sud','ouest']]
    dict_id_geo_id["departement"] = '+'.join([dict_id_geo_id[key] for key in dict_id_geo_id if len(key.split('+'))==1 and key not in ['nord','est','sud','ouest']])

    # on met à jour les id de nord,est,ouest,sud 
    dict_id_geo_id['nord']  = '+'.join([dict_id_geo_id['nord-est'],dict_id_geo_id['nord-centre'], dict_id_geo_id['nord-ouest']])
    dict_id_geo_id['sud']   = '+'.join([dict_id_geo_id['sud-est'],dict_id_geo_id['sud-centre'], dict_id_geo_id['sud-ouest']])
    dict_id_geo_id['est']   = '+'.join([dict_id_geo_id['nord-est'], dict_id_geo_id['est-centre'], dict_id_geo_id['sud-est']])
    dict_id_geo_id['ouest'] = '+'.join([dict_id_geo_id['nord-ouest'], dict_id_geo_id['ouest-centre'], dict_id_geo_id['sud-ouest']])

    # Nord + Est et Nord + ouest (idem pour sud)
    for var1 in ['nord','sud']:
        for var2 in ['est','ouest']: 
            id_geo = var1 + '+'+var2
            ds_mask[id_geo] = ds_mask[var1].copy()
            ds_mask[id_geo].values[ds_mask[var2].values==1] = 1
            dict_id_geo_id[id_geo] = '+'.join([dict_id_geo_id[var1],dict_id_geo_id[var2]])

    # centre + nord (resp + sud, + est, + ouest)
    for var in ['nord','sud','est','ouest']:
        id_geo = 'centre+'+var
        ds_mask[id_geo] = ds_mask['centre'].copy()
        ds_mask[id_geo].values[ds_mask[var].values==1] = 1
        dict_id_geo_id[id_geo] = '+'.join([dict_id_geo_id['centre'],dict_id_geo_id[var]])

    # tout le mask sauf certaines zones ('tout sauf tata')
    for var in ['nord','sud','est','ouest']:
        id_geo = 'tout-'+var
        ds_mask[id_geo] = ds_mask.mask.copy() - ds_mask[var].values
        dict_id_geo_id[id_geo] = '+'.join([dict_id_geo_id[key] for key in lst_ini_id_geo if var not in key])

    # save 
    ds_out = xr.Dataset()

    for i,keys in enumerate(ds_mask.data_vars):
        if keys =='mask':
            ds_temp = ds_mask[keys].expand_dims("id").assign_coords(id=[dict_id_geo_id['departement']]).rename("mask")
        else:
            ds_temp = ds_mask[keys].expand_dims("id").assign_coords(id=[dict_id_geo_id[keys]]).rename("mask")
        ds_out = xr.merge([ds_out,ds_temp])

    # on rajoute une variable contenant les id géographiques (id_geo)
    dict_id_id_geo = dict(zip(dict_id_geo_id.values(),dict_id_geo_id.keys())) # les values deviennent les keys.
    list_id_geo = [dict_id_id_geo[id] for id in ds_out.id.values] 
    ds_int = xr.Dataset({'id_geo':('id',list_id_geo),'id':ds_out.id.values})
    ds_out = ds_out.merge(ds_int)
    ds_out.to_netcdf(fname_mask_NSEO)
    
    if plot_dep:
        import matplotlib.pyplot as plt
        fig,axes = plt.subplots(nrows=7,ncols =4,figsize=(10,25))
        ax = axes.flat
        for imask_id,id in enumerate(ds_out.id.values): 
            ds_out.mask.sel(id=id).plot.imshow(ax=ax[imask_id])
            ax[imask_id].set_title(id+'\n'+ds_out.id_geo.sel(id=id).values.tolist())
        fig.tight_layout()
        
    return ds_out

def create_nc_mask_NSEO_old(dep_file,fname_mask_NSEO,plot_dep=False):
    '''
        fonction qui divise le mask (dep_file) en une vingtaine de sous-zones géographiques (nord,sud, nord  + est, etc...)
        et sauvegarde ce nouveau mask en ncdf. 
        in : 
            - dep_file: fichier ncdf contenant le mask du département
            - fname_mask_NSEO: fichier de sortie dans lequel seront stockés les nouveaux masks
        out: le mask avec les sous-zones 
        
        !!! fonction à rendre plus claire !!! 
    '''
    ds_dep    = read_xarray(dep_file) 

    lat1_3,lat2_3 = ds_dep["latitude"].quantile([1/3,2/3])
    lon1_3,lon2_3 = ds_dep["longitude"].quantile([1/3,2/3]) 

    ds_mask = ds_dep.copy().squeeze("id") # création d'un dataset contenant les masks N, S, E, O
    latmin_dict = {'nord':float(lat2_3.values),'sud':ds_mask.latitude.values.min()
                   ,'ouest':ds_mask.latitude.values.min(),'est':ds_mask.latitude.values.min()}

    latmax_dict = {'nord':ds_mask.latitude.values.max(),'sud':float(lat1_3.values)
                   ,'ouest':ds_mask.latitude.values.max(),'est':ds_mask.latitude.values.max()}

    lonmin_dict = {'nord':ds_mask.longitude.values.min(),'sud':ds_mask.longitude.values.min()
                   ,'ouest':ds_mask.longitude.values.min(),'est':float(lon2_3.values)}

    lonmax_dict = {'nord':ds_mask.longitude.values.max(),'sud':ds_mask.longitude.values.max()
                   ,'ouest':float(lon1_3.values),'est':ds_mask.longitude.values.max()}

    # definition des masks centraux
    for imask_id,mask_id in enumerate(['nord','sud','est','ouest']):
        ds_mask[mask_id] = ds_mask.mask * 0
        ind    = np.where((ds_mask.latitude>=latmin_dict[mask_id]) & (ds_mask.latitude<=latmax_dict[mask_id])
                 & (ds_mask.longitude >= lonmin_dict[mask_id]) & (ds_mask.longitude<=lonmax_dict[mask_id]))
        ds_mask[mask_id].values[ind] = 1
        ds_mask[mask_id].values[np.isnan(ds_dep.squeeze("id").mask.values)] = np.nan

    # definition des masks croises
    for var1 in ['est','ouest']:
        for var2 in ['nord','sud']: 
            mask_id = var2 + '-'+var1
            ds_mask[mask_id] = ds_mask[var1]* ds_mask[var2] # egal a 1 quand les deux valent 1, sinon 0

    # definition du centre 
    mask_id = 'centre'
    ds_mask[mask_id] = ds_mask.mask.copy()
    ds_mask[mask_id].values[(ds_mask.nord ==1 ) + (ds_mask.sud ==1 ) 
                            + (ds_mask.est ==1 ) + (ds_mask.ouest ==1 )] = 0
    # Nord + Est et Nord + ouest (idem pour sud)
    for var1 in ['nord','sud']:
        for var2 in ['est','ouest']: 
            mask_id = var1 + '+'+var2
            ds_mask[mask_id] = ds_mask[var1].copy()
            ds_mask[mask_id].values[ds_mask[var2].values==1] = 1
    # centre + nord (resp + sud, + est, + ouest)
    for var in ['nord','sud','est','ouest']:
        mask_id = 'centre+'+var
        ds_mask[mask_id] = ds_mask['centre'].copy()
        ds_mask[mask_id].values[ds_mask[var].values==1] = 1

    # tout le mask sauf certaines zones ('tout sauf tata')
    for var in ['nord','sud','est','ouest']:
        mask_id = 'tout-'+var
        ds_mask[mask_id] = ds_mask.mask.copy() - ds_mask[var].values

    if plot_dep:
        import matplotlib.pyplot as plt
        fig,axes = plt.subplots(nrows=5,ncols =4,figsize=(15,10))
        ax = axes.flat
        for imask_id,mask_id in enumerate(['nord','sud','est','ouest'                                      
                                           ,'nord-est','sud-est','nord-ouest','sud-ouest'
                                            ,'nord+est','sud+est','nord+ouest','sud+ouest'
                                           ,'centre+est','centre+nord','centre+ouest','centre+sud'
                                           ,'tout-est','tout-nord','tout-ouest','tout-sud'
                                          ]): 
            ds_mask[mask_id].plot.imshow(ax=ax[imask_id])
            ax[imask_id].set_title(mask_id)
        fig.tight_layout()

    # save 
    ds_out = xr.Dataset()
    for i,keys in enumerate(ds_mask.data_vars):
        ds_temp = ds_mask[keys].expand_dims("id").assign_coords(id=[keys]).rename("mask")
        ds_out = xr.merge([ds_out,ds_temp])
    ds_out.id.values[ds_out.id.values=='mask'] = 'departement'
    ds_out.to_netcdf(fname_mask_NSEO)
    return ds_out 




def create_combination_subzones(dir_mask,dep_id,lst_subzones,fname_out,degre5=False):
    '''
    calcul et creation d'une multitude de combinaison de zones sympos. 
    in:
        - dir_mask: répertoire de là où sont stockés les fichiers des zones sympos
        - dep_id: numéro du département (38 dans le cas de l'Isère)
        - lst_subzones: liste de subzones de zones sympos dans le département 
        - fname_out: fichier où sont stockés tous les différents masks
        - degre5: si on veut des masks à 5 zones aussi 
    '''
    
    ds_mask = xr.Dataset()
    '''
       1 - Mask du département: contient la somme des zones sympos
    '''
    for id in lst_subzones:
        file_2 = dir_mask+id+'.nc' #.format(dep_id,n)   
        ds_2   = read_xarray(file_2)
        ds_2   = ds_2.reset_index("id",drop=True)# pour pouvoir les ajouter 
        ds_mask = xr.merge([ds_mask,ds_2],join='outer')
    ds_mask = ds_mask.assign_coords(id = ['departement'])
    ds_mask.mask.attrs["name"] = 'combinaisons des zones sympos'

    '''
       2 - Mask de chaque zone sur le grand domaine 'departement' 
    '''
    for id in lst_subzones:
        file_2 = dir_mask+ id + '.nc'  
        ds_2   = read_xarray(file_2)
        new_id = ds_2.id.values[0]
        if new_id in ds_mask.id.values: 
            continue
        ds_3 = ds_2 *ds_mask.sel(id="departement") 
        ds_3 = ds_3.assign_coords(id = [new_id]) 
        ds_mask  = xr.concat([ds_mask,ds_3],dim = 'id')
        del(ds_3,ds_2)
        
    '''
       3 - Mask des somme des zones sympos voisines: return des mask du type 'zone1+zone3'
    '''
    lst_id_before3 = ds_mask.id.values
    for id_ref in lst_subzones:
        mask_ref = ds_mask.sel(id = id_ref).copy(deep=True)
        listMasks = [ds_mask.sel(id = id) for id in lst_subzones]
        list_neighbours = find_neighbours(mask_ref,listMasks)
    #     on crée les nouveaux mask qui englobent mask_ref + voisin
        listMasks = [ds_mask.sel(id = id) for id in list_neighbours]  
        mask_ref = ds_mask.sel(id = id_ref).copy(deep=True)
        ds_mask = create_new_mask(ds_mask, id_ref,listMasks)

    '''
       4 - somme entre chaque groupement de zones sympos: 
       return des masks du type '(zone1 + zone3) + (zone4 + zone5)' ou '(zone1 + zone3) + (zone4 )'
    '''
    lst_int4 = np.copy(ds_mask.id.values)
    lst_new_id4 = [key for key in lst_int4 if key not in lst_id_before3]

    for id_ref in lst_int4: 
        mask_ref = ds_mask.sel(id = id_ref).copy(deep=True) 
        listMasks = [ds_mask.sel(id = id) for id in lst_int4]
        list_neighbours = find_neighbours(mask_ref,listMasks)
        if len(list_neighbours) == 0: 
            continue
        listMasks = [ds_mask.sel(id = id) for id in list_neighbours]  
        mask_ref  = ds_mask.sel(id = id_ref).copy(deep=True)
        ds_mask   = create_new_mask(ds_mask, id_ref,listMasks)
  
    '''
        à voir si on veut continuer sur cette boucle ou pas
    '''
    if degre5:
        lst_int5 = np.copy(ds_mask.id.values)
        lst_new_id5 = [key for key in lst_int5 if key not in lst_int4]
        for id_ref in lst_new_id5:  
            mask_ref = ds_mask.sel(id = id_ref).copy(deep=True) 
            listMasks = [ds_mask.sel(id = id) for id in lst_int5]
            list_neighbours = find_neighbours(mask_ref,listMasks)
            if len(list_neighbours) == 0: 
                continue
            listMasks = [ds_mask.sel(id = id) for id in list_neighbours]  
            mask_ref  = ds_mask.sel(id = id_ref).copy(deep=True)
            ds_mask   = create_new_mask(ds_mask, id_ref,listMasks)

#     pour avoir des 0 en dehors de la sous-zone sur le departement 
    for iid,id_ref in enumerate(ds_mask.id.values): 
        ds_mask.mask[iid,:,:] = ds_mask.sel(id=id_ref).mask.where((ds_mask.sel(id=id_ref).mask.values==1) + (np.isnan(ds_mask.sel(id='departement').mask.values)),0)

    ds_mask.to_netcdf(fname_out)
    return ds_mask


'''
    Fonctions pour zoner un departement 
'''
def get_optimal_subzone_v2(ds_WME, groupe_mask_select,cible):
    """
        ds_WME  = xarray contenant les champs WME
        cible = valeur du temps sensible cible (par exemple code WME)
        groupe_mask_select = ensemble de masks qui vont être comparés à l'objet météo
        ds_mask = La liste de masques
    """
    score_precision = np.zeros(len(groupe_mask_select.mask))    
    score_hss       = np.zeros(len(groupe_mask_select.mask)) 

    for imask,ds_mask_sub in enumerate(groupe_mask_select.mask):    
        # check if latitudes are aranged in the the same way
        lat1 = ds_mask_sub.latitude.values
        lat2 = ds_WME.latitude.values
        if (np.sum(lat1==lat2) == lat1.size ): 
            # same order 
            y_true = ds_WME.wme_arr.copy()
        elif (np.sum(lat1[::-1]==lat2)== lat1.size):
            # reverse order
            y_true = ds_WME.wme_arr[::-1,:].copy()
        else: 
            print("pb sur lon/lat")
            break
        y_pred = ds_mask_sub.copy() 
        # binarise
        y_true = y_true.where(~((y_true.values!=cible) & (~np.isnan(y_true.values))),0)#ds_dep.wme_arr.copy()
        y_true = y_true.where(~(y_true.values == cible), 1)
        y_true_score = y_true.values[~np.isnan(y_true.values)]
        y_pred_score = y_pred.values[~np.isnan(y_pred.values)]
    #     print(y_true_score,y_pred_score )
        # metriques : 
        score_precision[imask] = precision(y_true_score,y_pred_score)
        score_hss[imask]       = hss(y_true_score,y_pred_score)

    ind_nan = np.where((~np.isnan(score_hss))*(score_hss>0))

    # car si hss <0, alors le hasard fait mieux les choses
    if np.size(ind_nan[0])== 0 :
        # signifie qu'il y a aucune zone qui représente bien la cible
        print('pas de zones homogène pour {}'.format(cible))
        zones_optimales_f,hss_f,precision_f = [],[],[] 
    elif np.size(ind_nan[0])== 1 : 
        # une seule zone possible
        zones_optimales_f = [groupe_mask_select.id.values[ind_nan][0]]
        hss_f             = [score_hss[ind_nan][0]]
        precision_f       = [score_precision[ind_nan][0]]

    else: 

        # selection de la zone qui maximise le hss
        indice = np.argmax(score_hss[ind_nan]) 
        zones_optimales_f = [groupe_mask_select.id.values[ind_nan][indice]]
        hss_f             = [score_hss[ind_nan][indice]]
        precision_f       = [score_precision[ind_nan][indice]] 
        mask_ref          =  groupe_mask_select.sel(id=zones_optimales_f[0]).mask
        # on cherche les zones non-incluses dans cette zone pour aller chercher le deuxième meilleur hss
        lst_mask_not_included, lst_mask_included = get_not_included_masks(mask_ref, groupe_mask_select.id.values[ind_nan],
                                                    groupe_mask_select,flag_strictly_included=False)
        print(zones_optimales_f[0],lst_mask_not_included)
        if(len(lst_mask_not_included)>0):
            score_hss2 = [score_hss[ind_nan][groupe_mask_select.id.values[ind_nan] == mask_id] for mask_id in lst_mask_not_included]
            score_precision2 = [score_precision[ind_nan][groupe_mask_select.id.values[ind_nan] == mask_id] for mask_id in lst_mask_not_included]
            list_mask2 = [groupe_mask_select.id.values[ind_nan][groupe_mask_select.id.values[ind_nan] == mask_id] for mask_id in lst_mask_not_included]
            indice2 = np.argmax(score_hss2)    
            if score_precision2[indice2]>0.2 and \
                np.abs(score_hss[ind_nan][indice] - score_hss2[indice2]) / score_hss[ind_nan][indice] <0.2:
                zones_optimales_f.append(list_mask2[indice2].tolist()[0]) #groupe_mask_select.id.values[ind_nan][indice2])
                hss_f.append(score_hss2[indice2])
                precision_f.append(score_precision2[indice2] )
    return zones_optimales_f,hss_f,precision_f



def get_WME_legend(file_CodesWWMF, ds):
    '''return: legend and WME code which are predicted in ds
    '''
    df             = pandas.read_csv(file_CodesWWMF,usecols = (0,1,6,7),sep=',')
    Code_WME       = df['Code WME'].to_numpy()
    Code_WWMF      = df['Code WWMF'].to_numpy()
    legende_WWMF   = df['Legende WWMF'].to_numpy()
    legende_WME    = df['Legende WME'].to_numpy()

    cible_list  = np.unique(ds.wme_arr.values[~np.isnan(ds.wme_arr.values)])# on parcourt les temps sensibles disponibles sur la zone
    legend_list = [np.unique(legende_WME[Code_WME == WME])[0] for WME in cible_list] 
    return cible_list,legend_list

def group_masks_size(listMasks,ds_mask):
    '''
        on regroupe les différents masks selon leur taille en trois groupes. 
        groupe 1: 0 à taille1
        groupe 2: taille1 à taille2
        groupe 3: taille2 à taille du departement
    '''
    taille_masks = ds_mask.mask.sum(["longitude","latitude"]).sel(id=listMasks).values
    taille1,taille2 = np.quantile(taille_masks,[1/3,2/3])

    ind1 = np.where( (taille_masks < taille1) & (taille_masks > 0))
    groupe1 = ds_mask.sel(id=listMasks).isel(id=ind1[0])

    ind2 = np.where((taille_masks >= taille1) & (taille_masks < taille2))
    groupe2 = ds_mask.sel(id=listMasks).isel(id=ind2[0])

    ind3 = np.where((taille_masks >= taille2))
    groupe3 = ds_mask.sel(id=listMasks).isel(id=ind3[0])

    return groupe1,groupe2,groupe3,taille1,taille2 

def select_group_mask(ds_WME,cible,groupe1,groupe2,groupe3,taille1,taille2):
    '''
        selectionne le groupe de mask dont la taille match celle de l'objet météo définit par son code WME 
        
    '''
    taille_objet_binaire = np.sum(ds_WME.wme_arr.values==cible)
    if taille_objet_binaire < taille1 and taille_objet_binaire >0: 
        groupe_mask_select = groupe1

    elif taille_objet_binaire>=taille1 and taille_objet_binaire < taille2: 
        groupe_mask_select = groupe2
    else :
        groupe_mask_select = groupe3
    return groupe_mask_select 

def get_not_included_masks(mask_temp, list_id,ds_mask,flag_strictly_included=True):
    '''
        return: Ensemble des combinaisons de zones qui n'ont pas de bout commun avec celles incluses dans mask_temp. 
        flag_strictly_included = True si on supprime seulement les zones qui sont incluses dans mask_temp 
                               = False si on supprime aussi les zones qui ont une zone sympo incluse dans mask_temp
        check par les noms des id et non pas par les inclusions de 1  
    '''    
    lst_mask_not_included = [] # not included in mask_temp
    lst_mask_strict_included = [] # zones included in mask_temp
    for id in list_id:
        mask2compare = ds_mask.mask.sel(id = id)  
        somme = np.sum((mask_temp.values ==1) & (mask2compare.values==1)) 
        taille2 = np.sum(mask2compare.values==1)
        taille1 = np.sum(mask_temp.values==1)
        if somme == taille2 :
            lst_mask_strict_included.append(id)

    lst_temp = []
    if not flag_strictly_included:
        for zone in list_id:
            for zone_included in lst_mask_strict_included:       
                if zone_included in zone:
                    lst_temp.append(zone)
                else: 
                    pass
        lst_mask_not_included_finale = [element for element in list_id if element not in lst_temp]            
    else: 
        lst_mask_not_included_finale = [element for element in list_id if element not in lst_mask_strict_included]  
    return lst_mask_not_included_finale,  lst_mask_strict_included


def get_optimal_subzone(ds_WME, groupe_mask_select,cible):
    """
        cible = valeur du temps sensible cible 
        groupe_mask_select = ensemble de masks qui vont être comparés à l'objet météo
        ds_WME:xarray contenant les champs WME
        return: zone qui minimise chaque score (hss, pod, far, f1, precision)
    """
    zones_optimales = {}    
    scores_zones_optimales = {}    

    score_precision = np.zeros(len(groupe_mask_select))    
    score_f1        = np.zeros(len(groupe_mask_select)) 
    score_hss       = np.zeros(len(groupe_mask_select)) 
    score_far       = np.zeros(len(groupe_mask_select))
    score_pod       = np.zeros(len(groupe_mask_select)) 
    for imask,ds_mask_sub in enumerate(groupe_mask_select):    
        # check si les latitudes sont selon le même ordre
        lat1 = ds_mask_sub.latitude.values
        lat2 = ds_WME.latitude.values
        if (np.sum(lat1==lat2) == lat1.size ): 
            # same order 
            y_true = ds_WME.wme_arr.copy()
        elif (np.sum(lat1[::-1]==lat2)== lat1.size):
    #         print('reverse order ')
            y_true = ds_WME.wme_arr[::-1,:].copy()
        else: 
            print("pb sur lon/lat")
            break

        y_pred = ds_mask_sub.copy() 
        y_true.values[(y_true.values!=cible) & (~np.isnan(y_true.values))] = 0 
        y_true.values[y_true.values == cible ] = 1 


        y_true_score = y_true.values[~np.isnan(y_true.values)]
        y_pred_score = y_pred.values[~np.isnan(y_pred.values)]
        # metriques : 
        score_precision[imask] = precision(y_true_score,y_pred_score)
#         score_f1[imask]        = f1(y_true_score,y_pred_score)
        score_hss[imask]       = hss(y_true_score,y_pred_score)
        score_far[imask]       = far(y_true_score,y_pred_score)
        score_pod[imask]       = pod(y_true_score,y_pred_score)

    ind_nan = np.where(~np.isnan(score_precision))
    zones_optimales['precision'] = groupe_mask_select.id.values[ind_nan][np.argmax(score_precision[ind_nan])]
    scores_zones_optimales['precision'] = score_precision[ind_nan][np.argmax(score_precision[ind_nan])]

#     ind_nan = np.where(~np.isnan(score_f1))
#     zones_optimales['f1'] = groupe_mask_select.id.values[ind_nan][np.argmax(score_f1[ind_nan])]
#     scores_zones_optimales['f1'] = score_f1[ind_nan][np.argmax(score_f1[ind_nan])]

    ind_nan = np.where((~np.isnan(score_far)) & (score_far>0))
    zones_optimales['far'] = groupe_mask_select.id.values[ind_nan][np.argmin(score_far[ind_nan])]
    scores_zones_optimales['far'] = score_far[ind_nan][np.argmin(score_far[ind_nan])]

    ind_nan = np.where(~np.isnan(score_pod))
    zones_optimales['pod'] = groupe_mask_select.id.values[ind_nan][np.argmax(score_pod[ind_nan])]
    scores_zones_optimales['pod'] = score_pod[ind_nan][np.argmax(score_pod[ind_nan])]

    ind_nan = np.where(~np.isnan(score_hss))
    zones_optimales['hss'] = groupe_mask_select.id.values[ind_nan][np.argmax(score_hss[ind_nan])]
    scores_zones_optimales['hss'] = score_hss[ind_nan][np.argmax(score_hss[ind_nan])]
    return zones_optimales,scores_zones_optimales




