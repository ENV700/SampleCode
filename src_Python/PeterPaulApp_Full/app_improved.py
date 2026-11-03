"""Lake nutrient explorer — Python Shiny dashboard.

Run from VS Code with: shiny run --reload --launch-browser app.py
Requires: shiny, pandas, seaborn, matplotlib.
Place the NTL-LTER CSV in the Data/ folder beside this script.

The original notebook's data wrangling and Seaborn scatterplot are retained.
The dashboard adds a polished layout, shared reactive filtering, and CSV export.
"""

# Step 1: Load and prepare the data (once, when the app starts)
from pathlib import Path
from itertools import cycle

import matplotlib.dates as mdates
from matplotlib.figure import Figure
import pandas as pd
import seaborn as sns
from shiny import App, reactive, render, ui

sns.set_theme(style="whitegrid")

DATA_FILE = (
    Path(__file__).resolve().parent
    / "Data"
    / "NTL-LTER_Lake_Nutrients_PeterPaul_Processed.csv"
)

# Same data reshaping as the notebook; don't repeat it on every input change.
df_nutrients = pd.read_csv(
    DATA_FILE,
    parse_dates=["sampledate"],
    dtype={"lakename": "category", "depth_id": "category"},
).melt(
    id_vars=["lakename", "sampledate", "depth_id"],
    value_vars=["tn_ug", "tp_ug", "nh34", "no23"],
    var_name="nutrient",
    value_name="ug",
).rename(columns={
    "lakename": "Lake name",
    "depth_id": "Depth zone",
})

nutrient_name_updates = {
    "tn_ug": "Total Nitrogen",
    "tp_ug": "Total Phosphorus",
    "nh34": "Ammonia",
    "no23": "Nitrates",
}
df_nutrients["nutrient"] = df_nutrients["nutrient"].map(nutrient_name_updates)
df_nutrients["ug"] = pd.to_numeric(df_nutrients["ug"], errors="coerce")

# Missing measurements cannot appear in the plot; remove them up front.
df_nutrients = df_nutrients.dropna(
    subset=["sampledate", "Lake name", "Depth zone", "ug"]
)
if df_nutrients.empty:
    raise ValueError("The nutrient data has no valid measurements to plot.")

nutrient_list = list(nutrient_name_updates.values())
min_date = df_nutrients["sampledate"].min().date()
max_date = df_nutrients["sampledate"].max().date()
depth_zones = df_nutrients["Depth zone"].unique().tolist()
lake_names = df_nutrients["Lake name"].unique().tolist()

# Select controls send strings. Map depth selections back to their original types.
depth_zone_lookup = {str(zone): zone for zone in depth_zones}

# Performance: only search records for the selected nutrient, not all 4 nutrients.
DATA_BY_NUTRIENT = {
    nutrient: df_nutrients.loc[df_nutrients["nutrient"] == nutrient]
    for nutrient in nutrient_list
}

# Keep colors and marker shapes consistent while users change filters.
DEPTH_COLORS = dict(zip(
    depth_zones, sns.color_palette("crest", n_colors=len(depth_zones))
))
MARKER_SHAPES = cycle(["o", "D", "^", "s", "P", "X", "v", "<", ">"])
LAKE_MARKERS = {lake: next(MARKER_SHAPES) for lake in lake_names}


def filter_nutrients(start_date, end_date, nutrient, depth_zones_selected, lake_names_selected):
    """Return measurements that match the UI selections."""
    data = DATA_BY_NUTRIENT[nutrient]
    if not depth_zones_selected or not lake_names_selected:
        return data.iloc[0:0]

    # End is exclusive on the following day, including all times on end_date.
    start = pd.Timestamp(start_date)
    end_exclusive = pd.Timestamp(end_date) + pd.Timedelta(days=1)
    keep = (
        (data["sampledate"] >= start)
        & (data["sampledate"] < end_exclusive)
        & data["Depth zone"].isin(depth_zones_selected)
        & data["Lake name"].isin(lake_names_selected)
    )
    return data.loc[keep]


