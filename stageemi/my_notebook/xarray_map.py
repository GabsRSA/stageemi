import stageemi.dev.decorator_map as dm
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

      
    
class interactive_map(widg.HBox):
    
    def __init__(self):
        self.m = ipyl.Map(center=(45,0),zoom=7,layout={"height":"500px"})
        # Date 
        date_picker = widg.DatePicker(value=dt.datetime(2020,1,26))
        self._date = date_picker.value 
        date_picker.observe(self.change_date,"value")
        self.step = 0
        variable_picker = widg.Dropdown(value="WWMF",options=["WWMF","PRECIP","T"])
        variable_picker.observe(self.variable_change,"value")
        dept_picker = widg.Dropdown(value="38",options={"Isère":"38","Hérault":"34"})
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
        #elif self.dept == "34":
        #    da_mask = xr.open_dataarray("../GeoData/nc_departement/FRJ13.nc")
        else: 
            raise(ValueError("Departement not known. Please add it"))
        da_mask["latitude"] = da_mask.latitude.round(5)
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
        #dir_zone = "/scratch/labia/lepapeb/geo_data/nc/StageEMI/ZONE_SYMPO/"
        #l_file = os.listdir(dir_zone)
        #l_dept = [dir_zone + x for x in l_file if (x.startswith(self.dept))]
        #self.da_zone = xr.open_mfdataset(l_dept,combine="nested",concat_dim="id").load()["mask"] 
        
        #start modif read Mary zone sympos files
        fname_mask = '../GeoData/zones_sympo_multiples/'+self.dept+'_mask_zones_sympos.nc'
        da_mask = xr.open_dataarray(fname_mask)
        zs_l=[zs for zs in da_mask.id.values.tolist() if "+" not in zs]
        zs_N=len(zs_l)
        self.da_zone=da_mask.isel(id=slice(1,zs_N)).load()
        print(self.da_zone)
        #end modif 
        
        self.da_zone["latitude"] = self.da_zone.latitude.round(5)
        #zsympo = "../GeoData/ZonesSympo/zones_sympo_4326.json"
        zsympo = "../GeoData/ZonesSympo/zones_sympo_38.json"
        
        with open(zsympo) as geojson1:
            poly_geojson = json.load(geojson1)
        new_poly  ={}
        new_poly["type"] = poly_geojson["type"]
        #new_poly["crs"] = poly_geojson["crs"]
        new_poly["features"] = []
        for x in poly_geojson["features"]:
            if x["properties"]["id"] in self.da_zone.id.values:
                print("par ici")
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
        if self.variable == "WWMF":
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
        if hasattr(self,"mask"):
             self.mask_da()
        if hasattr(self,"da_zone"):
            self.aggregate()
                
    @dm.gogeojson_wwmf
    def get_step(self):
        return self.da_masked.isel(step=self.step)
    
        
    def update_html(self,feature, **kwargs):
        self.html1.value = '''
        <h4> Type de temps </h4>
        <h4><b>{}</b></h4>
        '''.format(feature['properties']['value'])
        
    def update_chor_html(self,feature,**kwargs):
        id_i = feature["properties"]["id"]
        x = self.da_aggregated.isel(step=self.step).sel(id=id_i).values
        self.html1.value = '''
        <h4> Valeur sur {} </h4>
        <h4><b>{}</b></h4>
        '''.format(feature["properties"]["name"],x)
        
    def change_step(self,change):
        self.step = change["new"]
        self.render()
        
    def render(self):
        geo_file,legend_file = self.get_step()
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
        # Ajout du layer vectoriel 
        #start debug 
        #print(self.region_geo)
        #print(self.da_aggregated.isel(step=self.step).to_pandas().to_dict())
        #print(self.vmin)
        #print(self.vmax)
        #print(linear.RdBu_03)
        #end debug
        
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
            self.hist_name = properties["name"]
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
  