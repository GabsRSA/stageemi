This file is meant 

Les dossiers de scores : 
* scores 
* scores_advanced
* scores_advanced_labia
* visu : obsolete
* work_zone_Mary : update_json_zone_sympo : Crée un json qui contient l'ensemble des zones sympos par département (et les combinaisons des zones sympos). 


* Explore_zones_sympo : Notebook d'exploration de zones assez simple (pour visu de zones). 

Generation de matrices :
Todo : Migrer les codes de générations dans un fichiers `.py` dans les utils.  
* `Generation_AGAT_matrix_of_distances` : 
        utilise le fichier de sévérité pour calculer la matrice. Calcul la distance dans un espace normé.
* `make_asymetric_compas_matrix`, `make_asymetric_agat_matrix` : Generation de la matrice en ajoutant une pénalité (sous la diagonale)

`Find_critical_weather_situations.ipynb` : permet de déterminer quels échéances présentes des codes WWMF un peu élévés. Permet d'explorer rapidement avec des histogrammes. 
`
`Demo_agregation_advanced.ipynb` : Pas utile pour le zonage avec critère d'homogénéité. Permet d'obtenir l'aggrégation sur les départements et zones_sympo pour (AGAT,COMPAS,AGAT_ASYMETRIQUE, COMPAS_ASYMETRIQUE). Intérêt dans le futur ? Peut-être obsolète car moins puissant sur le calcul des distances que le nouveau code. Boucle sur tous les fichiers sur tous les deux mois. On obtient les mêmes résultats avec `distance_wwmf.py` ce qui a permis de valider la seconde méthode. 

`Process_scores_confusion_matrices` : Permettait de montrer les scores. 
    Permettrait de calculer  des matrices de confusions entre COMPAS, COMPAS_ASYMETRIQUE et AGAT/AGAT_ASYMETRIQUE. Permettrait de vérifier l'effet qu'on souhaite donner à ces matrices (à savoir faire plus souvent remonter les évènements un peu plus sévères).

