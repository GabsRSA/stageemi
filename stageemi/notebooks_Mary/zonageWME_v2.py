#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import glob
import xarray as xr 
import pandas as pd
import time
import glob
import sys, os
import string

sys.path.insert(0, os.path.abspath('./lib'))

from lib import create_combination_subzones, create_nc_mask_NSEO
from lib import find_neighbours, group_masks_size, select_group_mask, get_WME_legend, get_not_included_masks,get_optimal_subzone_v2

import stageemi
import stageemi.dev.distance_wwmf as distance_wwmf

# On obtient un zonage par departement par echeance.

''' input '''
date = '2020012600' # Date pour laquelle on fait tourner 
# date = '2020030600'
list_method_distance = ['compas']#,'agat','compas_asym','agat_asym'] # pour agreger le temps sensible

mask_sympo = False # Veut-on des combie de zones sympos ? 
mask_geographique = True # Veut-on des combinaisons Est/Ouest/Nord/Sud. A rebrancher. 
# mask_sympo = True # Veut-on des combie de zones sympos ? 
# mask_geographique = False # Veut-on des combinaisons Est/Ouest/Nord/Sud. A rebrancher. 


dir_fig = '../figures/total/' 
nsubzonesMax = 4 # Nombre de sous zones 
plot_results = False
Force = False # Force to recompute staff 
if date == '2020012600':
#     echeance_dict = {
#         '38':[44,12,3,46,43,25,30],
#         '29':[32,39,20,33,13],  
#         '34':[1,5,6,4 ,10, 20,30], 
#         '41':[45,4,44,5,20,30]
#     }
        echeance_dict = {
            '38':[44,43,3,46,30],
            '41':[45,4,44,5,20,30]
    }
elif date == '2020030600':
    echeance_dict = {
        '38':[29,3,1,4,36],
        '41':[18],
        '29':[1,5,3],  
        '34':[31,6,16,29,30], 
    }
    