# Step 2: Create the plot (Seaborn, as in the notebook)
def plot_nutrients(df_subset, nutrient):
    """Create the same time-series scatterplot using a lighter axes-level API."""
    # Figure + sns.scatterplot() avoids creating a new Seaborn FacetGrid.
    fig = Figure(figsize=(11.5, 5.4), dpi=110, facecolor="white")
    ax = fig.add_subplot(111)
    ax.set_facecolor("white")

    if df_subset.empty:
        ax.text(
            0.5, 0.54, "No observations match these filters",
            transform=ax.transAxes, ha="center", va="center",
            fontsize=16, fontweight="semibold", color="#243b47",
        )
        ax.text(
            0.5, 0.46, "Try selecting more lakes, depths, or dates.",
            transform=ax.transAxes, ha="center", va="center",
            fontsize=11, color="#7a8b94",
        )
        ax.set_axis_off()
        return fig

    sns.scatterplot(
        data=df_subset,
        x="sampledate",
        y="ug",
        hue="Depth zone",
        style="Lake name",
        palette=DEPTH_COLORS,
        markers=LAKE_MARKERS,
        hue_order=df_subset["Depth zone"].unique().tolist(),
        style_order=df_subset["Lake name"].unique().tolist(),
        s=38,
        alpha=0.78,
        edgecolor="none",
        ax=ax,
    )

    ax.set_xlabel("Sampling date", labelpad=12, fontsize=11, color="#465f6a")
    ax.set_ylabel(nutrient, labelpad=12, fontsize=11, color="#465f6a")
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=8))
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
    ax.tick_params(axis="both", labelsize=10, colors="#5c7079", length=0, pad=8)
    ax.grid(axis="y", color="#e5edef", linewidth=0.85)
    ax.grid(axis="x", visible=False)
    for spine in ax.spines.values():
        spine.set_visible(False)

    # A fixed legend area avoids squeezing the graph unpredictably.
    legend = ax.get_legend()
    if legend is not None:
        legend.set_bbox_to_anchor((1.01, 1))
        legend.set_loc("upper left")
        legend.set_frame_on(False)
        legend.get_title().set_fontsize(10)
        for label in legend.get_texts():
            label.set_fontsize(9)
    fig.subplots_adjust(left=0.09, right=0.79, bottom=0.16, top=0.94)
    return fig


