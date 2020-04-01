import stageemi.dev.decorator_map as dm
from stageemi.dev.distance_wwmf import conversion 
import xarray as xr 
import ipywidgets as widg 
import ipyleaflet as ipyl
import datetime as dt
import os 
from ipywidgets import Text, HTML
from ipyleaflet import WidgetControl
import json 
from branca.colormap import linear
from holoviews.operation import histogram
import holoviews as hv
import pandas as pd
import numpy as np

      
    
class interactive_map(widg.HBox):
    
    def __init__(self):
        self.m = ipyl.Map(center=(45,0),zoom=7,layout={"height":"500px"})
        # Date 
        date_picker = widg.DatePicker(value=dt.datetime(2020,1,26))
        self._date = date_picker.value 
        date_picker.observe(self.change_date,"value")
        self.step = 0
        variable_picker = widg.Dropdown(value="WWMF",options=["WWMF","WME","W1","PRECIP","T"])
        variable_picker.observe(self.variable_change,"value")
        dept_picker = widg.Dropdown(value="41",options={"Isère":"38","Hérault":"34","Loire-et-cher":"41"})
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
    
        slider = widg.IntSlider(min=0,max=len(self.da.step),step=1,value=0,description="step")
        slider.observe(self.change_step,'value')
        self.m.add_control(ipyl.WidgetControl(widget=widg.VBox([date_picker,slider,variable_picker,dept_picker]),position="topright"))
        self.m.add_control(ipyl.FullScreenControl())
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
  
    def aggregate(self):
        self.da_aggregated = (self.da_masked * self.da_zone).mean(["latitude","longitude"])
   
        
    def get_mask(self):
        if self.dept == "38":
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
        self.get_sympo_zone()
        if hasattr(self,"html1"):
            self.html1.values = '''<h4>Type de temps</h4>
                        Hover over a pixel
                        '''
        if hasattr(self,"da"):
            self.render()
        
    def get_sympo_zone(self):
        """
        Retourne les zones du departement concernes
        """
          
        #read Mary zone sympos files
        fname_mask = '../GeoData/zones_sympo_multiples/'+self.dept+'_mask_zones_sympos.nc'
        da_mask = xr.open_dataarray(fname_mask)
        zs_l = da_mask.id.values.tolist()[1:5] #[zs for zs in da_mask.id.values.tolist() if "+" not in zs]
        
        fileresult='../zonageWME/'+self.dept+'_'+self.date.strftime("%Y%m%d%H")+'_'+str(self.step)+'.csv'
        try:
            f = open(fileresult)
            # Do something with the file
            dfres=pd.read_csv(fileresult,sep=',',index_col=0)
            print(dfres)
            zs_l=dfres["zone"].to_list()
            print(zs_l)
            self.dfres=dfres
        except IOError:
            print("File not accessible")
            zs_l=["departement"]
            if hasattr(self,"dfres"):
                    del(self.dfres)  # we suppress the attribute in order to ignore the condition in update_chor_html      
        
        
        self.da_zone = da_mask.sel(id=zs_l).load()
        
        self.da_zone["latitude"] = self.da_zone.latitude.round(5)
        self.da_zone["longitude"] = self.da_zone.longitude.round(5)
        #zsympo = "../GeoData/ZonesSympo/zones_sympo_4326.json"
        #zsympo = "../GeoData/ZonesSympo/zones_sympo_"+self.dept+".json"
        zsympo = "../GeoData/ZonesSympo/zones_sympo_combined_"+self.dept+".json"
        
        with open(zsympo) as geojson1:
            poly_geojson = json.load(geojson1)
        new_poly  ={}
        new_poly["type"] = poly_geojson["type"]
        #new_poly["crs"] = poly_geojson["crs"]
        new_poly["features"] = []
        for x in poly_geojson["features"]:
            if x["properties"]["id"] in self.da_zone.id.values:
           
                x["id"] = x["properties"]["id"]
                new_poly["features"].append(x)
        self.region_geo = new_poly 
        if hasattr(self,"da"):
            self.aggregate()
            
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
            #print("on passe vraiment ici?")
            self.mask_da()
        if hasattr(self,"da_zone"):
            #print("et là aussi?")
            self.aggregate()
                
    @dm.gogeojson_wwmf
    def get_step(self,variable = "wwmf"):
        if self.variable in  ["WME","W1"]:
            print("Getting special variable %s"%self.variable)
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
            print("Getting normal variable %s"%self.variable)
            da = self.da_masked.isel(step=self.step)
        return da
    
        
    def update_html(self,feature, **kwargs):
        self.html1.value = '''
        <h4> Type de temps </h4>
        <h4><b>{}</b></h4>
        '''.format(feature['properties']['value'])
        
    def update_chor_html(self,feature,**kwargs):
        
        if hasattr(self, "dfres"):
            id_i = feature["properties"]["id"]
            r = int(self.dfres.loc[self.dfres['zone']==id_i]['cible_wme'])#da_aggregated.isel(step=self.step).sel(id=id_i).values
            w = int(self.dfres.loc[self.dfres['zone']==id_i]['compas'])
            x = int(self.dfres.loc[self.dfres['zone']==id_i]['agat'])
            y = int(self.dfres.loc[self.dfres['zone']==id_i]['compas_asym'])
            z = int(self.dfres.loc[self.dfres['zone']==id_i]['agat_asym'])    
            
            filecodeswwmf='../utils/CodesWWMF.csv'
            # Do something with the file
            df=pd.read_csv(filecodeswwmf,sep=',')
            #print(df.head)
            rstr=np.unique(df.loc[df['Code WME']==r]['Legende WME'])[0]
            wstr=np.unique(df.loc[df['Code WME']==w]['Legende WME'])[0]
            xstr=np.unique(df.loc[df['Code W1']==x]['Legende W1'])[0]
            ystr=np.unique(df.loc[df['Code WME']==y]['Legende WME'])[0]
            zstr=np.unique(df.loc[df['Code W1']==z]['Legende W1'])[0]
            
            # avec le code
            #self.html1.value = '''
            #<h4> Valeur sur {} </h4>
            #<h4><b>cible wme: {} {}</b></h4>
            #<h4><b>compas: {} {}</b></h4>
            #<h4><b>agat: {} {}</b></h4>
            #<h4><b>compas asym: {} {}</b></h4>
            #<h4><b>agat asym: {} {}</b></h4>            
            #'''.format(feature["properties"]["id"],rstr,r,wstr,w,xstr,x,ystr,y,zstr,z)
            
            # sans le code juste lae descriptif
            self.html1.value = '''
            <h4> Valeur sur {} </h4>
            <h4><b>cible wme: {}</b></h4>
            <h4><b>compas: {}</b></h4>
            <h4><b>agat: {}</b></h4>
            <h4><b>compas asym: {}</b></h4>
            <h4><b>agat asym: {}</b></h4>            
            '''.format(feature["properties"]["id"],rstr,wstr,xstr,ystr,zstr)
                                                            
        else: 
            self.html1.value = '''
            <h4> Valeur sur {} </h4>
            <h4><b>Not calculated</b></h4>
            '''.format(feature["properties"]["id"])
            
    def change_step(self,change):
        self.step = change["new"]
        self.get_sympo_zone()
        self.render()
        
    def render(self):
        #print("Avant de descendre dans le decorateur etc")
        geo_file,legend_file = self.get_step(variable= self.variable)
        #print("On en revient ici")
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
    
        
        chor_layer = ipyl.Choropleth(geo_data=self.region_geo,
                                    choro_data=self.da_aggregated.isel(step=self.step).to_pandas().to_dict(),
                                    name="zonage sur temps sensible (WME)",
                                    value_min = self.vmin,
                                    value_max = self.vmax,
                                    colormap=linear.RdBu_03)
                                    #name="regional_mean")
            
        if hasattr(self,"chor_layer"):
            if self.chor_layer in self.m.layers:
                #print("on passe la")
                self.m.substitute_layer(self.chor_layer,chor_layer)
            else: 
                self.m.add_layer(chor_layer)
        else:
            self.m.add_layer(chor_layer)
        self.chor_layer = chor_layer
        self.chor_layer.on_hover(self.update_chor_html)
        
        
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
                                    #name="regional_mean")
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
  