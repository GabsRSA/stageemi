import stageemi.dev.decorator_map as dm
import stageemi.dev.geojson_geoview as geo_gv 
from stageemi.dev.distance_wwmf import conversion 
import xarray as xr 
import ipywidgets as widg 
import ipyleaflet as ipyl
import datetime as dt
import os 
from ipywidgets import Text, HTML
from ipyleaflet import WidgetControl
import json 
import branca.colormap as cm
from holoviews.operation import histogram
import holoviews as hv
import pandas as pd
import numpy as np

import shapely.geometry as sh  
import json 
import geojson

import time 
def elapsed_since(start):
    #return time.strftime("%H:%M:%S", time.gmtime(time.time() - start))
    elapsed = time.time() - start
    if elapsed < 1:
        return str(round(elapsed*1000,2)) + "ms"
    if elapsed < 60:
        return str(round(elapsed, 2)) + "s"
    if elapsed < 3600:
        return str(round(elapsed/60, 2)) + "min"
    else:
        return str(round(elapsed / 3600, 2)) + "hrs"

class interactive_map(widg.HBox):
    
    def __init__(self,distance_choice="agat"):
        start = time.time()
        self.m = ipyl.Map(center=(45,0),zoom=7,layout={"height":"500px"})
        # Date 
        date_picker = widg.DatePicker(value=dt.datetime(2020,1,26))
        self._date = date_picker.value 
        date_picker.observe(self.change_date,"value")
        self.step = 0
        self.distance_choice=distance_choice
        variable_picker = widg.Dropdown(value="WWMF",options=["WWMF","WME","W1"])
        variable_picker.observe(self.variable_change,"value")
        dept_picker = widg.Dropdown(value="41",options={"Finistère":"29","Isère":"38","Hérault":"34","Loire-et-cher":"41"})
        dept_picker.observe(self.change_dept,"value")
        self.dept = dept_picker.value 
        self._variable = variable_picker.value
        # Open dataset and mask 
        self.open_file()
        # Add other widgets 
        self.legend = widg.Image(layout=widg.Layout(height="430px"))
        self.html1 = HTML('''
                    <h4>Type de temps</h4>
                        Hover over a pixel
                        ''')
        self.html1.layout.margin = '0px 20px 20px 20px'
        # Add controls 
        control1 = WidgetControl(widget=self.html1, position='bottomright')
        self.m.add_control(control1)
        self.m.add_control(ipyl.LayersControl())
    
        slider = widg.IntSlider(min=0,max=len(self.da.step)-1,step=1,value=0,description="step")
        slider.observe(self.change_step,'value')
        self.m.add_control(ipyl.WidgetControl(widget=widg.VBox([date_picker,slider,variable_picker,dept_picker]),position="topright"))
        self.m.add_control(ipyl.FullScreenControl())

        start2 = time.time()
        self.render()
        super().__init__([self.m,self.legend])

        
    @property 
    def variable(self):
        return self._variable
   
    @variable.setter 
    def variable(self,variable):
        self._variable = variable
        self.open_file()
        self.render()
        
    @property 
    def date(self):
        return self._date
    
    @date.setter
    def date(self,date):
        self._date = date
        self.open_file()
        self.render()
    
    @property 
    def mask(self):
        return self._mask 
    
    @mask.setter
    def mask(self,mask):
        self._mask = mask 
        if hasattr(self,"da"):
            self.mask_da()
            
    def variable_change(self,change):
        self.variable = change["new"]
        
    def mask_da(self):
        self.da_masked = (self.da *self.mask).squeeze("id")
  
    #def aggregate(self):
    #    """
    #    Fonction qui ne sert a rien ici .... 
    #    Elle aurait du etre remplacee par les fonctions d'aggregation specifique developpee durant le stage.
    #    A voir comment les integrer. 
    #    """
    #    self.da_aggregated = (self.da_masked * self.da_zone).mean(["latitude","longitude"])
   
        
    def get_mask(self):
        if self.dept == "29":
            da_mask = xr.open_dataarray("../GeoData/nc_departement/FRH02.nc")
        elif self.dept == "38":
            da_mask = xr.open_dataarray("../GeoData/nc_departement/FRK24.nc")
        elif self.dept == "34":
            da_mask = xr.open_dataarray("../GeoData/nc_departement/FRJ13.nc")
        elif self.dept == "41":
            da_mask = xr.open_dataarray("../GeoData/nc_departement/FRB05.nc")
        else: 
            raise(ValueError("Departement not known. Please add it"))
        da_mask["latitude"] = da_mask.latitude.round(5)
        da_mask["longitude"] = da_mask.longitude.round(5)
        self.mask = da_mask
        
    @property 
    def dept(self):
        return self._dept
    
    @dept.setter
    def dept(self,dept):
        self._dept = dept 
        self.get_mask()
        self.get_Mary_zone()
        self.get_sympo_zone2()
        if hasattr(self,"html1"):
            self.html1.values = '''<h4>Type de temps</h4>
                        Hover over a pixel
                        '''
        if hasattr(self,"da"):
            self.render()
        

    def reading_Mary_results(self):
        # On lit les resultat des zonages de Mary
        fileresult='../zonageWME/v2_'+self.dept+'_'+self.date.strftime("%Y%m%d%H")+'_'+str(self.step)+'.csv'
        # Voir si pas posible de faire autrement ? 
        # On lit le fichier de resultat s'il existe 
        # On recupere les zones concernees a la step qui nous interesse (via les clefs contenues dans le fichier)
        # Si pas de fichier, on prend le departement dans son ensemble
        if os.path.exists(fileresult):
            dfres=pd.read_csv(fileresult,sep=',',index_col=0)
            zs_l=dfres["zone"].to_list()
            self.dfres = dfres
        else: 
            zs_l=["departement"]
            if hasattr(self,"dfres"):
                del(self.dfres)  # we suppress the attribute in order to ignore the condition in update_chor_html          
        return zs_l 

    def reading_homogeneous_results(self):

        fileresult = '../zonage_homogeneous_criterion/'+self.dept+'_'+self.date.strftime("%Y%m%d%H%M")+'_'+self.distance_choice+'.csv'
        try:
            # for some reason, zones from this columns are considered float otherwise (41_202001260000_compas.csv)
            dfres2=pd.read_csv(fileresult,sep=',',index_col=0, na_filter=True, dtype={'zone_winning_comp':str})
            dfres2=dfres2.fillna(9999)            
            # ajout fonction
            self.dfres2 = dfres2
            zone_id = self.zones_homogenes() # Permet de retourner les zones homogenes
        except IOError:
            zone_id = ["departement"]
            if hasattr(self,"dfres2"):
                del(self.dfres2)  # we suppress the attribute in order to ignore the condition in update_chor_html  
        return zone_id 

    @staticmethod 
    def extract_geozone(poly_geojson,zone_list):
        new_poly  ={}
        new_poly["type"] = poly_geojson["type"]
        new_poly["features"] = []
        for x in poly_geojson["features"]:
            if x["properties"]["id"] in zone_list:
                x["id"] = x["properties"]["id"]
                new_poly["features"].append(x)
        return new_poly 

    def get_Mary_zone(self):
        """
        Retourne les zones du departement concernes
        """
        zs_l = self.reading_Mary_results()   
        zsympo = "../GeoData/ZonesSympo/zones_sympo_combined_"+self.dept+".json"
        with open(zsympo) as geojson1:
            poly_geojson = json.load(geojson1)

        self.region_geo = self.extract_geozone(poly_geojson,zs_l)
        if hasattr(self,"dfres"):
            self.mary_zone = self.dfres.set_index("zone")[self.distance_choice]
  
        # On lit les resultat des zonages de Mary
        
        # On charge la liste de zone correspondant 
        #da_mask = xr.open_dataarray(fname_mask)
        #self.da_zone = da_mask.sel(id=zs_l).load()   
        #self.da_zone["latitude"] = self.da_zone.latitude.round(5)
        #self.da_zone["longitude"] = self.da_zone.longitude.round(5)
        # read the zone sympos file for the corresponding department
        #fname_mask = '../GeoData/zones_sympo_multiples/'+self.dept+'_mask_zones_sympos.nc'
        # On ouvre le fichier de zones sympos

    def get_sympo_zone2(self):
        """
        Retourne les zones du departement concernes
        """
          
        # read the zone sympos file for the corresponding department
        fname_mask = '../GeoData/zones_sympo_multiples/'+self.dept+'_mask_zones_sympos.nc'
        da_mask = xr.open_dataarray(fname_mask)
        
        # On lit le fichier de zone homogene 
        self.zone_homo_id = self.reading_homogeneous_results()

        # As we are able to create zone which are not part of the "zones_sympo_combined_dpt.json", we need to create them (to plot them. 
        # when the combined zone is not part of the "zones_sympo_combined_dpt.json" we need to create it
        with open("../GeoData/ZonesSympo/zones_sympo_4326.json","r") as fp: 
            poly_geo = json.load(fp)
        # list of the zones sympo id in the json file (zones_sympo_4326.json)
        feature=[] # Will contain the list of new area 
        zs_json=[poly_geo["features"][i]["properties"]["id"] for i in range(len(poly_geo["features"]))]

        for val in self.zone_homo_id:
            if not (val in list(da_mask.id.values)):
                #print('qd est ce qu on est dans ce cas ci?',val,self.step)
                val_l=val.split('+')
                for j,zs in enumerate(val_l):
                    if j==0: # init shape
                        id_json=zs_json.index(zs)
                        shape = sh.asShape(poly_geo['features'][id_json]['geometry'])
                    else:
                        id_json=zs_json.index(zs)
                        shape=shape.union(sh.asShape(poly_geo['features'][id_json]['geometry']))
                feature.append(geojson.Feature(geometry=shape,properties = {'id':val}))
        data = geojson.FeatureCollection(feature)
        zsympo = "../GeoData/ZonesSympo/zones_sympo_combined_"+self.dept+".json"
        with open(zsympo) as geojson1:
            poly_geojson = json.load(geojson1)
        
        if not len(feature)==0:
            for new_feat in data["features"]:
                poly_geojson["features"].append(new_feat)
                
        self.region_geo2 = self.extract_geozone(poly_geojson,self.zone_homo_id)

        # for the sake of not bugging the function ipyl.Choropleth
        self.homo_zone = dict(zip(self.zone_homo_id,np.asarray(self.temps_l).astype(float)))

            
            
    def zones_homogenes(self):
        """
        retourne les zones et les temps sensibles resultant de la division sur critere d homogeneite
        """
        zone_l=[]
        temps_l=[]
        
        i=self.step
        
        if np.all(self.dfres2.iloc[i][['zone_winning_2','zone_winning_comp']]!=9999):
            zone_l.append(self.dfres2.iloc[i][['zone_winning_2','zone_winning_comp']].tolist())
            temps_l.append(self.dfres2.iloc[i][['zw2_'+self.distance_choice,'zwc_'+self.distance_choice]].tolist())
        else:
            zone_l.append(self.dfres2.iloc[i][['zone_winning']].tolist())
            temps_l.append(self.dfres2.iloc[i][['zw_'+self.distance_choice]].tolist())
        
        if np.all(self.dfres2.iloc[i][['zone_comp_winning','zone_comp_comp']]!=9999):
            zone_l.append(self.dfres2.iloc[i][['zone_comp_winning','zone_comp_comp']].tolist())
            temps_l.append(self.dfres2.iloc[i][['zcw_'+self.distance_choice,'zc2_'+self.distance_choice]].tolist())
        else: 
            if np.all(self.dfres2.iloc[i][['zone_winning']]!="departement"): # if zone_winning == "departement" alors on ne s'interesse pas à la zone complémentaire
                zone_l.append(self.dfres2.iloc[i][['zone_comp']].tolist())
                temps_l.append(self.dfres2.iloc[i][['zc_'+self.distance_choice]].tolist())
            
        zone_id =[item for sublist in zone_l for item in sublist] # flatten the list (not a list of lists)
        self.temps_l=[int(item) for sublist in temps_l for item in sublist] # idem

        return zone_id 
    
 
    def change_dept(self,change):
        self.dept = change["new"]

    def change_date(self,change):
        self.date = change["new"]
        
    def open_file(self):
        if self.variable in ["WWMF","WME","W1"]:
            fname = "../WWMF/%s__PG0PAROME__WWMF__EURW1S100______GRILLE____0_48_1__SOL____GRIB2.nc"%self.date.strftime("%Y%m%d%H%M%S")
            self.vmin = 2
            self.vmax = 99
            self.levels = False
        elif self.variable == "PRECIP":
            fname = "/scratch/labia/lepapeb/models_data/PRECIP/%s__PAROME__PRECIP__EURW1S100______GRILLE____1_48_1__SOL____.nc"%self.date.strftime("%Y%m%d%H%M%S")
            self.vmin = 0
            self.vmax = 20
            self.levels = [0,1,2,5,7,10,15,20] 
            self.colors = ['#5ebaff', '#00faf4', '#ffffcc', '#ffe775', '#ffc140', '#ff8f20', '#ff6060']
        elif self.variable == "T":
            fname = "/scratch/labia/lepapeb/models_data/T/%s__PG1PAROME__T__EURW1S100______GRILLE____0_48_1__HAUTEUR__2__.nc"%self.date.strftime("%Y%m%d%H%M%S")
            self.vmin = 250
            self.vmax = 320
            self.levels = False
            
        else: 
            raise(ValueError("Unknown variable"))

        
        self.da = xr.open_dataarray(fname)
        self.da['latitude'] = self.da.latitude.round(5)
        self.da['longitude'] = self.da.longitude.round(5)
           
        
        if hasattr(self,"mask"):
            self.mask_da()
                
    @dm.gogeojson_wwmf
    def get_step(self,variable = "wwmf"):
        if self.variable in  ["WME","W1"]:

            ds_temp = self.da_masked.isel(step=self.step)
            ds_temp["latitude"] = ds_temp.latitude.round(5)
            ds_temp["longitude"] = ds_temp.longitude.round(5)
            ds_temp.name = "unknown"
            if self.variable == "WME":
                ds_out = conversion(ds_temp.to_dataset(),"compas")
                da = ds_out["wme_arr"]
            elif self.variable == "W1":
                ds_out = conversion(ds_temp.to_dataset(),"agat")
                da = ds_out["w1_arr"]
            else:
                raise(ValueError("Conversion not implemented")) 
        else:   
            da = self.da_masked.isel(step=self.step)
        return da
    
        
    def update_html(self,feature, **kwargs):
        self.html1.value = '''
        <h4> Type de temps </h4>
        <h4><b>{}</b></h4>
        '''.format(feature['properties']['value'])
        
    def update_chor_html(self,feature,**kwargs):  
        if hasattr(self, "dfres"):
            filecodeswwmf='../utils/CodesWWMF.csv'
            df=pd.read_csv(filecodeswwmf,sep=',')
            id_i = feature["properties"]["id"]
            df_feature = self.dfres.loc[self.dfres['zone']==id_i]
            
            w = int(df_feature['compas'])
            x = int(df_feature['agat'])
            y = int(df_feature['compas_asym'])
            z = int(df_feature['agat_asym'])                
            
            wstr=np.unique(df.loc[df['Code WME']==w]['Legende WME'])[0]
            xstr=np.unique(df.loc[df['Code W1']==x]['Legende W1'])[0]
            ystr=np.unique(df.loc[df['Code WME']==y]['Legende WME'])[0]
            zstr=np.unique(df.loc[df['Code W1']==z]['Legende W1'])[0]
            if len(df_feature["cible_wme"].dropna()) > 0: 
                r = int(df_feature['cible_wme'])
                rstr=np.unique(df.loc[df['Code WME']==r]['Legende WME'])[0]
                self.html1.value = '''
                <h4> Valeur sur {} </h4>
                <h4><b>cible wme: {}</b></h4>
                <h4><b>compas: {}</b></h4>
                <h4><b>agat: {}</b></h4>
                <h4><b>compas asym: {}</b></h4>
                <h4><b>agat asym: {}</b></h4>            
                '''.format(feature["properties"]["id"],rstr,wstr,xstr,ystr,zstr)
            else : 
                self.html1.value = '''
                <h4> Valeur sur {} </h4>
                <br>
                <h4><b>compas: {}</b></h4>
                <h4><b>agat: {}</b></h4>
                <h4><b>compas asym: {}</b></h4>
                <h4><b>agat asym: {}</b></h4>            
                '''.format(feature["properties"]["id"],wstr,xstr,ystr,zstr)
        else: 
            self.html1.value = '''
            <h4> Valeur sur {} </h4>
            <h4><b>Not calculated</b></h4>
            '''.format(feature["properties"]["id"])
        
    def update_chor_html2(self,feature,**kwargs):
        if hasattr(self, "dfres2"):
            try:
                id_i = feature["properties"]["id"]
                ind = self.zone_homo_id.index(id_i)
                x=self.temps_l[ind]
                filecodeswwmf='../utils/CodesWWMF.csv'
                df=pd.read_csv(filecodeswwmf,sep=',')
                if "compas" in self.distance_choice:
                    xstr=np.unique(df.loc[df['Code WME']==x]['Legende WME'])[0]
                elif "agat" in self.distance_choice:
                    xstr=np.unique(df.loc[df['Code W1']==x]['Legende W1'])[0]
                else:
                    print("warning, none of the 2 options (compas or agat) were found, please check again!")
            # avec le code
                self.html1.value = '''
                <h4> Valeur sur {} </h4>
                <h4><b>{}: {} {}</b></h4>           
                '''.format(feature["properties"]["id"],self.distance_choice,xstr,x)                                                        
            except Exception as e: 
                self.html1.value =  '''
                <h4> For this area {} we get this {}. <br> Please wait a few second and try again</h4>
                <h4><b>Not calculated</b></h4>
                '''.format(feature["properties"]["id"],repr(e))
        else: 
            self.html1.value = '''
            <h4> Valeur sur {} </h4>
            <h4><b>Not calculated</b></h4>
            '''.format(feature["properties"]["id"])
            
    def change_step(self,change):
        self.step = change["new"]
        self.get_Mary_zone()
        self.get_sympo_zone2()
        self.render()

    def update_HSS_area(self):
        # On change les donnees de Mary 
        if hasattr(self,"dfres"):
            # On choisit (par defaut) le code WME a afficher pour Mary 
            if self.distance_choice in ["compas","compas_asym"]:
                variable = "WME"
            else: 
                variable = "W1"
            (code,hexc,_) = geo_gv.get_cmap_info(variable)
            cmap = cm.StepColormap(hexc.values,index=np.asarray(code).astype(float),vmin=code[0],vmax=code[-1]+1)
            chor_layer = ipyl.Choropleth(
                                    geo_data=self.region_geo,
                                    choro_data=self.mary_zone.to_dict(),
                                    name="zonage sur temps sensible (WME)",
                                    value_min = float(code[0]),
                                    value_max = float(code[-1]+1),
                                    colormap = cmap, 
                                    border_color='blue',
                                    style={'fillOpacity': 0.8, 'dashArray': '5, 5'},
                                    hover_style={"opacity":1,"color":"black","weight":4})      
            chor_layer.value_min = float(code[0])
            chor_layer.value_max = code[-1]*1.0
            if hasattr(self,"chor_layer"):
                if self.chor_layer in self.m.layers:
                #print("on passe la")
                    self.m.substitute_layer(self.chor_layer,chor_layer)
                else: 
                    #print("ici")
                    self.m.add_layer(chor_layer)
            else:
                #print('ou la')
                self.m.add_layer(chor_layer)
            self.chor_layer = chor_layer
            self.chor_layer.on_hover(self.update_chor_html)
        else: 
            if hasattr(self,"chor_layer") and self.chor_layer in self.m.layers:
                self.m.remove_layer(self.chor_layer)

    def update_homo_area(self):
        # On change les donnes de Gab 
        if self.distance_choice in ["compas","compas_asym"]:
            variable = "WME"
        else: 
            variable = "W1"
        (code,hexc,_) = geo_gv.get_cmap_info(variable)
        cmap = cm.StepColormap(hexc.values,index=np.asarray(code).astype(float),vmin=code[0],vmax=code[-1]+1)
        chor_layer2 = ipyl.Choropleth(geo_data=self.region_geo2,
                                    choro_data=self.homo_zone,
                                    name="zonage sur homogeneous temps sensible criterion ("+self.distance_choice+")",
                                    value_min = float(code[0]),
                                    value_max = float(code[-1]+1),
                                    colormap = cmap, 
                                    border_color="red",
                                    style={'fillOpacity': 0.8, 'dashArray': '5, 5',"opacity":0.5},
                                    hover_style={"opacity":1,"color":"black","weight":4})

        chor_layer2.value_min = float(code[0])
        chor_layer2.value_max = code[-1]*1.0
        if hasattr(self,"chor_layer2"):
            if self.chor_layer2 in self.m.layers:
                #print("et par la")
                self.m.substitute_layer(self.chor_layer2,chor_layer2)
            else: 
                #print('et ici')
                self.m.add_layer(chor_layer2)
        else:
            #print('et ou la')
            self.m.add_layer(chor_layer2)
        self.chor_layer2 = chor_layer2
        self.chor_layer2.on_hover(self.update_chor_html2)
        

    def render(self):
        # On change AROME 
        geo_file,legend_file = self.get_step(variable= self.variable)
        geojson_layer = ipyl.GeoJSON(data=geo_file,hover_style={"opacity":1},name="AROME")
        if hasattr(self,"geojson_layer"):
            if self.geojson_layer in self.m.layers:
                self.m.substitute_layer(self.geojson_layer,geojson_layer)
            else:
                self.m.add_layer(geojson_layer)
        else:
            self.m.add_layer(geojson_layer)
        self.geojson_layer = geojson_layer
        self.geojson_layer.on_hover(self.update_html)
        legend_file.seek(0)
        self.legend.value =legend_file.read()
        self.update_HSS_area()
        self.update_homo_area()
        
        