for dep_id in echeance_dict.keys():
    echeance_list = echeance_dict[dep_id]
    print('dep_id',dep_id)
    ''' lecture fichier arome '''
    fname = "../WWMF/" + date+'0000__PG0PAROME__'+'WWMF'+'__EURW1S100______GRILLE____0_48_1__SOL____GRIB2.nc'
    ds = xr.open_dataset(fname,chunks={"step":1}).isel(step = echeance_list)
    # Arrondi pour éviter les erreurs     
    ds['latitude']  = ds['latitude'].round(5)
    ds['longitude'] = ds['longitude'].round(5)
    if date == '2020030600':
        ds = ds.rename({'paramId_0':'unknown'})

        
    ''' lecture du mask '''
    if mask_sympo and not mask_geographique:         
        fname_out = '../GeoData/zones_sympo_multiples/'+dep_id+'_mask_zones_sympos.nc'
        if not os.path.exists(fname_out): 
            # Creation du fichier (netcdf) de combinaison des zones sympos 
            dir_mask = '/home/mrpa/borderiesm/stageEMI/Codes/StageEMI/Masques_netcdf/ZONE_SYMPO/'
            list_subzones = glob.glob(dir_mask + dep_id +'*.nc')
            n_subzones = len(list_subzones)  # nombre de zones sympos initiales
            lst_subzones = [zone[-7:-3] for zone in list_subzones]
            ds_mask = create_combination_subzones(dir_mask,dep_id,lst_subzones,fname_out,degre5=True) 
            ds_mask = ds_mask.chunk({"id":1}) # Rend le calcul parallele possible 
        else: 
            # Le fichier est disponible 
            ds_mask = xr.open_dataset(fname_out,chunks={"id":1})
        dir_out = '../zonageWME/v7_'+'WME_' # repertoire contenant les fichiers résultats du zonage
        id_dep = 'departement' # identifiant de la zone recouvrant tout le departement
    if mask_geographique and not mask_sympo: 
        if   dep_id == '38': dep = 'FRK24'
        elif dep_id == '41': dep = 'FRB05'
        elif dep_id == "34": dep = 'FRJ13'
        elif dep_id == '29': dep = "FRH02"
        else: 
            print('remplir la bonne valeur pour le dep')
            sys.exit()
        fname_out = '../GeoData/zones_sympo_multiples/'+ dep_id+'_'+dep+'_mask_NSEO.nc'
        if not os.path.exists(fname_out):
            # Creation du fichier (netcdf) s'il n'existe pas 
            dir_mask  = '../GeoData/nc_departement/'
            dep_file  = dir_mask + dep +'.nc' 
            print('on cree',fname_out)
            ds_mask = create_nc_mask_NSEO(dep_file,fname_out,plot_dep=False)
            ds_mask = ds_mask.chunk({"id":1})
        else:
            ds_mask = xr.open_dataset(fname_out,chunks={"id":1})
        dir_out = '../zonageWME/v7_'+'geo_' # repertoire contenant les fichiers résultats du zonage
        id_dep = '0+1+2+3+4+5+6+7+8'# identifiant de la zone recouvrant tout le departement
        
    # Arrondi pour éviter les erreurs         
    ds_mask["latitude"]  = ds_mask["latitude"].round(5)
    ds_mask["longitude"] = ds_mask["longitude"].round(5)
    ds_dep_tot = (ds*ds_mask.mask.sel(id=id_dep))
   
    ''' calcul des temps agrégés '''
    ds_distance_dict = {}
    for name in list_method_distance:
        ds_distance         = distance_wwmf.get_pixel_distance_dept(ds_dep_tot,name) # rajoute les variables wme_arr et w1_arr
        ds_distance_chunk   = ds_distance.chunk({"step":1}) 
        # On recupere ici toute les zones. 
        ds_distance_dict[name] = (ds_distance_chunk * ds_mask.mask).sum(['latitude',"longitude"]).compute()
    print('fin calcul distance')
   
    # On part toujours sur l'utilisation des dénominations COMPAS car elles sont moins nombreuses?  
    var_name = 'wme_arr'
    for icheance,echeance in enumerate(echeance_list): 
        print(echeance)
        fname_out = dir_out+dep_id+'_'+date+'_'+str(echeance)+'.csv'

        if os.path.exists(fname_out) and not Force:
            print(fname_out,'existe')
            continue
        
        tdeb = time.time()
        ''' on restreint la liste des WME pour le zonage '''
        ds_dep = ds_dep_tot.isel(step = icheance).copy()
        # on regroupe 'Très nuageux/Couvert' et 'Nuageux'
        ds_dep = ds_dep.where(~((ds_dep[var_name].values == 2) + (ds_dep[var_name].values == 3) ), 2)
        # on regroupe ensemble neige (10) et neige faible (7)
        ds_dep = ds_dep.where(~((ds_dep[var_name].values == 7) + (ds_dep[var_name].values == 10)), 10)
        # on regroupe ensemble pluie (8) et pluie faible (6)
        ds_dep = ds_dep.where(~((ds_dep[var_name].values == 8) + (ds_dep[var_name].values == 6)),8)
        # on regroupe ensemble qlqs averses (12) et averses (14), et qlqs averses de neige (13)
        ds_dep = ds_dep.where(~((ds_dep[var_name].values == 12) + (ds_dep[var_name].values == 13)
                                  + (ds_dep[var_name].values == 14 )),14)
        # on regroupe ensemble averses Orageuses (16) et Orages  (18)
        ds_dep = ds_dep.where(~((ds_dep[var_name].values == 16) + (ds_dep[var_name].values == 18)),18)

        file_CodesWWMF = '../utils/CodesWWMF.csv'
        cible_list,legend_list = get_WME_legend(file_CodesWWMF, ds_dep) 

        ''' zonage '''
        listCible    = cible_list[::-1] # On considère que l'ordre inverse est l'ordre de criticité maximun.
                                        # A bien définir lors de l'utilisation selon les cas.  

        legend_cible = [] # pour stocker la légende du code WME
        listMasksNew = ds_mask.id.values # on commence avec l'ensemble des masks

        # liste de zones sympos initiales (pour checker à la fin si on a une info sur toutes les zones du département)
        list_zones_sympos_initiales = [zone for zone in ds_mask.id.values if (('+' not in zone) and (zone!='departement'))]
        
        nsubzones    = 0
        zones_cibles = {}
        score_zones_cibles = {}
        if len(listCible) == 0 : # si un département a le même temps sensible partout
            zones_cibles[listCible[0]] = 'departement'
        else: 
            for icible,cible in enumerate(listCible):
                if nsubzones > nsubzonesMax: 
                    print('nombre de sous-zones trop grand')
                    break 
                if nsubzones >1: 
                    # pour éviter que departement ne soit selectionné alors que des sous-zones de departement aient déjà été selectionnées.
                    listMasksNew = [element for element in listMasksNew if element !=id_dep ]

                if len(listMasksNew)>60:
                    #  on regroupe les masks selon leur taille pour aller plus vite 
                    groupe1,groupe2,groupe3,taille1,taille2  = group_masks_size(listMasksNew,ds_mask)
                    # on selectionne le groupement de zones qui match l'objet météo
                    groupe_mask_select = select_group_mask(ds_dep,cible,groupe1,groupe2,groupe3,taille1,taille2)
                else: 
                    # on considère l'ensemble des masks
                    groupe_mask_select = ds_mask.sel(id=listMasksNew) 
                # on selectionne la zone optimale (selon le hss et la précision)
                zones_optimales,score_hss,score_precision=get_optimal_subzone_v2(ds_dep, groupe_mask_select,cible)              
                if len(zones_optimales)!=0:
                    legend_cible.append(legend_list[::-1][icible])
                    score_zones_cibles[cible] = score_hss
                    zones_cibles[cible] = zones_optimales 
                    nsubzones +=1 
                    # sinon pas de zones selectionnées                                            
                    ''' on check que la somme des zones n'est pas déjà égale au departement '''
                    if  (nsubzones== 1) and (len(zones_cibles[cible]) == 1) :
                        ds_temp  = ds_mask.sel(id=zones_cibles[cible][0]).mask.copy()

                    elif (nsubzones== 1) and (len(zones_cibles[cible]) > 1): 
    #                    ds_temp  = ds_mask.sel(id=zones_cibles[cible]).mask.sum("id") >= 1  
                        ds_temp  = ds_mask.sel(id=zones_cibles[cible][0]).mask.copy() 
                        ds_temp.values[(ds_temp.values == 1) + (ds_mask.sel(id=zones_cibles[cible][1]).mask.values ==1) ] = 1
                    else: 
                        for zone in zones_cibles[cible]:                            
                            ds_temp.values[(ds_temp.values == 1) + (ds_mask.sel(id=zone).mask.values ==1) ] = 1

                    somme = np.sum((ds_temp.values == 1)&( ds_mask.sel(id=id_dep).mask.values== 1))
                    tailleDep = np.sum( ds_mask.sel(id=id_dep).mask.values== 1)
                    if somme == tailleDep: 
                        print('on a atteint la taille du departement')
                        break
                    # on récupère les zones non-incluses dans la zone sélectionnée
                    for zone in zones_cibles[cible]:
                        listMasksNew, lst_mask_included = get_not_included_masks(ds_mask.mask.sel(id=zone)
                                                        ,listMasksNew,ds_mask,flag_strictly_included=False)
            # fin boucle sur cible
            ''' on vérifie que toutes les zones du département sont dans les zones selectionnées '''
            list_zones_select = sum([zones_cibles[cible] for cible in zones_cibles.keys()],[]) 
            zones_restantes = []
            for zone_sympo in list_zones_sympos_initiales:
                n = 0
                for zone_select in list_zones_select: 
                    if zone_sympo in zone_select:
                        n+=1
                if n == 0 : 
                    zones_restantes.append(zone_sympo)
        
        '''save results in csv'''
        print('saving results')
        
        d = { 'zone':sum([zones_cibles[cible] for cible in zones_cibles.keys()],[]), 
            'cible_wme':sum([[cible]  if len(zones_cibles[cible])==1 else [cible,cible] for cible in zones_cibles.keys()],[]),
            'hss' : sum([score_zones_cibles[cible] for cible in zones_cibles.keys()],[])}

        if len(zones_restantes)>0:
            d['zone'] += zones_restantes
            d['hss'] += [np.nan for i in range(len(zones_restantes))]
            d['cible_wme'] += [np.nan for i in range(len(zones_restantes))]
        for name in list_method_distance:
            d[name] =  ds_distance_dict[name].wwmf_2[ds_distance_dict[name].argmin("wwmf_2")].sel(id=d['zone']).isel(step=icheance).values
        pd.DataFrame(data=d).to_csv(fname_out)
        print('temps %s \n'%(time.time()-tdeb))


