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