# Step 3: Dashboard styling (one file; no external assets required)
APP_CSS = """
:root { --ink: #183643; --muted: #657d86; --sea: #12767c; --line: #e2ecee; }
html, body { background: #f2f6f7; color: var(--ink); font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
.navbar { background: #103541 !important; border-bottom: 1px solid #2c5960; box-shadow: 0 3px 14px #0c33401a; }
.navbar .navbar-brand { color: #ffffff !important; font-weight: 700; letter-spacing: .025em; }
.navbar .navbar-brand:hover { color: #e7f7f4 !important; }
.bslib-sidebar-layout { background: transparent; }
.filters-sidebar { border-right: 1px solid var(--line) !important; }
.filters-sidebar .sidebar-content { padding-top: 8px; }
.filters-sidebar .form-label, .filters-sidebar label { color: #274450; font-weight: 620; font-size: .9rem; }
.filters-sidebar .form-group { margin-bottom: 1.35rem; }
.filters-sidebar .form-select, .filters-sidebar .selectize-input { border-color: #d4e3e4; border-radius: 9px; }
.filters-sidebar .irs-bar, .filters-sidebar .irs-from, .filters-sidebar .irs-to, .filters-sidebar .irs-single { background: var(--sea); }
.filters-sidebar .irs-handle > i:first-child { background: var(--sea) !important; }
.sidebar-eyebrow { font-size: .69rem; letter-spacing: .15em; font-weight: 800; color: #668790; margin: 18px 0 10px; }
.sidebar-intro { font-size: .88rem; color: #6d858c; line-height: 1.55; margin-bottom: 10px; }
.sidebar-divider { border: 0; border-top: 1px solid #e1ebec; margin: 22px 0; }
.reset-btn { width: 100%; color: #235c65; background: #e9f2f2; border: 1px solid #cddfe0; border-radius: 9px; font-weight: 650; padding: 10px; }
.reset-btn:hover { background: #dceced; color: #194953; }
.dashboard-main { max-width: 1480px; margin: 0 auto; padding: 12px 8px 34px; }
.hero { position: relative; overflow: hidden; padding: 30px 38px; border-radius: 18px; color: white;
  background: radial-gradient(circle at 85% 0%, #286a70 0, transparent 45%), linear-gradient(117deg, #153a48, #0d5761 78%); margin-bottom: 22px; }
.hero::after { content: ""; width: 250px; height: 250px; position: absolute; border: 1px solid #ffffff20; border-radius: 50%; top: -135px; right: 70px; box-shadow: 0 0 0 45px #ffffff08, 0 0 0 96px #ffffff06; pointer-events: none; }
.hero-label { font-size: .7rem; font-weight: 800; letter-spacing: .16em; color: #a9e3dc; margin: 0 0 10px; }
.hero h1 { font-size: clamp(1.7rem, 3vw, 2.45rem); margin: 0 0 8px; font-weight: 760; letter-spacing: -.025em; }
.hero p { margin: 0; max-width: 600px; color: #d0e8e8; font-size: .99rem; line-height: 1.55; }
.metric-tile { border: 1px solid #e5edef; border-radius: 14px; background: white; padding: 19px 22px; min-height: 128px; box-shadow: 0 5px 18px #163e4609; }
.metric-label { font-size: .7rem; font-weight: 800; letter-spacing: .12em; color: #69828c; text-transform: uppercase; }
.metric-tile .shiny-text-output { display: block; font-size: 2rem; font-weight: 760; line-height: 1.35; letter-spacing: -.04em; color: #143e48; margin: 4px 0; }
.metric-note { font-size: .75rem; color: #889ca2; }
.plot-card { border: 1px solid #e4edee; background: white; box-shadow: 0 7px 22px #163e4610; border-radius: 16px; margin-top: 19px; overflow: hidden; }
.plot-card .card-header { background: #fff; border-bottom: 1px solid #edf2f2; padding: 23px 28px 15px; }
.plot-eyebrow { color: #15918c; font-size: .69rem; letter-spacing: .13em; font-weight: 800; }
.plot-card h2 { margin: 6px 0 6px; font-size: 1.28rem; font-weight: 730; letter-spacing: -.02em; }
.plot-subtitle { color: #81949c; font-size: .84rem; }
.plot-card .card-body { padding: 4px 20px 5px; }
.plot-card .card-footer { background: #fff; border-top: 1px solid #edf2f2; padding: 15px 26px; }
.plot-footer { display: flex; justify-content: space-between; align-items: center; gap: 16px; flex-wrap: wrap; }
.plot-note { color: #71848c; font-size: .82rem; }
.export-btn { border-radius: 9px; padding: 9px 16px; background: #116e73; border: 1px solid #116e73; font-weight: 650; }
.export-btn:hover { background: #0a565a; border-color: #0a565a; }
.data-attribution { font-size: .76rem; color: #91a1a6; padding: 13px 4px 0; }
@media(max-width: 700px) { .hero { padding: 25px 23px; } .metric-tile { padding: 15px; min-height: 115px; } .plot-card .card-header { padding: 18px; } .plot-card .card-body { padding: 0; } }
"""


def metric_tile(label, output_id, note):
    return ui.div(
        ui.div(label, class_="metric-label"),
        ui.output_text(output_id, inline=True),
        ui.div(note, class_="metric-note"),
        class_="metric-tile",
    )


