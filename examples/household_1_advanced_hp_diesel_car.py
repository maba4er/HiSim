"""  Household example with advanced heat pump and diesel car. """

# clean

from typing import List, Optional, Any
from os import listdir
from pathlib import Path
from dataclasses import dataclass
from dataclasses_json import dataclass_json
from utspclient.helpers.lpgdata import (
    ChargingStationSets,
    Households,
    TransportationDeviceSets,
    TravelRouteSets,
)
from utspclient.helpers.lpgpythonbindings import JsonReference

from hisim.simulator import SimulationParameters
from hisim.components import loadprofilegenerator_utsp_connector
from hisim.components import weather
from hisim.components import advanced_heat_pump_hplib
from hisim.components import heat_distribution_system
from hisim.components import building
from hisim.components import simple_hot_water_storage
from hisim.components import generic_car
from hisim.components import generic_heat_pump_modular
from hisim.components import controller_l1_heatpump
from hisim.components import generic_hot_water_storage_modular
from hisim.components import sumbuilder
from hisim.components.configuration import HouseholdWarmWaterDemandConfig
from hisim import utils
from hisim import log

__authors__ = "Markus Blasberg"
__copyright__ = "Copyright 2023, FZJ-IEK-3"
__credits__ = ["Noah Pflugradt"]
__license__ = "MIT"
__version__ = "1.0"
__maintainer__ = "Markus Blasberg"
__status__ = "development"


# Todo: adopt Config-Class according to needs
@dataclass_json
@dataclass
class HouseholdAdvancedHPDieselCarConfig:

    """Configuration for with advanced heat pump and diesel car."""

    # pv_size: float
    building_type: str
    household_type: JsonReference
    lpg_url: str
    result_path: str
    travel_route_set: JsonReference
    simulation_parameters: SimulationParameters
    api_key: str
    transportation_device_set: JsonReference
    charging_station_set: JsonReference
    # pv_azimuth: float
    # tilt: float
    # pv_power: float
    # total_base_area_in_m2: float
    consumption: float
    building_config: building.BuildingConfig.get_config_classname
    hdscontroller_config: heat_distribution_system.HeatDistributionControllerConfig.get_config_classname
    hds_config: heat_distribution_system.HeatDistributionConfig.get_config_classname
    hp_controller_config: advanced_heat_pump_hplib.HeatPumpHplibControllerL1Config.get_config_classname
    hp_config: advanced_heat_pump_hplib.HeatPumpHplibConfig.get_config_classname
    simple_heat_water_storage_config: simple_hot_water_storage.SimpleHotWaterStorageConfig.get_config_classname
    dhw_heatpump_config: generic_heat_pump_modular.HeatPumpConfig.get_config_classname
    dhw_heatpump_controller_config: controller_l1_heatpump.L1HeatPumpConfig.get_config_classname
    # dhw_storage_config: generic_hot_water_storage_modular.StorageConfig.get_config_classname

    @classmethod
    def get_default(cls):
        """Get default HouseholdAdvancedHPDieselCarConfig."""

        return HouseholdAdvancedHPDieselCarConfig(
            # pv_size=5,
            building_type="blub",
            household_type=Households.CHR01_Couple_both_at_Work,
            lpg_url="http://134.94.131.167:443/api/v1/profilerequest",
            api_key="OrjpZY93BcNWw8lKaMp0BEchbCc",
            simulation_parameters=SimulationParameters.one_day_only(2022),
            result_path="mypath",
            travel_route_set=TravelRouteSets.Travel_Route_Set_for_10km_Commuting_Distance,
            transportation_device_set=TransportationDeviceSets.Bus_and_one_30_km_h_Car,
            charging_station_set=ChargingStationSets.Charging_At_Home_with_11_kW,
            # pv_azimuth=180,
            # tilt=30,
            # pv_power=10000,
            # total_base_area_in_m2=121.2,
            consumption=0.0,
            building_config=building.BuildingConfig.get_default_german_single_family_home(),
            hdscontroller_config=(
                heat_distribution_system.HeatDistributionControllerConfig.get_default_heat_distribution_controller_config()
            ),
            hds_config=(
                heat_distribution_system.HeatDistributionConfig.get_default_heatdistributionsystem_config()
            ),
            hp_controller_config=advanced_heat_pump_hplib.HeatPumpHplibControllerL1Config.get_default_generic_heat_pump_controller_config(),
            hp_config=advanced_heat_pump_hplib.HeatPumpHplibConfig.get_default_generic_advanced_hp_lib(),
            simple_heat_water_storage_config=(
                simple_hot_water_storage.SimpleHotWaterStorageConfig.get_default_simplehotwaterstorage_config()
            ),
            dhw_heatpump_config=(
                generic_heat_pump_modular.HeatPumpConfig.get_default_config_waterheating()
            ),
            dhw_heatpump_controller_config=controller_l1_heatpump.L1HeatPumpConfig.get_default_config_heat_source_controller_dhw(
                name="DHWHeatpumpController"
            ),
            # dhw_storage_config=(
            #     generic_hot_water_storage_modular.StorageConfig.get_default_config_boiler()
            # ),
        )