class contour_interactive(interactive_map):
    
    def get_step(self,variable = "wwmf"):
        import stageemi.dev.geojson_geoview as geo_gv 
        
        from io import BytesIO
        
        #On converti si besoin 
        if variable in  ["WME","W1"]:
            ds_temp = self.da_masked.isel(step=self.step)
            ds_temp["latitude"] = ds_temp.latitude.round(5)
            ds_temp["longitude"] = ds_temp.longitude.round(5)
            ds_temp.name = "unknown"
            if self.variable == "WME":
                ds_out = conversion(ds_temp.to_dataset(),"compas")
                da = ds_out["wme_arr"]
            elif self.variable == "W1":
                ds_out = conversion(ds_temp.to_dataset(),"agat")
                da = ds_out["w1_arr"]
            else:
                raise(ValueError("Conversion not implemented")) 
        else:   
            da = self.da_masked.isel(step=self.step)
            
        if variable in ["WWMF","W1","WME"]: 
            legend_file = BytesIO()
            geo_contour = geo_gv.get_WeatherType_contour(da,
                                                         variable=variable,
                                                         colorbar_title=legend_file)
            return geo_contour,legend_file
        else:
            raise(ValueError("To be linked"))
        
    def update_html(self,feature, **kwargs):
        self.html1.value = '''
        <h4> Type de temps </h4>
        <h4><b>{}</b></h4>
        '''.format(feature['properties']['legend']) 
        
        
