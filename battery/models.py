import datetime
from dataclasses import dataclass
from typing import Dict, List

import pandas as pd
from pulp import *


class Renewables:
    def __init__(
        self,
        names: List[str],
        capacities: Dict[str, float],
        profiles: pd.DataFrame,  # TODO - enforce structure with pandera
    ) -> None:
        self.names = names
        self.capacities = capacities
        self.profiles = profiles
        self.generation = self.calculate_generation(names, capacities, profiles)
        pass

    @staticmethod
    def calculate_generation(
        names: List[str],
        capacities: Dict[str, float],
        profiles: pd.DataFrame,  # TODO - enforce structure with pandera
    ) -> pd.DataFrame:
        assert set(names) == set(capacities.keys())
        assert "Total" not in names
        generation = pd.DataFrame()
        for name, capacity in capacities.items():
            print(name, capacity)
            generation[name] = profiles[name] * capacity

        generation["Total"] = generation.sum(axis=1)
        return generation


class Load:
    def __init__(
        self,
        capacity: float,
        profile: pd.Series,  # TODO - enforce structure with pandera
    ) -> None:

        self.capacity = capacity
        self.profile = profile
        self.load = capacity * profile
        pass


@dataclass
class Storage:
    efficiency: float  # can a range be set with dataclass, or is this then a job for pydantic classes?
    minimum_duration: float
    capex_power: float
    capex_capacity: float


@dataclass
class ScenarioInputs:
    name: str
    start_date: datetime.datetime
    time_index: List[int]
    renewables: Renewables
    load: Load
    storage: Storage


@dataclass
class ModelVarsScalar:
    capacity: LpVariable
    power: LpVariable


@dataclass
class ModelVarsTimeDependent:
    level: Dict[int, LpVariable]
    charge: Dict[int, LpVariable]
    discharge: Dict[int, LpVariable]


@dataclass
class ModelVars:
    scalar: ModelVarsScalar
    time: ModelVarsTimeDependent


class ScenarioManager:
    vars: ModelVars
    lpmodel: LpProblem

    def __init__(self, inputs: ScenarioInputs) -> None:
        self.inputs = inputs
        self.name = self.inputs.name
        self.solved_status = False

        self.setup_linear_problem()
        self.define_endogenous_variables()
        self.define_objective_function()
        self.define_constraints()

    def verify_inputs(self) -> None:
        assert (
            self.inputs.load.load.mean()
            < self.inputs.renewables.generation["Total"].mean()
        )  # there is more generation than demand
        assert (
            self.inputs.renewables.generation.isna().sum().sum() == 0
        )  # no nans in input data
        assert self.inputs.load.load.isna().sum() == 0  # no nans in input data

    def setup_linear_problem(self) -> None:
        self.lpmodel = LpProblem(name=self.inputs.name, sense=LpMinimize)

    def define_endogenous_variables(self) -> None:
        self.vars = ModelVars(
            scalar=ModelVarsScalar(
                capacity=LpVariable(name="capacity", lowBound=0),
                power=LpVariable(
                    name="power", lowBound=0
                ),  # todo calculate minimum power based on res profiles and load
            ),
            time=ModelVarsTimeDependent(
                level=LpVariable.dicts(
                    name="storagelevel", indices=self.inputs.time_index, lowBound=0
                ),
                charge=LpVariable.dicts(
                    name="charge", indices=self.inputs.time_index, lowBound=0
                ),
                discharge=LpVariable.dicts(
                    name="discharge", indices=self.inputs.time_index, lowBound=0
                ),
            ),
        )

    def define_objective_function(self) -> None:
        obj_func_capex_total = (
            self.vars.scalar.capacity * self.inputs.storage.capex_capacity
            + self.vars.scalar.power * self.inputs.storage.capex_power
        )
        self.lpmodel += obj_func_capex_total

    def define_constraints(self) -> None:
        self.lpmodel += (
            self.vars.scalar.capacity
            >= self.inputs.storage.minimum_duration * self.vars.scalar.power,
            "duration is greater than input minimum",
        )

        t_max = max(self.inputs.time_index)
        start_of_year_constraint = (
            self.vars.time.level[0]
            == self.vars.time.level[t_max]
            - self.vars.time.discharge[t_max]
            + self.inputs.storage.efficiency * self.vars.time.charge[t_max]
        )
        self.lpmodel += (
            start_of_year_constraint,
            f"storage level at start is determined by the end",
        )

        for t in self.inputs.time_index[:-1]:
            storage_level_constraint = (
                self.vars.time.level[t + 1]
                == self.vars.time.level[t]
                - self.vars.time.discharge[t]
                + self.inputs.storage.efficiency * self.vars.time.charge[t]
            )
            self.lpmodel += (
                storage_level_constraint,
                f"storage level is determined by charge and discharge, and efficiency (t={t})",
            )

            # Is this constraint necessary? The level variable has a lower bound of 0 already
            available_energy_constraint = (
                self.vars.time.level[t] >= self.vars.time.discharge[t]
            )
            self.lpmodel += (
                available_energy_constraint,
                f"cannot dispatch more than available energy (t={t})",
            )

        for t in self.inputs.time_index:
            self.lpmodel += (
                self.vars.time.charge[t] <= self.vars.scalar.power,
                f"storage charge is limited by power rating (t={t})",
            )
            self.lpmodel += (
                self.vars.time.discharge[t] <= self.vars.scalar.power,
                f"storage discharge is limited by power rating (t={t})",
            )
            self.lpmodel += (
                self.vars.time.level[t] <= self.vars.scalar.capacity,
                f"storage level cannot be higher then capacity (t={t})",
            )
            self.lpmodel += (
                self.inputs.renewables.generation["Total"][t]
                + self.vars.time.discharge[t]
                - self.vars.time.charge[t]
                >= self.inputs.load.load[t],
                f"load is supplied (t={t})",
            )

    def solve(self, **kwargs) -> None:
        self.lpmodel.solve(**kwargs)
        if self.lpmodel.status == 1:
            self.solved_status = True

    def verify_solve(self) -> None:
        if self.lpmodel.status != 1:
            raise Exception("Model has not solved")
