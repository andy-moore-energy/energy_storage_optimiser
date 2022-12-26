from typing import List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from models import ScenarioManager


def get_design_results(scenario: ScenarioManager) -> dict:
    """
    Show only the design specific results for sizing the battery system
    """
    assert scenario.solved_status
    results = {}
    for var in scenario.lpmodel.variables():
        if var.name in ["capacity", "power"]:
            results[var.name] = var.value()
    return results


def get_operational_batteryflow_results(scenario: ScenarioManager) -> pd.DataFrame:
    variables = {}
    for v in scenario.lpmodel.variables():
        variables[v.name] = v.value()

    var_df = pd.Series(variables).reset_index()
    var_df.rename(columns={0: "value"}, inplace=True)

    var_df["parameter"] = var_df["index"].str.split("_").str[0]

    time_results = var_df.loc[
        var_df["parameter"].isin(["storagelevel", "charge", "discharge"])
    ].copy()
    time_results["timestep"] = time_results["index"].str.split("_").str[-1]
    time_results["timestep"] = pd.to_numeric(time_results["timestep"])

    time_results["time"] = scenario.inputs.start_date + pd.to_timedelta(
        time_results["timestep"], unit="H"
    )
    time_results = time_results.sort_values(by=["parameter", "time"])
    return time_results.pivot(index="time", columns="parameter", values="value")


def get_full_operation_data(scenario) -> pd.DataFrame:
    plot_df = get_operational_batteryflow_results(scenario)
    plot_df["charge_cumulative"] = plot_df["charge"].cumsum()
    plot_df["discharge_cumulative"] = plot_df["discharge"].cumsum()

    plot_df = pd.concat([plot_df, scenario.inputs.renewables.generation], axis=1)
    plot_df["Load"] = scenario.inputs.load.load
    plot_df["Curtailment_final"] = (
        plot_df["Total"] + plot_df["discharge"] - plot_df["charge"] - plot_df["Load"]
    )
    return plot_df


def plot_results(scenario: ScenarioManager, figure_kwargs: dict) -> List[go.Figure]:
    design_results = get_design_results(scenario)
    capacity = design_results["capacity"]
    power = design_results["power"]

    fig = make_subplots(
        rows=3,
        cols=1,
        subplot_titles=[
            "Storage level",
            "System dispatch hourly",
            "System dispatch monthly",
        ],
    )

    fig.update_layout(
        title=f"{scenario.inputs.name} Storage dispatch. Power {round(power,0)} capacity {round(capacity,0)}",
        **figure_kwargs,
    )

    operational_results = get_full_operation_data(scenario)
    storage_level_params = ["charge", "discharge", "storagelevel"]
    line_plot = px.line(operational_results[storage_level_params])
    line_plot_traces = [t for t in line_plot.data]
    for trace in line_plot_traces:
        fig.add_trace(trace, row=1, col=1)

    operational_results["net charge"] = -operational_results["charge"]
    generation_params = ["net charge", "discharge", "Solar", "Wind"]
    generation_areaplot = px.area(
        operational_results[generation_params],
        title="Generation minus storage charging",
    )
    generation_areaplot_traces = [t for t in generation_areaplot.data]
    for trace in generation_areaplot_traces:
        fig.add_trace(trace, row=2, col=1)

    genration_monthly_areaplot = px.area(
        operational_results[generation_params].resample("1m").mean(),
        title="Monthly generation and storage averages",
    )
    generation_monthly_areaplot_traces = [t for t in genration_monthly_areaplot.data]
    for trace in generation_monthly_areaplot_traces:
        fig.add_trace(trace, row=3, col=1)

    return fig
