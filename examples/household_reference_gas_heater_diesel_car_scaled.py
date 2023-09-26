"""  Reference Household example with gas heater and diesel car. """

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

from hisim.simulator import SimulationParameters
from hisim.components import loadprofilegenerator_utsp_connector
from hisim.components import weather
from hisim.components import generic_gas_heater
from hisim.components import controller_l1_generic_gas_heater
from hisim.components import heat_distribution_system
from hisim.components import building
from hisim.components import simple_hot_water_storage
from hisim.components import generic_car
from hisim.components import generic_heat_pump_modular
from hisim.components import controller_l1_heatpump
from hisim.components import generic_hot_water_storage_modular
from hisim.components import electricity_meter
from hisim.components.configuration import HouseholdWarmWaterDemandConfig
from hisim.sim_repository_singleton import SingletonSimRepository, SingletonDictKeyEnum
from hisim import utils
from hisim import loadtypes as lt
from hisim import log
from examples.modular_example import cleanup_old_lpg_requests

__authors__ = "Markus Blasberg"
__copyright__ = "Copyright 2023, FZJ-IEK-3"
__credits__ = ["Noah Pflugradt"]
__license__ = "MIT"
__version__ = "1.0"
__maintainer__ = "Markus Blasberg"
__status__ = "development"


@dataclass_json
@dataclass
class ReferenceHouseholdScaledConfig:

    """Configuration for ReferenceHosuehold."""

    building_type: str
    number_of_apartments: int
    # simulation_parameters: SimulationParameters
    # total_base_area_in_m2: float
    occupancy_config: loadprofilegenerator_utsp_connector.UtspLpgConnectorConfig
    building_config: building.BuildingConfig
    hds_controller_config: heat_distribution_system.HeatDistributionControllerConfig
    hds_config: heat_distribution_system.HeatDistributionConfig
    gasheater_controller_config: controller_l1_generic_gas_heater.GenericGasHeaterControllerL1Config
    gasheater_config: generic_gas_heater.GenericGasHeaterConfig
    simple_hot_water_storage_config: simple_hot_water_storage.SimpleHotWaterStorageConfig
    dhw_heatpump_config: generic_heat_pump_modular.HeatPumpConfig
    dhw_heatpump_controller_config: controller_l1_heatpump.L1HeatPumpConfig
    dhw_storage_config: generic_hot_water_storage_modular.StorageConfig
    car_config: generic_car.CarConfig
    electricity_meter_config: electricity_meter.ElectricityMeterConfig

    @classmethod
    def get_default(cls):
        """Get default HouseholdPVConfig."""

        # set number of apartments (mandatory for dhw storage config)
        number_of_apartments = 1
        SingletonSimRepository().set_entry(
            key=SingletonDictKeyEnum.NUMBEROFAPARTMENTS, entry=number_of_apartments
        )
        heating_reference_temperature_in_celsius: float = -7
        set_heating_threshold_outside_temperature_in_celsius: float = 16.0

        # Todo: residence-information is calculated manually for now. find a way to get this from building component
        my_residence_information = building.BuildingInformation(
            building_conditioned_floor_area_in_m2=121.2,
            building_rooftop_area_in_m2=168.9,
            building_heating_load_in_watt=8000,
            building_number_of_apartments=1.0,
            building_number_of_storeys=1.0,
        )

        household_config = ReferenceHouseholdScaledConfig(
            building_type="blub",
            number_of_apartments=number_of_apartments,
            # simulation_parameters=SimulationParameters.one_day_only(2022),
            # total_base_area_in_m2=121.2,
            occupancy_config=loadprofilegenerator_utsp_connector.UtspLpgConnectorConfig(
                url="http://134.94.131.167:443/api/v1/profilerequest",
                api_key="OrjpZY93BcNWw8lKaMp0BEchbCc",
                household=Households.CHR01_Couple_both_at_Work,
                result_path=utils.HISIMPATH["results"],
                travel_route_set=TravelRouteSets.Travel_Route_Set_for_10km_Commuting_Distance,
                transportation_device_set=TransportationDeviceSets.Bus_and_one_30_km_h_Car,
                charging_station_set=ChargingStationSets.Charging_At_Home_with_11_kW,
                name="UTSPConnector",
                consumption=0.0,
                profile_with_washing_machine_and_dishwasher=True,
            ),
            building_config=building.BuildingConfig.get_default_german_single_family_home(),
            hds_controller_config=(
                heat_distribution_system.HeatDistributionControllerConfig.get_default_heat_distribution_controller_config()
            ),
            hds_config=(
                heat_distribution_system.HeatDistributionConfig.get_default_heatdistributionsystem_config()
            ),
            gasheater_controller_config=(
                controller_l1_generic_gas_heater.GenericGasHeaterControllerL1Config.get_scaled_generic_gas_heater_controller_config(
                    heating_load_of_building_in_watt=my_residence_information.building_heating_load_in_watt
                )
            ),
            gasheater_config=generic_gas_heater.GenericGasHeaterConfig.get_scaled_gasheater_config(
                heating_load_of_building_in_watt=my_residence_information.building_heating_load_in_watt
            ),
            simple_hot_water_storage_config=(
                simple_hot_water_storage.SimpleHotWaterStorageConfig.get_scaled_hot_water_storage(
                    heating_load_of_building_in_watt=my_residence_information.building_heating_load_in_watt)
            ),
            dhw_heatpump_config=(
                generic_heat_pump_modular.HeatPumpConfig.get_scaled_waterheating()
            ),
            dhw_heatpump_controller_config=controller_l1_heatpump.L1HeatPumpConfig.get_default_config_heat_source_controller_dhw(
                name="DHWHeatpumpController"
            ),
            dhw_storage_config=(
                generic_hot_water_storage_modular.StorageConfig.get_default_config_for_boiler_scaled()
            ),
            car_config=generic_car.CarConfig.get_default_diesel_config(),
            electricity_meter_config=electricity_meter.ElectricityMeterConfig.get_electricity_meter_default_config(),
        )

        # set same heating threshold
        household_config.hds_controller_config.set_heating_threshold_outside_temperature_in_celsius = (
            set_heating_threshold_outside_temperature_in_celsius
        )
        household_config.gasheater_controller_config.set_heating_threshold_outside_temperature_in_celsius = (
            set_heating_threshold_outside_temperature_in_celsius
        )

        # set same heating reference temperature
        household_config.hds_controller_config.heating_reference_temperature_in_celsius = (
            heating_reference_temperature_in_celsius
        )
        household_config.building_config.heating_reference_temperature_in_celsius = (
            heating_reference_temperature_in_celsius
        )

        # set dhw storage volume, because default(volume = 230) leads to an error
        household_config.dhw_storage_config.volume = 250

        return household_config