# Step 4: User interface (same four controls, redesigned layout)
app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.div("FILTER THE DATA", class_="sidebar-eyebrow"),
        ui.div("Adjust any selection to update the chart and summary.", class_="sidebar-intro"),
        ui.div("01  ·  TIME PERIOD", class_="sidebar-eyebrow"),
        ui.input_slider(
            "date_slider", "Sampling date range",
            min=min_date, max=max_date, value=(min_date, max_date),
            time_format="%b %Y", drag_range=True,
        ),
        ui.hr(class_="sidebar-divider"),
        ui.div("02  ·  CHEMISTRY", class_="sidebar-eyebrow"),
        ui.input_select(
            "nutrient_dropdown", "Nutrient",
            choices=nutrient_list, selected=nutrient_list[0],
        ),
        ui.hr(class_="sidebar-divider"),
        ui.div("03  ·  SAMPLING LOCATION", class_="sidebar-eyebrow"),
        ui.input_select(
            "lake_name_select", "Lakes",
            choices=lake_names, selected=lake_names, multiple=True,
        ),
        ui.input_select(
            "depth_zone_select", "Depth zones",
            choices=list(depth_zone_lookup),
            selected=list(depth_zone_lookup), multiple=True,
        ),
        ui.input_action_button("reset_filters", "Reset all filters", class_="reset-btn"),
        width=310, open="desktop", bg="#fbfdfd", class_="filters-sidebar",
    ),
    ui.tags.head(ui.tags.style(APP_CSS)),
    ui.div(
        ui.div(
            ui.div("FRESHWATER DATA EXPLORER  /  NTL-LTER", class_="hero-label"),
            ui.h1("Lake nutrient explorer"),
            ui.p("Explore nutrient measurements over time and compare patterns among lakes and sampling depths."),
            class_="hero",
        ),
        ui.layout_columns(
            metric_tile("Observations", "metric_observations", "Measurements in selected data"),
            metric_tile("Sampling dates", "metric_dates", "Distinct sampling days"),
            metric_tile("Median value", "metric_median", "In the data's reported units"),
            col_widths=[4, 4, 4], fill=False,
        ),
        ui.card(
            ui.card_header(
                ui.div("TEMPORAL DISTRIBUTION", class_="plot-eyebrow"),
                ui.h2("Nutrient measurements"),
                ui.div(ui.output_text("selection_summary", inline=True), class_="plot-subtitle"),
            ),
            ui.output_plot("nutrient_plot", height="520px"),
            ui.card_footer(
                ui.div(
                    ui.div("Color represents depth zone · Marker shape represents lake", class_="plot-note"),
                    ui.download_button("download_csv", "Download filtered CSV", class_="export-btn"),
                    class_="plot-footer",
                )
            ),
            full_screen=True, fill=False, class_="plot-card",
        ),
        ui.div(
            "Source: NTL-LTER nutrient data · Summary values describe the currently filtered measurements.",
            class_="data-attribution",
        ),
        class_="dashboard-main",
    ),
    title="Lake nutrients", window_title="Lake nutrient explorer",
)


# Step 5: Reactive server logic
# One cached reactive calculation feeds every output. Filtering runs only
# when a control changes, not independently for each summary and the plot.
def server(input, output, session):
    @reactive.calc
    def filtered_data():
        return filter_nutrients(
            start_date=input.date_slider()[0],
            end_date=input.date_slider()[1],
            nutrient=input.nutrient_dropdown(),
            depth_zones_selected=[depth_zone_lookup[z] for z in (input.depth_zone_select() or ())],
            lake_names_selected=input.lake_name_select() or (),
        )

    @render.text
    def metric_observations():
        return f"{len(filtered_data()):,}"

    @render.text
    def metric_dates():
        dates = filtered_data()["sampledate"].dt.normalize().nunique()
        return f"{dates:,}"

    @render.text
    def metric_median():
        data = filtered_data()
        return f"{data['ug'].median():,.1f}" if not data.empty else "—"

    @render.text
    def selection_summary():
        start, end = input.date_slider()
        return f"{input.nutrient_dropdown()}  ·  {start:%b %Y} – {end:%b %Y}"

    @render.plot(alt="Nutrient measurements by date, depth zone, and lake")
    def nutrient_plot():
        return plot_nutrients(filtered_data(), input.nutrient_dropdown())

    @render.download_button(filename="lake_nutrients_filtered.csv")
    def download_csv():
        # Data are serialized only when the user asks for a download.
        yield filtered_data().to_csv(index=False)

    @reactive.effect
    @reactive.event(input.reset_filters)
    def _reset_filters():
        ui.update_slider("date_slider", value=(min_date, max_date))
        ui.update_select("nutrient_dropdown", selected=nutrient_list[0])
        ui.update_select("depth_zone_select", selected=list(depth_zone_lookup))
        ui.update_select("lake_name_select", selected=lake_names)


# Step 6: Create the Shiny app
app = App(app_ui, server)
