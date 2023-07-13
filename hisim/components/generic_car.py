"""Simple Car (LPG connected) and configuration.
Evaluates diesel or electricity consumption based on driven kilometers and processes Car Location for charging stations."""

# -*- coding: utf-8 -*-
from typing import List, Any, Tuple
from os import listdir, path
from dataclasses import dataclass
import datetime as dt
import json
from dataclasses_json import dataclass_json

import pandas as pd
import numpy as np

from hisim import component as cp
from hisim import loadtypes as lt
from hisim.simulationparameters import SimulationParameters
from hisim import utils

__authors__ = "Johanna Ganglbauer"
__copyright__ = "Copyright 2021, the House Infrastructure Project"
__credits__ = ["Noah Pflugradt"]
__license__ = ""
__version__ = ""
__maintainer__ = "Johanna Ganglbauer"
__email__ = "johanna.ganglbauer@4wardenergy.at"
__status__ = "development"


@dataclass_json
@dataclass
class CarConfig(cp.ConfigBase):

    """Definition of configuration of Car."""

    #: name of the car
    name: str
    #: priority of the component in hierachy: the higher the number the lower the priority
    source_weight: int
    #: type of fuel, either Electricity or Diesel
    fuel: lt.LoadTypes
    #: consumption per kilometer driven, either in kWh/km or l/km
    consumption_per_km: float
    #: CO2 footprint of investment in kg
    co2_footprint: float
    #: cost for investment in Euro
    cost: float
    #: lifetime of car in years
    lifetime: float
    #: consumption of the car in kWh or l
    consumption: float

    @classmethod
    def get_main_classname(cls):
        """Returns the full class name of the base class."""
        return Car.get_full_classname()

    @classmethod
    def get_default_diesel_config(cls) -> Any:
        """Defines default configuration for diesel vehicle."""
        config = CarConfig(
            name="Car",
            source_weight=1,
            fuel=lt.LoadTypes.DIESEL,
            consumption_per_km=0.06,
            co2_footprint=9139.3,
            cost=32035.0,
            lifetime=18,
            consumption=0,
        )
        return config

    @classmethod
    def get_default_ev_config(cls) -> Any:
        """Defines default configuration for electric vehicle."""
        config = CarConfig(
            name="Car",
            source_weight=1,
            fuel=lt.LoadTypes.ELECTRICITY,
            consumption_per_km=0.15,
            co2_footprint=8899.4,
            cost=44498.0,
            lifetime=18,
            consumption=0,
        )
        return config


def most_frequent(input_list: List) -> Any:
    """Returns most frequent value - needed for down sampling Location information from 1 minute resoultion to lower."""
    counter = 0
    num = input_list[0]

    for i in input_list:
        curr_frequency = input_list.count(i)
        if curr_frequency > counter:
            counter = curr_frequency
            num = i
    return num


