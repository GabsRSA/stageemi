#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 24 17:49:16 2020

@author: borderiesm
"""

import numpy as np
import glob
import xarray as xr 
import matplotlib.pyplot as plt 
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import matplotlib
# import pandas as pd
import time
import glob
import sys, os
import string
from pathlib import Path # pour windows 
sys.path.insert(0, os.path.abspath('./lib'))

from lib import find_neighbours,get_optimal_subzone_v2
from lib import hss,precision 
from lib import create_combination_subzones, create_nc_mask_NSEO
from lib import group_masks_size, get_optimal_subzone, select_group_mask, get_WME_legend, get_not_included_masks

import stageemi
import stageemi.dev.distance_wwmf as distance_wwmf

'''
input 
'''
date   = '2020012600'
list_name = ['compas','agat','compas_asym','agat_asym'] # pour agreger le temps sensible

mask_sympo = True
mask_geographique = False
dir_fig = 'C:\\Users\\mary\\Desktop\\stageemi\\figures\\zonage\\compas_compas_agat\\total\\'

# dep_id = '41'#'29'#'41' #'38'#
# echeance = 4

echeance_dict = {
    '29':[32,39,20,33,13], 
    '38':[44,12,3,46,43,25,30], 
    '34':[1,5,6,4 ,10, 20,30], 
    '41':[45,4,44,5,20,30]
}

for dep_id in echeance_dict.keys():
    echeance_list = echeance_dict[dep_id]
    print(dep_id)
    ''' lecture du mask '''
    if mask_sympo and not mask_geographique: 
        t1 = time.time()
        fname_out = '../GeoData/zones_sympo_multiples/'+dep_id+'_mask_zones_sympos.nc'
        if not os.path.exists(fname_out): 
            dir_mask = '/home/mrpa/borderiesm/stageEMI/Codes/StageEMI/Masques_netcdf/ZONE_SYMPO/'
            list_subzones = glob.glob(dir_mask + dep_id +'*.nc')
            n_subzones = len(list_subzones)  # nombre de zones sympos initiales
            lst_subzones = [zone[-7:-3] for zone in list_subzones]
            ds_mask = create_combination_subzones(dir_mask,dep_id,lst_subzones,fname_out,degre5=True) 
        else: 
            ds_mask = xr.open_dataset(fname_out,chunks={"id":1})
            ds_mask["latitude"]  = ds_mask["latitude"].round(5)
            ds_mask["longitude"] = ds_mask["longitude"].round(5)
        print(time.time() - t1)

    if mask_geographique and not mask_sympo: 
        dir_mask  = '/home/mrpa/borderiesm/stageEMI/Codes/stageemi/stageemi/GeoData/nc_departement/'
        if   dep_id == '38': dep = 'FRK24'
        elif dep_id == '41': dep = 'FRB05'
        elif dep_id == "34": dep = 'FRJ13'
        elif dep_id == '29': dep = "FRH02"
        else: 
            print('remplir la bonne valeur pour le dep')
            sys.exit()

        dep_file  = dir_mask + dep +'.nc' 
        fname_out = '/home/mrpa/borderiesm/stageEMI/Codes/StageEMI/Masques_netcdf/ZONE_SYMPO_MULTIPLE/'+ dep_id+'_'+dep+'_mask_NSEO.nc'

        if not os.path.exists(fname_out):
            ds_mask = create_nc_mask_NSEO(dep_file,fname_out)
        else:
            print('fichier existe pas')
    #         ds_mask = read_xarray(fname_out) 
    # lecture arome
    fname = "../WWMF/" + date+'0000__PG0PAROME__'+'WWMF'+'__EURW1S100______GRILLE____0_48_1__SOL____GRIB2.nc'

    ds = xr.open_dataset(fname,chunks={"step":1})
    ds['latitude']  = ds['latitude'].round(5)
    ds['longitude'] = ds['longitude'].round(5)
    # ds.latitude.values = ds.latitude.values[::-1]

    if mask_sympo and not mask_geographique: 
        ds_dep_tot = (ds*ds_mask.mask.sel(id="departement").drop("id"))
    if mask_geographique and not mask_sympo: 
    #     ds2plot = ds.isel(step=echeance) * ds_mask.mask.sel(id="mask") 
        ds_dep_tot = (ds*ds_mask.mask.sel(id="mask").drop("id"))
    
    ''' calcul des temps agrégés '''
    ds_distance_dict = {}
    for name in list_name:
        ds_distance         = distance_wwmf.get_pixel_distance_dept(ds_dep_tot,name)
        ds_distance_chunk   = ds_distance.chunk({"step":1}) 
        ds_distance_dict[name] = (ds_distance_chunk * ds_mask.mask).sum(['latitude',"longitude"]).compute()

    ''' restreint la liste des WME pour le zonage '''
    var_name = 'wme_arr'
    for echeance in echeance_list: 
        print(echeance)
        tdeb = time.time()
        ds_dep = ds_dep_tot.isel(step = echeance).copy()
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

        # ds_dep.wme_arr.plot()

        file_CodesWWMF = '../utils/CodesWWMF.csv'
        cible_list,legend_list = get_WME_legend(file_CodesWWMF, ds_dep)
        print(cible_list,legend_list)


        ''' zonage '''
        nsubzonesMax = 7
        listCible    = cible_list[::-1]
        # listCible = [4]
        legend_cible = []
        listMasksNew = ds_mask.id.values # on commence avec l'ensemble des masks

        # liste de zones sympos initiales (pour checker à la fin si oui ou non on a une info sur toutes les zones)
        list_zones_sympos_initiales = [zone for zone in ds_mask.id.values if len(zone) == 4]

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
                    listMasksNew = [element for element in listMasksNew if element !='departement']

                if len(listMasksNew)>60:
                    #  on regroupe les masks selon leur taille
                    groupe1,groupe2,groupe3,taille1,taille2  = group_masks_size(listMasksNew,ds_mask)
                    # on selectionne le groupement de zones qui match l'objet météo
                    groupe_mask_select = select_group_mask(ds_WME,cible,groupe1,groupe2,groupe3,taille1,taille2)
                else: 
                    # on considère l'ensemble des masks
                    groupe_mask_select = ds_mask.mask.sel(id=listMasksNew)
                # on selectionne la zone optimale (selon le hss et la précision)
                zones_optimales,score_hss,score_precision=get_optimal_subzone_v2(ds_dep, groupe_mask_select,cible)
                print('zone optimales',zones_optimales,score_hss,score_precision)
        #         sys.exit()
                if len(zones_optimales)==0:
                    continue
                else: 
                    legend_cible.append(legend_list[::-1][icible])
                    score_zones_cibles[cible] = score_hss
                    zones_cibles[cible] = zones_optimales #zones_optimales[score_zonage]
                    nsubzones +=1  
        #         print(cible,zones_cibles[cible],len(zones_cibles[cible]),score_zones_cibles[cible])            

                '''
                    on check que la somme des zones n'est pas deja egale au departement
                '''
                if  (nsubzones== 1) and (len(zones_cibles[cible]) == 1) :
                    ds_temp  = ds_mask.sel(id=zones_cibles[cible][0]).mask.copy()

                elif (nsubzones== 1) and (len(zones_cibles[cible]) > 1): 
                    ds_temp  = ds_mask.sel(id=zones_cibles[cible][0]).mask.copy() 
                    ds_temp.values[(ds_temp.values == 1) + (ds_mask.sel(id=zones_cibles[cible][1]).mask.values ==1) ] = 1
                else: 
                    for zone in zones_cibles[cible]:
                        print(zone)
                        ds_temp.values[(ds_temp.values == 1) + (ds_mask.sel(id=zone).mask.values ==1) ] = 1

                somme = np.sum((ds_temp.values == 1)&( ds_mask.sel(id='departement').mask.values== 1))
                tailleDep = np.sum( ds_mask.sel(id='departement').mask.values== 1)
                if somme == tailleDep: 
                    print('on a atteint la taille du departement')
                    break
                for zone in zones_cibles[cible]:
                    listMasksNew, lst_mask_included = get_not_included_masks(ds_mask.mask.sel(id=zone)
                                                    ,listMasksNew,ds_mask,flag_strictly_included=False)
        #             print("on enleve les zones",listMasksNew)
            '''
                on vérifie que toutes les zones du département sont dans les zones selectionnées
            '''
            list_zones_select = sum([zones_cibles[cible] for cible in zones_cibles.keys()],[]) # [zones_cibles[cible] for cible in zones_cibles.keys()]
            zones_restantes = []
            for zone_sympo in list_zones_sympos_initiales:
                n = 0
                for zone_select in list_zones_select: 
                    if zone_sympo in zone_select:
                        n+=1
                if n == 0 : 
                    zones_restantes.append(zone_sympo)
            if len(zones_restantes) > 0: 
                print('zones restantes:',zones_restantes)
            else:
                print('toutes les zones sont bien décrites')

        print(zones_cibles)    

        ''' plot '''
        matplotlib.rcParams['legend.handlelength'] = 0
        matplotlib.rcParams['legend.numpoints'] = 1

        X,Y = np.meshgrid( ds_mask.longitude.values,ds_mask.latitude.values)
        listMasks = [ds_mask.sel(id=id_ref) for id_ref in list_zones_sympos_initiales]

        legende = string.ascii_lowercase
        patches = []
        fig,ax = plt.subplots(nrows=1,ncols =1)
        # ds_dep.wme_arr.plot.imshow(ax = ax,cmap=matplotlib.cm.tab20)
        ds_dep_tot.isel(step = echeance).wme_arr.plot.imshow(ax = ax,cmap=matplotlib.cm.tab20)
        ax.set_title(date+' + {} h'.format(echeance))
        # print(zones_cibles)
        for icible,cible in enumerate(zones_cibles): #['3801+3802']:#, '3806']:#zones_cibles:
        #     zone_select = zones_cibles[cible] 
            for zone_select in  zones_cibles[cible] :
                mask_ref = ds_mask.sel(id = zone_select)

                list_neighbours = find_neighbours(mask_ref,listMasks)
                lst_mask_not_included, lst_mask_included = get_not_included_masks(mask_ref.mask, list_neighbours,ds_mask,flag_strictly_included=True)
                for neighbours in lst_mask_not_included:
                    ind = np.where((mask_ref.mask.values == 1) & (ds_mask.sel(id=neighbours).mask.values == 1))
                    ax.scatter(X[ind],Y[ind],color='k',s=6)
                # 
                # ajout de la legende
                indice_mask_ref = np.where(mask_ref.mask.values == 1)
                ax.text(X[indice_mask_ref].mean(),Y[indice_mask_ref].mean(),s=legende[icible],color='k',fontsize=15)
                label = zone_select +': '+ legend_list[::-1][icible] + ' ({})'.format(cible)
                # ajout de l'agregation: 
                for name in list_name: 
                    val_agrege = ds_distance_dict[name].wwmf_2[ds_distance_dict[name].argmin("wwmf_2")].sel(id=zone_select).isel(step=echeance).values
                    label += ' {}:{}'.format(name,val_agrege)
            patches.append(mlines.Line2D([],[],label = label,marker='${}$'.format(legende[icible]),color='black'))


        fig.legend(handles=patches,bbox_to_anchor=(1.05, 0.5), loc='center left',labelspacing =2,fontsize = 16)
        fig.tight_layout()
        fname_fig = dir_fig + 'v3_zonage_'+dep_id+date+'_'+str(echeance)+'.png'
        print(fname_fig)
        fig.savefig(fname_fig,dpi=400,bbox_inches='tight',format='png')
        plt.clf()
        plt.close('all')
        print('temps',time.time()-tdeb)

