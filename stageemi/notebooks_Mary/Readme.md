Seul `lib.py` et `test_multi_dep_echance.py` sont à utiliser. 
Le notebook `zonage_echeance_fixe_v3.ipynb` est similiaire au fichier précédent. 

modifications du 27/04/2020:
1. découpage gégraphique: modif de la fonction create_nc_mask_NSEO. 
    - les identifiants ne sont plus géographiques (ex nord) mais des chiffres. Les ids des 9 zones primaires (N-E, S-E, centre, etc...) vont de 0 à 8. Pour les autres zones, l'id est la "somme" des ids primaires inclus dans la zone (ie, ids primaires concaténés et séparés par un "+"). Par exemple, l'id de la zone englobant tout le département correspond à la "somme" des ids primaires, à savoir: "0+1+2+3+4+5+6+7+8". 
    - Pour s'y repérer, la variable id_geo a été rajoutée pour faire correspondre à chaque id son identifiant géographique (par exemple, "nord",'nord-est','centre+nord',etc...). 
    - les masques géographiques sont ici: GeoData/zones_sympo_multiples/*_mask_NSEO.nc
    
2. sélection de la zone optimale pour un temps WME: fonction get_optimal_subzone_v2
    - une entrée en moins (avant ds_mask était redondant avec groupe_mask_select)
    - Possibilité de sélectionner deux zones non-incluses l'une dans l'autre pour un temps sensible donnée si la précision est supérieure à 0.2 et si la différence relative des hss des deux zones est inférieure à 0.2 (je n'ai pas fait de tests sur les seuils, je les ai choisis arbitrairement) 

3. le fichier main qui est désormais zonageWME_v2.py et qui est utilisable pour les découpages géo ou sympo. 