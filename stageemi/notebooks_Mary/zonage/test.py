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

from lib import read_xarray, find_neighbours, conversion
from lib import hss,precision,far,f1, pod,pofd
from lib import create_combination_subzones, create_nc_mask_NSEO
from lib import group_masks_size, select_group_mask, get_WME_legend, get_not_included_masks
from lib import calculate_distance

def get_optimal_subzone_v2(ds_WME, groupe_mask_select,cible):
    """
        cible = valeur du temps sensible cible 
        groupe_mask_select = ensemble de masks qui vont être comparés à l'objet météo
        ds_WME:xarray contenant les champs WME
    """
    score_precision = np.zeros(len(groupe_mask_select))    
    score_hss       = np.zeros(len(groupe_mask_select)) 
    for imask,ds_mask_sub in enumerate(groupe_mask_select):    
        # check si les latitudes sont selon le même ordre
        lat1 = ds_mask_sub.latitude.values
        lat2 = ds_WME.latitude.values
        if (np.sum(lat1==lat2) == lat1.size ): 
            # same order 
    #         print("same order")
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
        score_hss[imask]       = hss(y_true_score,y_pred_score)
        
    ind_nan = np.where((~np.isnan(score_hss))*(score_hss>0))
    
    if np.size(ind_nan[0])== 0 :
        # signifie qu'il y a aucune zone qui représente bien la cible
        print('pas de zones homogène pour {}'.format(cible))
        zones_optimales_f,hss_f,precision_f = [],[],[] 
    elif np.size(ind_nan[0])== 1 : 
        # une seule zone possible
#         print(ind_nan)
#         print('une seule zone possible pour {}'.format(cible))
        zones_optimales_f = [groupe_mask_select.id.values[ind_nan][0]]
        hss_f             = [score_hss[ind_nan][0]]
        precision_f       = [score_precision[ind_nan][0]]
    else: 
        indice = np.argsort(score_hss[ind_nan])[::-1][:2]
        zones_optimales = groupe_mask_select.id.values[ind_nan][indice].tolist()
#         print('hss',score_hss[ind_nan][indice])
#         print('precision',(score_precision[ind_nan][indice]))
#         print(zones_optimales)
        if score_precision[ind_nan][indice][1]>0.2 and \
            np.abs(score_hss[ind_nan][indice][1] - score_hss[ind_nan][indice][0]) / score_hss[ind_nan][indice][0] <0.2: 
            # si la fraction de l'événement est supérieure à 20% dans la zone, et si les hss des deux meilleures zones 
            # sont similaires
            best_zones = zones_optimales
#             print('deux choix',best_zones)
            # checker de l'inclusion de l'une ou l'autre des zones
            list_neighbours = best_zones[::-1]
            list_ref        = best_zones 
            for iref in range(len(list_ref)):
                mask_ref=ds_mask.sel(id=list_ref[iref])
            #     print(list_ref[iref],list_neighbours[iref])
                lst_mask_not_included, lst_mask_included = get_not_included_masks(mask_ref.mask, [list_neighbours[iref]],ds_mask,flag_strictly_included=True)
                if len(lst_mask_included)>0 :
                    # signifie que un des deux masks est inclu dans l'autre
                    zones_optimales_f = [list_ref[iref]]
                    hss_f             = [score_hss[ind_nan][indice][iref]]
                    precision_f       = [score_precision[ind_nan][indice][iref]]
                    break
                else:
                    zones_optimales_f = best_zones
                    hss_f             = score_hss[ind_nan][indice].tolist()
                    precision_f       = score_precision[ind_nan][indice].tolist()
        else: 
            # tant pis on prend qu'une seule zone
            zones_optimales_f = [groupe_mask_select.id.values[ind_nan][indice][0]]
            hss_f             = [score_hss[ind_nan][indice][0]]
            precision_f       = [score_precision[ind_nan][indice][0]]
    return zones_optimales_f,hss_f,precision_f

# 29 : Finistère (185), 34: Hérault (235 combi), 38: Isère (80 combi), 41: Loi-et-cher (27)
# date   = '2019110400'
# date   = '2019121200'
# # date   = '2019122100'
# dep_id = '38'#'29'#'41' #'38'#