class interactive_choro_map(interactive_map): 
    def __init__(self,*args,**kwargs): 
        
        super().__init__(*args,**kwargs)
        self.html2 = HTML(''' Graphique ''')
        self.children = (self.children[0],self.html2)
        
    def change_step(self,change):
        super().change_step(change)
        self.update_hist()
    def variable_change(self,change):
        super().variable_change(change)
        self.update_hist() 
        
    def change_date(self,change):
        super().change_date(change)
        self.update_hist() 
        
    def update_hist(self):
        hv.extension("matplotlib")
        dcrop = (self.da_masked*self.da_zone.sel(id=self.id_i)).isel(step=self.step)
        dcrop.name = self.da.name
        var_name = self.da.name 
        if self.levels:
            hv_img = hv.Image(hv.Dataset(dcrop),kdims=["longitude","latitude"]).opts(colorbar=True, color_levels=self.levels,
                                                                                    cmap = self.colors)
            html_map = hv.renderer("matplotlib").html(hv_img)
        else:
            hv_img = hv.Image(hv.Dataset(dcrop),kdims=["longitude","latitude"]).opts(colorbar=True, color_levels=30)
            html_map  = hv.renderer("matplotlib").html(hv_img)
       # Si besoin de specifier le range : hv_img.redim.__getattribute__("range")(**{var_name:(self.vmin,self.vmax)}))
        
        dstack = dcrop.stack(z=("latitude","longitude")).reset_index("z")
        dstack["z"]=range(len(dstack.z))
        dstack.name = self.da.name
        hv_dst = hv.Dataset(dstack)
        k = histogram(hv_dst,dynamic=True,name="Test")
        
        html = ''' <h4> Histogramme sur {} </h4> de {}'''.format(self.hist_name,self.variable)
        self.html2.value = html + hv.renderer("matplotlib").html(k) +html_map
        
        
        
    def hist_html(self,event=None, id=None, properties=None,**args):
        from holoviews.operation import histogram
        import holoviews as hv
        if event == "click":
            self.id_i = properties["id"]
            self.hist_name = properties.get("name",properties["id"])
            self.update_hist()
        
        
    def render(self):
        # On ajoute le choropleth
        chor_layer = ipyl.Choropleth(geo_data=self.region_geo,
                                    choro_data=self.da_aggregated.isel(step=self.step).to_pandas().to_dict(),
                                    name="regional_mean",
                                    value_min = self.vmin,
                                    value_max = self.vmax,
                                    colormap=linear.RdBu_03)

        if hasattr(self,"chor_layer"):
            if self.chor_layer in self.m.layers:
                self.m.substitute_layer(self.chor_layer,chor_layer)
            else: 
                self.m.add_layer(chor_layer)
        else:
            self.m.add_layer(chor_layer)
        self.chor_layer = chor_layer
        self.chor_layer.on_hover(self.update_chor_html)
        # On ajoute l'interactivité sur click
        self.chor_layer.on_click(self.hist_html)
  
class Agg_Map(contour_interactive):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        
        drop_Agg = widg.Dropdown(description="Aggregation method",options={"Compas":"compas",
                                                                           "Compas asymétrique":"compas_asym",
                                                                           'AGAT':"agat",
                                                                           'AGAT asymétrique':"agat_asym"})
        drop_Agg.value = self.distance_choice
        drop_Agg.observe(self.change_aggregate,"value")
        self.m.add_control(ipyl.WidgetControl(widget = drop_Agg,
                                              position="topright"))
    
    def change_aggregate(self,change):
        self.distance_choice = change["new"]
        self.get_Mary_zone()
        self.get_sympo_zone2()
        self.update_HSS_area()
        self.update_homo_area()