"""Shiny version of app_widgets.ipynb.

Keep this file alongside the Data/ folder used by the original notebook.
Run from an activated environment with: shiny run --reload app.py
"""
#%%
# Step 1: Read in the data and create the plot function
# Import packages
from pathlib import Path
import pandas as pd
import seaborn as sns
from shiny import App, render, req, ui

# Set sns theme
sns.set_theme(style='whitegrid')

#%%
# Read the data into a dataframe, pivotting nutrients into longer format
# Path(__file__) makes the Data path relative to this script.
data_file = Path(__file__).resolve().parent / 'Data' / 'NTL-LTER_Lake_Nutrients_PeterPaul_Processed.csv'
df_nutrients = pd.read_csv(
    data_file,
    parse_dates=['sampledate'],
    dtype={'lakename': 'category', 'depth_id': 'category'}
).melt(
    id_vars=['lakename', 'sampledate', 'depth_id'],
    value_vars=['tn_ug', 'tp_ug', 'nh34', 'no23'],
    var_name='nutrient',
    value_name='ug'
).rename(columns={
    'lakename': 'Lake name',
    'depth_id': 'Depth zone'
})

# Update nutrient values to more readable names
nutrient_name_updates = {
    'tn_ug': 'Total Nitrogen',
    'tp_ug': 'Total Phosphorus',
    'nh34': 'Ammonia',
    'no23': 'Nitrates'
}
df_nutrients['nutrient'] = df_nutrients['nutrient'].map(nutrient_name_updates)

#%%
# Plot as a function (same function as in the notebook)
def plot_nutrients(start_date='1995-01-01',
                   end_date='1999-12-31',
                   nutrient='Total Nitrogen',
                   depth_zones=[1, 2, 3],
                   lake_names=['Peter Lake', 'Paul Lake']):
    # Subset the data
    df_subset = df_nutrients.loc[
        (df_nutrients['sampledate'] >= start_date) &  # Start date (inclusive)
        (df_nutrients['sampledate'] <= end_date) &    # End date (inclusive)
        (df_nutrients['nutrient'] == nutrient) &      # Nutrient
        (df_nutrients['Depth zone']).isin(depth_zones) &  # Depth IDs
        (df_nutrients['Lake name']).isin(lake_names),     # Lake names
    ]

    # Create a plot of selected nutrients by sampledate, with markers
    # colored by depth_id and different shapes for lakename
    the_plot = sns.relplot(
        data=df_subset,
        x='sampledate',
        y='ug',
        hue='Depth zone',
        style='Lake name', markers=['d', 'o'],
        palette='magma',
        s=20,
        alpha=0.7,
    )

    # Set plot title and axis labels
    the_plot.set_axis_labels('Sample Date', nutrient)
    the_plot.set(title=f'{nutrient}')
    the_plot.set_xticklabels(rotation=45, ha='right')

    # Clean up the legend
    sns.move_legend(
        the_plot,
        loc='center right',
        frameon=True,
    )

    # Return the plot
    return the_plot

#%%
# Step 2: Get choices for the controls (same values as the ipywidgets)
nutrient_list = df_nutrients['nutrient'].unique()
min_date = df_nutrients['sampledate'].min().date()
max_date = df_nutrients['sampledate'].max().date()
depth_zones = df_nutrients['Depth zone'].unique()
lake_names = df_nutrients['Lake name'].unique()

# Shiny selection values are strings. Keep a lookup to original depth types.
depth_zone_lookup = {str(zone): zone for zone in depth_zones}

#%%
# Step 3: Create Shiny controls and the plot location
app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_slider(
            'date_slider', 'Date range:',
            min=min_date, max=max_date,
            value=(min_date, max_date),
            time_format='%Y/%m/%d',
        ),
        ui.input_select(
            'nutrient_dropdown', 'Nutrient:',
            choices=list(nutrient_list),
            selected=nutrient_list[0],
        ),
        ui.input_select(
            'depth_zone_select', 'Depth zones:',
            choices=list(depth_zone_lookup),
            selected=[str(depth_zones[0])],
            multiple=True,
        ),
        ui.input_select(
            'lake_name_select', 'Lake names:',
            choices=list(lake_names),
            selected=[lake_names[0]],
            multiple=True,
        ),
    ),
    ui.output_plot('nutrient_plot', height='550px'),
    title='Lake Nutrients',
)

#%%
# Step 4: Update the plot when the controls change
# @render.plot replaces the ipywidgets .observe() callbacks and Output widget.
def server(input, output, session):
    @render.plot
    def nutrient_plot():
        # Don't attempt to plot if either multi-select has no selections.
        req(input.depth_zone_select(), input.lake_name_select())

        g = plot_nutrients(
            start_date=pd.Timestamp(input.date_slider()[0]),
            end_date=pd.Timestamp(input.date_slider()[1]),
            nutrient=input.nutrient_dropdown(),
            depth_zones=[depth_zone_lookup[z] for z in input.depth_zone_select()],
            lake_names=input.lake_name_select(),
        )
        return g.figure

#%%
# Step 5: Combine the user interface and the server
app = App(app_ui, server)
