# %% [markdown]
# # Dashboard Example
# - CalFire REST endpoint: <https://services2.arcgis.com/iq8zYa0SRsvIFFKz/ArcGIS/rest/services/CAL_FIRE/FeatureServer/0>
# 
#
# **CONDA RECIPE**
# ```bash
# conda create -n env700-shiny -c conda-forge python=3.12 shiny geopandas pandas matplotlib folium mapclassify jupyterlab ipykernel
# ```
#
# John Fay · Fall 2026
#  
# ---
# %%
# SETUP
# Packages
from pathlib import Path
import requests, json
import pandas as pd
import geopandas as gpd

# Paths
project_path = Path(__file__).parent.resolve()
data_path = project_path / 'Data' / 'raw'

# %%
# FUNCTIONS
# Fetch Calfire Fire Perimeters
# See <https://developers.arcgis.com/rest/services-reference/enterprise/query-feature-service/>
rest_url='https://services2.arcgis.com/iq8zYa0SRsvIFFKz/ArcGIS/rest/services/CAL_FIRE/FeatureServer/0/query'
query_params = {
    'where': "ALARM_DATE >= DATE '1991-01-01' AND ALARM_DATE < DATE '1992-01-01'",
    'outFields':'*',
    'f':'pgeojson'
}
response = requests.get(rest_url,params=query_params)
response_json = response.json()

# Convert to geojson
gdf = gpd.GeoDataFrame.from_features(
    response_json["features"],
    crs="EPSG:4326"
)

# %%
gdf.plot()