def household_advanced_hp_diesel_car(
    my_sim: Any, my_simulation_parameters: Optional[SimulationParameters] = None
) -> None:  # noqa: too-many-statements
    """example with advanced hp and diesel car.

    This setup function emulates a household with some basic components. Here the residents have their
    electricity and heating needs covered by a the advanced heat pump.

    - Simulation Parameters
    - Components
        - Occupancy (Residents' Demands)
        - Weather
        - Building
        - Electricity Base Load
        - Advanced Heat Pump HPlib
        - Advanced Heat Pump HPlib Controller
        - Heat Distribution System
        - Heat Distribution System Controller
        - Simple Hot Water Storage

        - DHW (Heatpump, Heatpumpcontroller, Storage; copied from modular_example)
        - Car (Diesel)
    """
    # Todo: change config with systemConfigBase.json for all components similar to modular_example
    config_filename = "reference_household_config.json"

    my_config: HouseholdAdvancedHPDieselCarConfig
    if Path(config_filename).is_file():
        with open(config_filename, encoding="utf8") as system_config_file:
            my_config = HouseholdAdvancedHPDieselCarConfig.from_json(system_config_file.read())  # type: ignore
        log.information(f"Read system config from {config_filename}")
    else:
        my_config = HouseholdAdvancedHPDieselCarConfig.get_default()

        my_config_json = my_config.to_json()
        with open(config_filename, "w", encoding="utf8") as system_config_file:
            system_config_file.write(my_config_json)

    # =================================================================================================================================
    # Set System Parameters

    # Set Simulation Parameters
    year = 2021
    seconds_per_timestep = 60

    # =================================================================================================================================
    # Build Components

    # Build Simulation Parameters
    if my_simulation_parameters is None:
        my_simulation_parameters = SimulationParameters.full_year_all_options(
            year=year, seconds_per_timestep=seconds_per_timestep
        )
    my_sim.set_simulation_parameters(my_simulation_parameters)

    # Build Occupancy
    my_occupancy_config = loadprofilegenerator_utsp_connector.UtspLpgConnectorConfig(
        url=my_config.lpg_url,
        api_key=my_config.api_key,
        household=my_config.household_type,
        result_path=my_config.result_path,
        travel_route_set=my_config.travel_route_set,
        transportation_device_set=my_config.transportation_device_set,
        charging_station_set=my_config.charging_station_set,
        name="UTSP Connector",
        consumption=my_config.consumption,
    )
    my_occupancy = loadprofilegenerator_utsp_connector.UtspLpgConnector(
        config=my_occupancy_config, my_simulation_parameters=my_simulation_parameters
    )

    # Build Weather
    my_weather = weather.Weather(
        config=weather.WeatherConfig.get_default(weather.LocationEnum.Aachen),
        my_simulation_parameters=my_simulation_parameters,
    )

    # Build Building
    my_building = building.Building(
        config=my_config.building_config,
        my_simulation_parameters=my_simulation_parameters,
    )

    # Build heat Distribution System Controller
    my_heat_distribution_controller = (
        heat_distribution_system.HeatDistributionController(
            config=my_config.hdscontroller_config,
            my_simulation_parameters=my_simulation_parameters,
        )
    )

    # Build Heat Distribution System
    my_heat_distribution = heat_distribution_system.HeatDistribution(
        my_simulation_parameters=my_simulation_parameters, config=my_config.hds_config
    )

    # Build Heat Pump Controller
    my_heat_pump_controller_config = my_config.hp_controller_config
    my_heat_pump_controller_config.name = "HeatPumpHplibController"

    my_heat_pump_controller = advanced_heat_pump_hplib.HeatPumpHplibController(
        config=my_heat_pump_controller_config,
        my_simulation_parameters=my_simulation_parameters,
    )

    # Build Heat Pump
    my_heat_pump_config = my_config.hp_config
    my_heat_pump_config.name = "HeatPumpHPLib"

    my_heat_pump = advanced_heat_pump_hplib.HeatPumpHplib(
        config=my_heat_pump_config,
        my_simulation_parameters=my_simulation_parameters,
    )

    # Build Heat Water Storage
    my_simple_hot_water_storage = simple_hot_water_storage.SimpleHotWaterStorage(
        config=my_config.simple_heat_water_storage_config,
        my_simulation_parameters=my_simulation_parameters,
    )

    # Build DHW
    my_dhw_heatpump_config = my_config.dhw_heatpump_config
    my_dhw_heatpump_config.power_th = (
        my_occupancy.max_hot_water_demand
        * (4180 / 3600)
        * 0.5
        * (3600 / my_simulation_parameters.seconds_per_timestep)
        * (
            HouseholdWarmWaterDemandConfig.ww_temperature_demand
            - HouseholdWarmWaterDemandConfig.freshwater_temperature
        )
    )

    my_dhw_heatpump_controller_config = my_config.dhw_heatpump_controller_config

    dhw_storage_config = (
        generic_hot_water_storage_modular.StorageConfig.get_default_config_boiler()
    )
    dhw_storage_config.name = "DHWStorage"

    dhw_storage_config.compute_default_cycle(
        temperature_difference_in_kelvin=my_dhw_heatpump_controller_config.t_max_heating_in_celsius
        - my_dhw_heatpump_controller_config.t_min_heating_in_celsius
    )

    my_domnestic_hot_water_storage = generic_hot_water_storage_modular.HotWaterStorage(
        my_simulation_parameters=my_simulation_parameters, config=dhw_storage_config
    )

    my_domnestic_hot_water_heatpump_controller = (
        controller_l1_heatpump.L1HeatPumpController(
            my_simulation_parameters=my_simulation_parameters,
            config=my_dhw_heatpump_controller_config,
        )
    )

    my_domnestic_hot_water_heatpump = generic_heat_pump_modular.ModularHeatPump(
        config=my_dhw_heatpump_config, my_simulation_parameters=my_simulation_parameters
    )

    # Build Diesel-Car
    # get names of all available cars
    # Todo: check if multiple cars are necesary
    filepaths = listdir(utils.HISIMPATH["utsp_results"])
    filepaths_location = [elem for elem in filepaths if "CarLocation." in elem]
    names = [elem.partition(",")[0].partition(".")[2] for elem in filepaths_location]

    my_car_config = generic_car.CarConfig.get_default_diesel_config()
    my_car_config.name = "DieselCar"

    # create all cars
    my_cars: List[generic_car.Car] = []
    for car in names:
        my_car_config.name = car
        my_cars.append(
            generic_car.Car(
                my_simulation_parameters=my_simulation_parameters,
                config=my_car_config,
                occupancy_config=my_occupancy_config,
            )
        )

    # Build Base Electricity Load Profile
    my_base_electricity_load_profile = sumbuilder.ElectricityGrid(
        config=sumbuilder.ElectricityGridConfig(
            name="ElectrcityGrid_BaseLoad",
            grid=[
                my_occupancy,
                "Sum",
                my_domnestic_hot_water_heatpump,
                "Sum",
                my_heat_pump,
            ],
            signal=None,
        ),
        my_simulation_parameters=my_simulation_parameters,
    )

    # =================================================================================================================================
    # Connect Component Inputs with Outputs

    my_building.connect_only_predefined_connections(my_weather, my_occupancy)
    my_building.connect_input(
        my_building.ThermalPowerDelivered,
        my_heat_distribution.component_name,
        my_heat_distribution.ThermalPowerDelivered,
    )

    my_heat_pump_controller.connect_only_predefined_connections(
        my_weather, my_simple_hot_water_storage, my_heat_distribution_controller
    )

    my_heat_pump.connect_only_predefined_connections(
        my_heat_pump_controller, my_weather, my_simple_hot_water_storage
    )

    my_heat_distribution_controller.connect_only_predefined_connections(
        my_weather, my_building, my_simple_hot_water_storage
    )

    my_heat_distribution.connect_only_predefined_connections(
        my_heat_distribution_controller, my_building, my_simple_hot_water_storage
    )

    my_simple_hot_water_storage.connect_input(
        my_simple_hot_water_storage.WaterTemperatureFromHeatDistributionSystem,
        my_heat_distribution.component_name,
        my_heat_distribution.WaterTemperatureOutput,
    )

    my_simple_hot_water_storage.connect_input(
        my_simple_hot_water_storage.WaterTemperatureFromHeatGenerator,
        my_heat_pump.component_name,
        my_heat_pump.TemperatureOutput,
    )

    my_simple_hot_water_storage.connect_input(
        my_simple_hot_water_storage.WaterMassFlowRateFromHeatGenerator,
        my_heat_pump.component_name,
        my_heat_pump.MassFlowOutput,
    )

    # connect DHW
    my_domnestic_hot_water_storage.connect_only_predefined_connections(
        my_occupancy, my_domnestic_hot_water_heatpump
    )

    my_domnestic_hot_water_heatpump_controller.connect_only_predefined_connections(
        my_domnestic_hot_water_storage
    )

    my_domnestic_hot_water_heatpump.connect_only_predefined_connections(
        my_weather, my_domnestic_hot_water_heatpump_controller
    )

    # =================================================================================================================================
    # Add Components to Simulation Parameters
    my_sim.add_component(my_occupancy)
    my_sim.add_component(my_weather)
    my_sim.add_component(my_building)
    my_sim.add_component(my_heat_pump)
    my_sim.add_component(my_heat_pump_controller)
    my_sim.add_component(my_heat_distribution)
    my_sim.add_component(my_heat_distribution_controller)
    my_sim.add_component(my_simple_hot_water_storage)
    my_sim.add_component(my_domnestic_hot_water_storage)
    my_sim.add_component(my_domnestic_hot_water_heatpump_controller)
    my_sim.add_component(my_domnestic_hot_water_heatpump)
    my_sim.add_component(my_base_electricity_load_profile)
    for my_car in my_cars:
        my_sim.add_component(my_car)