# echeance_dict = {
#     '29':[32,39,20,33,13], 
#     '38':[44,12,3,46,43,25,30], 
#     '34':[1,5,6,4 ,10, 20,30], 
#     '41':[45,4,44,5,20,30]
# }

echeance_dict = { 
    '41':[45,4,44,5,20,30],
    '34':[4 ,10, 20,30]
}

date   = '2020012600'
# echeance = 13
windows = True 
mask_sympo = True
mask_geographique = False

dir_fig = 'C:\\Users\\mary\\Desktop\\stageemi\\figures\\'

for dep_id in echeance_dict.keys():
    echeance_list = echeance_dict[dep_id]
#     print(dep_id,echeance_list)
    for echeance in echeance_list: 
        print(dep_id,str(echeance))
        tdebut = time.time()


        ''' 1 - lecture des masks '''
        if mask_sympo and not mask_geographique: 
            t1 = time.time()
            if windows : 
        #         print('windows')
                fname_out =  Path(r'C:\\Users\\mary\\Desktop\\stageemi\\zones_sympo_multiples\\'+ dep_id+'_mask_zones_sympos.nc')
            else :         
                fname_out = '/home/mrpa/borderiesm/stageEMI/Codes/StageEMI/Masques_netcdf/ZONE_SYMPO_MULTIPLE/'+ dep_id+'_mask_zones_sympos.nc'
            if not os.path.exists(fname_out): 
                dir_mask = '/home/mrpa/borderiesm/stageEMI/Codes/StageEMI/Masques_netcdf/ZONE_SYMPO/'
                list_subzones = glob.glob(dir_mask + dep_id +'*.nc')
                n_subzones = len(list_subzones)  # nombre de zones sympos initiales
                lst_subzones = [zone[-7:-3] for zone in list_subzones]
                ds_mask = create_combination_subzones(dir_mask,dep_id,lst_subzones,fname_out,degre5=True) 
            else: 
                print(fname_out)
                ds_mask = read_xarray(fname_out)
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

        print(ds_mask.id.values.size)

        ''' 2- lecture champs arome'''

        if windows: 
            dir_in = 'C:\\Users\\mary\\Desktop\\stageemi\\WWMF\\' 
            fname = Path(dir_in +  date+'0000__PG0PAROME__'+'WWMF'+'__EURW1S100______GRILLE____0_48_1__SOL____GRIB2.nc')
        else:    
            dir_in = '/scratch/labia/lepapeb/StageEMI/WWMF/'
            fname  = dir_in + date+'0000__PG0PAROME__'+'WWMF'+'__EURW1S100______GRILLE____0_48_1__SOL____GRIB2.nc'

        ds     = read_xarray(fname)
        ds.latitude.values = ds.latitude.values[::-1]
        if mask_sympo and not mask_geographique: 
            ds2plot = ds.isel(step=echeance) * ds_mask.mask.sel(id='departement') 
        if mask_geographique and not mask_sympo: 
            ds2plot = ds.isel(step=echeance) * ds_mask.mask.sel(id="mask") 

        for name in ['compas','compas_asym']:
            ds_WME = conversion(ds2plot,name) 

        # ds_WME_agregation = ds_WME.copy()
        file_CodesWWMF = '../../utils/CodesWWMF.csv'
        cible_list,legend_list = get_WME_legend(file_CodesWWMF, ds_WME)

        for var_name in ['wme_arr','wme_asym_arr']:
            # on regroupe 'Très nuageux/Couvert' et 'Nuageux'
            ds_WME[var_name].values[(ds_WME[var_name].values == 2) 
                                  + ((ds_WME[var_name].values == 3) )] = 2

            # on regroupe ensemble neige (10) et neige faible (7)
            ds_WME[var_name].values[(ds_WME[var_name].values == 7) 
                                  + ((ds_WME[var_name].values == 10) )] = 10

            # on regroupe ensemble pluie (8) et pluie faible (6)
            ds_WME[var_name].values[(ds_WME[var_name].values == 6) 
                                  + ((ds_WME[var_name].values == 8) )] = 8

            # on regroupe ensemble qlqs averses (12) et averses (14), et qlqs averses de neige (13)
            ds_WME[var_name].values[(ds_WME[var_name].values == 12) + (ds_WME[var_name].values == 13)
                                  + ((ds_WME[var_name].values == 14) )] = 14

            # on regroupe ensemble averses Orageuses (16) et Orages  (18)
            ds_WME[var_name].values[(ds_WME[var_name].values == 16) + ((ds_WME[var_name].values == 18) )] = 18

        del(ds,ds2plot)
        # ds_WME.wme_arr.plot.imshow()

        # on regarde les codes 
        cible_list,legend_list = get_WME_legend(file_CodesWWMF, ds_WME)
        print(cible_list,legend_list)

        '''
            3- on selectionne les zones pour chaque temps sensible
        '''

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
                zones_optimales,score_hss,score_precision=get_optimal_subzone_v2(ds_WME, groupe_mask_select,cible)
                print('zone optimales',zones_optimales,score_hss,score_precision)

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

        '''
            4- on agrège sur les zones selectionnees
        '''
        list_zones_select = sum([zones_cibles[cible] for cible in zones_cibles.keys()],[])
        # sys.exit()
        temps_agrege = {}
        for name in ['compas','compas_asym']:
    #         print(name)
            temps_agrege[name] = {}
        #     ds_w1 = conversion(ds_WME,name)

            for zone_select in list_zones_select:
        #         ds_zone = ds_WME_agregation * ds_mask.mask.sel(id=zone_select)
                ds_zone = ds_WME * ds_mask.mask.sel(id=zone_select)

                if name == 'compas':
                    var_name = "wme_arr"
                if name == 'agat':
                    var_name="w1_arr" 
                if name == "compas_asym":
                    var_name="wme_asym_arr"
                if name == 'agat_asym':
                    var_name="w1_asym_arr"

                ds_zone[var_name].values[ds_zone[var_name].values == 0] = np.nan        
                ds = calculate_distance(ds_zone,name)
                temps_agrege[name][zone_select] = ds.attrs[name]
    #             print(zone_select,cible,ds.attrs[name]) 
    #             print(temps_agrege[name][zone_select])
        #         print(ds.attrs)
            print('')

        '''
            plot des zones finales
        '''
        print('plot')
        matplotlib.rcParams['legend.handlelength'] = 0
        matplotlib.rcParams['legend.numpoints'] = 1

        X,Y = np.meshgrid( ds_mask.longitude.values,ds_mask.latitude.values)
        listMasks = [ds_mask.sel(id=id_ref) for id_ref in list_zones_sympos_initiales]

        legende = string.ascii_lowercase
        patches = []
        fig,ax = plt.subplots(nrows=1,ncols =1)
        ds_WME.wme_arr.plot.imshow(ax = ax,cmap=matplotlib.cm.tab20)
        ax.set_title(date+' + {} h'.format(echeance))
        for icible,cible in enumerate(zones_cibles): #['3801+3802']:#, '3806']:#zones_cibles:
            for zone_select in  zones_cibles[cible] :
                mask_ref = ds_mask.sel(id = zone_select)

                list_neighbours = find_neighbours(mask_ref,listMasks)
                lst_mask_not_included, lst_mask_included = get_not_included_masks(mask_ref.mask, list_neighbours,ds_mask,flag_strictly_included=True)
                for neighbours in lst_mask_not_included:
                    ind = np.where((mask_ref.mask.values == 1) & (ds_mask.sel(id=neighbours).mask.values == 1))
                    ax.scatter(X[ind],Y[ind],color='k',s=6)

                # ajout de la legende
                indice_mask_ref = np.where(mask_ref.mask.values == 1)
                ax.text(X[indice_mask_ref].mean(),Y[indice_mask_ref].mean(),s=legende[icible],color='k',fontsize=15)
                label = zone_select +': '+ legend_list[::-1][icible] + ' ({})'.format(cible)\
                        + ' Compas:{},'.format(temps_agrege['compas'][zone_select])\
                        + ' Compas Asym:{}'.format(temps_agrege['compas_asym'][zone_select])
            #        + ' Agat:{}'.format(temps_agat[zone_select])
        #     patches.append(mpatches.Patch(label = legende[icible],marker='${}$'.format(legende[icible])))
            patches.append(mlines.Line2D([],[],label = label,marker='${}$'.format(legende[icible]),color='black'))


        fig.legend(handles=patches,bbox_to_anchor=(1.05, 0.5), loc='center left',labelspacing =2,fontsize = 16)
        fig.tight_layout()
        fname_fig = dir_fig + 'zonage\\compas_compas_asym\\v2_zonage_'+dep_id+date+'_'+str(echeance)+'.png'
    #     print(fname_fig)
        fig.savefig(fname_fig,dpi=400,bbox_inches='tight',format='png')
        plt.clf()
        plt.close('all')


        '''
            5- même plot mais avec zones sympos initiales
        '''

        temps_agrege = {}
        for name in ['compas','compas_asym']:
            print(name)
            temps_agrege[name] = {}
        #     ds_w1 = conversion(ds_WME,name)

            for zone_select in list_zones_sympos_initiales:
        #         ds_zone = ds_WME_agregation * ds_mask.mask.sel(id=zone_select)
                ds_zone = ds_WME * ds_mask.mask.sel(id=zone_select)

                if name == 'compas':
                    var_name = "wme_arr"
                if name == 'agat':
                    var_name="w1_arr" 
                if name == "compas_asym":
                    var_name="wme_asym_arr"
                if name == 'agat_asym':
                    var_name="w1_asym_arr"

                ds_zone[var_name].values[ds_zone[var_name].values == 0] = np.nan        
                ds = calculate_distance(ds_zone,name)
                temps_agrege[name][zone_select] = ds.attrs[name]
    #             print(zone_select,cible,ds.attrs[name]) 
    #             print(temps_agrege[name][zone_select])
        #         print(ds.attrs)
    #         print('')

        legende = string.ascii_lowercase
        patches = []
        fig,ax = plt.subplots(nrows=1,ncols =1)
        ds_WME.wme_arr.plot.imshow(ax = ax,cmap=matplotlib.cm.tab20)
        ax.set_title(date+' + {} h'.format(echeance))
        # print(zones_cibles)

        for icible,zone_select in enumerate(list_zones_sympos_initiales): #['3801+3802']:#, '3806']:#zones_cibles:
            mask_ref = ds_mask.sel(id = zone_select)

            list_neighbours = find_neighbours(mask_ref,listMasks)
            lst_mask_not_included, lst_mask_included = get_not_included_masks(mask_ref.mask,list_neighbours,ds_mask,flag_strictly_included=True)

            for neighbours in lst_mask_not_included:
                ind = np.where((mask_ref.mask.values == 1) & (ds_mask.sel(id=neighbours).mask.values == 1))
                ax.scatter(X[ind],Y[ind],color='k',s=6)

            # ajout de la legende
            indice_mask_ref = np.where(mask_ref.mask.values == 1)
            ax.text(X[indice_mask_ref].mean(),Y[indice_mask_ref].mean(),s=legende[icible],color='k',fontsize=15)
            label = zone_select +': ' \
                        + ' Compas:{},'.format(temps_agrege['compas'][zone_select])\
                        + ' Compas Asym:{}'.format(temps_agrege['compas_asym'][zone_select])
        #             + ' Agat:{}'.format(temps_agat[zone_select])
        #     patches.append(mpatches.Patch(label = legende[icible],marker='${}$'.format(legende[icible])))
            patches.append(mlines.Line2D([],[],label = label,marker='${}$'.format(legende[icible]),color='black'))
        fig.legend(handles=patches,bbox_to_anchor=(1.05, 0.5), loc='center left',labelspacing =2,fontsize = 16,ncol=2)
        fig.tight_layout()
        fig.savefig(dir_fig + 'zonage\\compas_compas_asym\\v2_zonage_ref_'+dep_id+date+'_'+str(echeance)+'.png',dpi=400,bbox_inches='tight')
        plt.clf()
        plt.close('all')
        tfin = time.time()
        print('temps',tfin - tdebut)
