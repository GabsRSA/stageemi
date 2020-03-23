import json
from ipyleaflet import Map, GeoJSON

"""
Pour la visu sur carte de frontieres. 
"""
class Borders(GeoJSON):
    """
    Permet le chargement et la creation d'un layer a partir d'un fichier geojson avec ipyleaflet
    Le fond est quasi transparent
    """
    def __init__(self,fname="",**kwargs):
        """
        Init a borders (geoJSON) to display with ipyleaflet
        """
        with open(fname) as fp:
            geojson_data = json.load(fp)
        
        if kwargs.get("color",False): 
            self.change_color(geojson_data,kwargs.get("color"))
        for feature in geojson_data["features"]:
            self.set_fill_opacity(feature, 0)
        super().__init__(data=geojson_data,name=kwargs.get("layer_name","Boundaries"))

    def change_color(self,geojson_data,color):
        """
        Change the color of the border 
        """
        if isinstance(color,bool):
            color = "#000"
        try: 
            for elt in geojson_data["features"]: 
                elt["properties"]["style"] =  {"color": color}
        except Exception:
            print("Do not change color")
            pass
        
    @staticmethod
    def set_fill_opacity(feature, opacity):

        if "style" in feature["properties"]:
            feature["properties"]["style"]["fillOpacity"] = 0.1
        else:
            feature["properties"]["style"] = {"fillOpacity": 0.1}