class Car(cp.Component):

    """Simulates car with constant consumption. Car usage (driven kilometers and state) orginate from LPG."""

    # Outputs
    FuelConsumption = "FuelConsumption"
    ElectricityOutput = "ElectricityOutput"
    CarLocation = "CarLocation"

    @staticmethod
    def get_cost_capex(config: CarConfig) -> Tuple[float, float, float]:
        """Returns investment cost, CO2 emissions and lifetime."""
        return config.cost, config.co2_footprint, config.lifetime

    def __init__(
        self,
        my_simulation_parameters: SimulationParameters,
        config: CarConfig,
        occupancy_config: Any,
    ) -> None:
        """Initializes Car."""
        super().__init__(
            name=config.name + "_w" + str(config.source_weight),
            my_simulation_parameters=my_simulation_parameters,
            my_config=config,
        )
        self.build(config=config, occupancy_config=occupancy_config)

        if self.config.fuel == lt.LoadTypes.ELECTRICITY:
            self.electricity_output: cp.ComponentOutput = self.add_output(
                object_name=self.component_name,
                field_name=self.ElectricityOutput,
                load_type=lt.LoadTypes.ELECTRICITY,
                unit=lt.Units.WATT,
                postprocessing_flag=[lt.ComponentType.CAR],
                output_description="Electricity Consumption of the car while driving. [W]",
            )
            self.car_location_output: cp.ComponentOutput = self.add_output(
                object_name=self.component_name,
                field_name=self.CarLocation,
                load_type=lt.LoadTypes.ANY,
                unit=lt.Units.ANY,
                output_description="Location of the car as integer.",
            )
        elif self.config.fuel == lt.LoadTypes.DIESEL:
            self.fuel_consumption: cp.ComponentOutput = self.add_output(
                object_name=self.component_name,
                field_name=self.FuelConsumption,
                load_type=lt.LoadTypes.DIESEL,
                unit=lt.Units.LITER,
                postprocessing_flag=[
                    lt.InandOutputType.FUEL_CONSUMPTION,
                    lt.LoadTypes.DIESEL,
                    lt.ComponentType.CAR,
                ],
                output_description="Diesel Consumption of the car while driving [l].",
            )

    def i_save_state(self) -> None:
        """Saves actual state."""
        pass

    def i_restore_state(self) -> None:
        """Restores previous state."""
        pass

    def i_doublecheck(self, timestep: int, stsv: cp.SingleTimeStepValues) -> None:
        """Checks statements."""
        pass

    def i_prepare_simulation(self) -> None:
        """Prepares the simulation."""
        pass

    def i_simulate(
        self, timestep: int, stsv: cp.SingleTimeStepValues, force_convergence: bool
    ) -> None:
        """Returns consumption and location of car in each timestep."""

        if self.config.fuel == lt.LoadTypes.ELECTRICITY:
            watt_used = (
                self.meters_driven[timestep]
                * self.config.consumption_per_km
                * (3600 / self.my_simulation_parameters.seconds_per_timestep)
            )  # conversion Wh to W
            stsv.set_output_value(self.electricity_output, watt_used)
            stsv.set_output_value(self.car_location_output, self.car_location[timestep])

        # if not already running: check if activation makes sense
        elif self.config.fuel == lt.LoadTypes.DIESEL:
            liters_used = (
                self.meters_driven[timestep] * self.config.consumption_per_km * 1e-3
            )  # conversion meter to kilometer
            stsv.set_output_value(self.fuel_consumption, liters_used)

    def get_cost_opex(self, all_outputs: List, postprocessing_results: pd.DataFrame, ) -> Tuple[float, float]:
        for index, output in enumerate(all_outputs):
            if output.component_name == self.config.name + "_w" + str(self.config.source_weight):
                if output.unit == lt.Units.LITER:
                    self.config.consumption = round(sum(postprocessing_results.iloc[:, index]), 1)
                    # be careful, this is hard coded and should be placed somewhere else!
                    co2_per_unit = 2.6
                    euro_per_unit = 1.6
                elif output.unit == lt.Units.WATT:
                    co2_per_unit = 0.4
                    euro_per_unit = 0.25
                    self.config.consumption = round(sum(postprocessing_results.iloc[:, index]) * self.my_simulation_parameters.seconds_per_timestep / 3.6e6, 1)

        return self.config.consumption * euro_per_unit, self.config.consumption * co2_per_unit

    def build(self, config: CarConfig, occupancy_config: Any) -> None:
        """Loads necesary data and saves config to class."""
        self.config = config
        self.car_location = []
        self.meters_driven = []

        location_translator = {
            "School": 0,
            "Event Location": 0,
            "Shopping": 0,
            None: 0,
            "Home": 1,
            "Workplace": 2,
        }

        # check if caching is possible
        file_exists, cache_filepath = utils.get_cache_file(
            component_key=self.component_name,
            parameter_class=occupancy_config,
            my_simulation_parameters=self.my_simulation_parameters,
        )
        if file_exists:
            # load from cache
            dataframe = pd.read_csv(
                cache_filepath, sep=",", decimal=".", encoding="cp1252"
            )
            self.car_location = dataframe["car_location"].tolist()
            self.meters_driven = dataframe["meters_driven"].tolist()
        else:
            # load car data from LPG output
            filepaths = listdir(utils.HISIMPATH["utsp_results"])
            filepath_location = [
                elem for elem in filepaths if "CarLocation." + self.config.name in elem
            ][0]
            filepath_meters_driven = [
                elem for elem in filepaths if "DrivingDistance." + self.config.name in elem
            ][0]
            with open(
                path.join(utils.HISIMPATH["utsp_results"], filepath_location),
                encoding="utf-8",
            ) as json_file:
                car_location = json.load(json_file)
            with open(
                path.join(utils.HISIMPATH["utsp_results"], filepath_meters_driven),
                encoding="utf-8",
            ) as json_file:
                meters_driven = json.load(json_file)

            # compare time resolution of LPG to time resolution of hisim
            time_resolution_original = dt.datetime.strptime(
                car_location["TimeResolution"], "%H:%M:%S"
            )
            seconds_per_timestep_original = (
                time_resolution_original.hour * 3600
                + time_resolution_original.minute * 60
                + time_resolution_original.second
            )
            steps_ratio = int(
                self.my_simulation_parameters.seconds_per_timestep
                / seconds_per_timestep_original
            )

            # extract values for location and distance of car
            car_location = car_location["Values"]
            meters_driven = meters_driven["Values"]

            # translate car location to integers (according to location_translator)
            car_location = [location_translator[elem] for elem in car_location]

            # sum / extract most common value from data to match hisim time resolution
            for i in range(int(len(meters_driven) / steps_ratio)):
                self.meters_driven.append(
                    sum(meters_driven[i * steps_ratio: (i + 1) * steps_ratio])
                )  # sum
                location_list = car_location[
                    i * steps_ratio: (i + 1) * steps_ratio
                ]  # extract list
                occurence_count = most_frequent(
                    input_list=location_list
                )  # extract most common
                self.car_location.append(occurence_count)

            # save data in cache
            data = np.transpose([self.car_location, self.meters_driven])
            database = pd.DataFrame(data, columns=["car_location", "meters_driven"])

            database.to_csv(cache_filepath)
            del data
            del database

    def write_to_report(self) -> List[str]:
        """Writes Car values to report."""
        return self.config.get_string_dict()
