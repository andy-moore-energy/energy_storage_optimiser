# Find the optimal battery size for an industrial site

## Context
A consumer is targeting 100% self-reliance on solar and wind energy and wants to buy a battery to shift generation when it needs to be used.

The model find the cheapest size and duration for the battery (MW and MWh sizes) based on input costs, reneable supply, and demand.

The word "battery" is used throughout but refers to any given storage technology - this could be compressed air, hydrogen, or any other.

The target use case for this model, and therefore scenario design, is the compare the cost of different storages by researching and implementing different costs for the power (MW) and capacity (MWh) values.

## Usage
Two versions of the model are available, either built in-line, or object oriented.
The in-line code is stored run here: `battery/battery_solver_inplace.ipynb`
An implementation of the object-oriented version is here: `battery/battery_solver_modular.ipynb`

1. Select input renewables datasets
2. Select load amount
3. Choose cost for battery power and capacity
4. Run the model
5. Plot the results

Standardised results take this form per scenario:
![Alt text](https://github.com/abmoore92/energy_storage_optimiser/blob/main/docs/example_plot.png?raw=true "Example Results")

## Setup
Poetry is used as a package manager, the poetry.lock file contains information on which packages are required
https://python-poetry.org/docs/
Install using:
`poetry install`

## Limitations and Extensions
Cost
* Cost is currently capex only, this is a limited view as opex can differ between power and capacity components of a project.

Multi-year modelling
* The model currently looks at one timeseries, representing one typical year or operating period. In reality, multi-year variation plays an important effect, and should be considered. Currently this should be solved either by careful selection of the model year, or running multiple scenarios with different year inputs. A future version of the model should include multiple years into the simulation.

Multi-storage solutions
* Currently the model only considers 1 storage unit. It may be interesting to build 2 or more storages of different technologies to match short and longer duration demands for volatility management. A hybrid site may produce more efficient outcomes than using only one storage. Currently, the best way to solve this is to compare scenarios with different storages.

Excess renewables production has no value
* Excess renewables are in reality sold to the grid. The objective function for the model is simiplistic in that it targets self-reliance. A more interesting question is to find the economic sensitivity of % of self reliance. This would require including market prices for energy sold.

Scenario Management
* Data connectivity is currently manual, the user needs to download data from external sources and create their own connection. Results are also similarly not stored and managed.
* Data input should be connected to external sources that provide relevant data - such as https://data.open-power-system-data.org/time_series/.
* Sensitivity analysis of key metrics should be automated in the model run
* Results should be stored in a standardised structure and a simple dashboard built to enable scenario comparison.

## Licensing
Data from renewables.ninja is used in this example, which is under a non-commercial license. Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)# energy_storage_optimiser