def household_reference_gas_heater_diesel_car_scaled(
    my_sim: Any, my_simulation_parameters: Optional[SimulationParameters] = None
) -> None:  # noqa: too-many-statements
    """Reference example.

    This setup function emulates a household with some basic components. Here the residents have their
    electricity and heating needs covered by a generic gas heater.

    - Simulation Parameters
    - Components
        - Occupancy (Residents' Demands)
        - Weather
        - Building
        - Electricity Meter
        - Gas Heater
        - Gas Heater Controller
        - Heat Distribution System
        - Heat Distribution System Controller
        - Simple Hot Water Storage

        - DHW (Heatpump, Heatpumpcontroller, Storage; copied from modular_example)
        - Car (Diesel)
    """

    # cleanup old lpg requests, mandatory to change number of cars
    # Todo: change cleanup-function if result_path from occupancy is not utils.HISIMPATH["results"]
    if Path(utils.HISIMPATH["utsp_results"]).exists():
        cleanup_old_lpg_requests()

    config_filename = "household_reference_gas_heater_diesel_car_scaled.json"

    my_config: ReferenceHouseholdScaledConfig
    if Path(config_filename).is_file():
        with open(config_filename, encoding="utf8") as system_config_file:
            my_config = ReferenceHouseholdScaledConfig.from_json(system_config_file.read())  # type: ignore
        log.information(f"Read system config from {config_filename}")
    else:
        my_config = ReferenceHouseholdScaledConfig.get_default()

        # Todo: save file leads to use of file in next run. File was just produced to check how it looks like
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

    # Build heat Distribution System Controller
    my_heat_distribution_controller = (
        heat_distribution_system.HeatDistributionController(
            config=my_config.hds_controller_config,
            my_simulation_parameters=my_simulation_parameters,
        )
    )

    # Build Occupancy
    my_occupancy_config = my_config.occupancy_config
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

    # Build Gas Heater Controller
    my_gasheater_controller = (
        controller_l1_generic_gas_heater.GenericGasHeaterControllerL1(
            my_simulation_parameters=my_simulation_parameters,
            config=my_config.gasheater_controller_config,
        )
    )

    # Build Gasheater
    my_gasheater = generic_gas_heater.GasHeater(
        config=my_config.gasheater_config,
        my_simulation_parameters=my_simulation_parameters,
    )

    # Build Heat Distribution System
    my_heat_distribution = heat_distribution_system.HeatDistribution(
        my_simulation_parameters=my_simulation_parameters, config=my_config.hds_config
    )

    # Build Heat Water Storage
    my_simple_hot_water_storage = simple_hot_water_storage.SimpleHotWaterStorage(
        config=my_config.simple_hot_water_storage_config,
        my_simulation_parameters=my_simulation_parameters,
    )

    # Build DHW
    my_dhw_heatpump_config = my_config.dhw_heatpump_config
    my_dhw_heatpump_controller_config = my_config.dhw_heatpump_controller_config

    my_dhw_storage_config = my_config.dhw_storage_config
    my_dhw_storage_config.name = "DHWStorage"
    my_dhw_storage_config.compute_default_cycle(
        temperature_difference_in_kelvin=my_dhw_heatpump_controller_config.t_max_heating_in_celsius
        - my_dhw_heatpump_controller_config.t_min_heating_in_celsius
    )

    my_domnestic_hot_water_storage = generic_hot_water_storage_modular.HotWaterStorage(
        my_simulation_parameters=my_simulation_parameters, config=my_dhw_storage_config
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

    # Build Diesel-Car(s)
    # get names of all available cars
    filepaths = listdir(utils.HISIMPATH["utsp_results"])
    filepaths_location = [elem for elem in filepaths if "CarLocation." in elem]
    names = [elem.partition(",")[0].partition(".")[2] for elem in filepaths_location]

    my_car_config = my_config.car_config
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

    # Build Electricity Meter
    my_electricity_meter = electricity_meter.ElectricityMeter(
        my_simulation_parameters=my_simulation_parameters,
        config=my_config.electricity_meter_config,
    )

    # =================================================================================================================================
    # Connect Component Inputs with Outputs

    my_building.connect_only_predefined_connections(my_weather, my_occupancy)
    my_building.connect_input(
        my_building.ThermalPowerDelivered,
        my_heat_distribution.component_name,
        my_heat_distribution.ThermalPowerDelivered,
    )

    my_gasheater.connect_only_predefined_connections(
        my_gasheater_controller, my_simple_hot_water_storage
    )

    my_gasheater_controller.connect_only_predefined_connections(
        my_simple_hot_water_storage, my_weather, my_heat_distribution_controller
    )

    my_heat_distribution_controller.connect_only_predefined_connections(
        my_weather, my_building, my_simple_hot_water_storage
    )

    my_heat_distribution.connect_only_predefined_connections(
        my_heat_distribution_controller, my_building, my_simple_hot_water_storage
    )

    my_simple_hot_water_storage.connect_input(
        my_simple_hot_water_storage.WaterTemperatureFromHeatDistribution,
        my_heat_distribution.component_name,
        my_heat_distribution.WaterTemperatureOutput,
    )

    my_simple_hot_water_storage.connect_input(
        my_simple_hot_water_storage.WaterTemperatureFromHeatGenerator,
        my_gasheater.component_name,
        my_gasheater.MassflowOutputTemperature,
    )

    my_simple_hot_water_storage.connect_input(
        my_simple_hot_water_storage.WaterMassFlowRateFromHeatGenerator,
        my_gasheater.component_name,
        my_gasheater.MassflowOutput,
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

    # -----------------------------------------------------------------------------------------------------------------
    # connect Electricity Meter
    my_electricity_meter.add_component_input_and_connect(
        source_component_class=my_occupancy,
        source_component_output=my_occupancy.ElectricityOutput,
        source_load_type=lt.LoadTypes.ELECTRICITY,
        source_unit=lt.Units.WATT,
        source_tags=[lt.InandOutputType.ELECTRICITY_CONSUMPTION_UNCONTROLLED],
        source_weight=999,
    )

    my_electricity_meter.add_component_input_and_connect(
        source_component_class=my_domnestic_hot_water_heatpump,
        source_component_output=my_domnestic_hot_water_heatpump.ElectricityOutput,
        source_load_type=lt.LoadTypes.ELECTRICITY,
        source_unit=lt.Units.WATT,
        source_tags=[lt.InandOutputType.ELECTRICITY_CONSUMPTION_UNCONTROLLED],
        source_weight=999,
    )

    # =================================================================================================================================
    # Add Components to Simulation Parameters
    my_sim.add_component(my_occupancy)
    my_sim.add_component(my_weather)
    my_sim.add_component(my_building)
    my_sim.add_component(my_gasheater)
    my_sim.add_component(my_gasheater_controller)
    my_sim.add_component(my_heat_distribution)
    my_sim.add_component(my_heat_distribution_controller)
    my_sim.add_component(my_simple_hot_water_storage)
    my_sim.add_component(my_domnestic_hot_water_storage)
    my_sim.add_component(my_domnestic_hot_water_heatpump_controller)
    my_sim.add_component(my_domnestic_hot_water_heatpump)
    my_sim.add_component(my_electricity_meter)
    for my_car in my_cars:
        my_sim.add_component(my_car)
