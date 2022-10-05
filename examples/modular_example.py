"""Example sets up a modular household according to json input file."""

from typing import Optional, List, Any
from pathlib import Path
import os
import json
import hisim.log
import hisim.utils
import hisim.loadtypes as lt
import scipy.interpolate
from hisim.modular_household import component_connections
from hisim.modular_household.modular_household_results import ModularHouseholdResults
from hisim.simulationparameters import SystemConfig
from hisim.simulator import SimulationParameters
from hisim.postprocessingoptions import PostProcessingOptions

from hisim.components import loadprofilegenerator_connector
from hisim.components import generic_price_signal
from hisim.components import weather
from hisim.components import building
from hisim.components import controller_l2_energy_management_system


def modular_household_explicit(my_sim: Any, my_simulation_parameters: Optional[SimulationParameters] = None) -> None:

    """Setup function emulates an household including the basic components.

    The configuration of the household is read in via the json input file "system_config.json".
    """

    # Set simulation parameters
    year = 2018
    seconds_per_timestep = 60 * 15

    # path of system config file
    system_config_filename = "system_config.json"

    count = 1  # initialize source_weight with one
    production: List = []  # initialize list of components involved in production
    consumption: List = []  # initialize list of components involved in consumption
    heater: List = []  # initialize list of components used for heating

    # Build system parameters
    if my_simulation_parameters is None:
        my_simulation_parameters = SimulationParameters.january_only(year=year, seconds_per_timestep=seconds_per_timestep)
        my_simulation_parameters.post_processing_options.append(PostProcessingOptions.PLOT_CARPET)
        my_simulation_parameters.post_processing_options.append(PostProcessingOptions.GENERATE_PDF_REPORT)
        my_simulation_parameters.post_processing_options.append(PostProcessingOptions.COMPUTE_KPI)
        my_simulation_parameters.post_processing_options.append(PostProcessingOptions.MAKE_NETWORK_CHARTS)
        my_simulation_parameters.skip_finished_results = False

    # try to read the system config from file
    if Path(system_config_filename).is_file():
        with open(system_config_filename, encoding='utf8') as system_config_file:
            system_config = SystemConfig.from_json(system_config_file.read())  # type: ignore
        hisim.log.information(f"Read system config from {system_config_filename}")
        my_simulation_parameters.system_config = system_config

    else:
        my_simulation_parameters.reset_system_config(
            location=lt.Locations.AACHEN, occupancy_profile=lt.OccupancyProfiles.CH01, building_code=lt.BuildingCodes.DE_N_SFH_05_GEN_REEX_001_002,
            predictive=True, prediction_horizon=24 * 3600, pv_included=True, pv_peak_power=10e3, smart_devices_included=True,
            water_heating_system_installed=lt.HeatingSystems.HEAT_PUMP, heating_system_installed=lt.HeatingSystems.HEAT_PUMP, buffer_included=True,
            buffer_volume=500, battery_included=True, battery_capacity=10e3, chp_included=True, chp_power=10e3, h2_storage_size=100,
            electrolyzer_power=5e3, current_mobility=lt.Cars.NO_CAR, mobility_distance=lt.MobilityDistance.RURAL)

    my_sim.set_simulation_parameters(my_simulation_parameters)

    # get system configuration
    location = weather.LocationEnum[my_simulation_parameters.system_config.location.value]
    occupancy_profile = my_simulation_parameters.system_config.occupancy_profile
    building_code = my_simulation_parameters.system_config.building_code
    pv_included = my_simulation_parameters.system_config.pv_included  # True or False
    if pv_included:
        pv_peak_power = my_simulation_parameters.system_config.pv_peak_power
    smart_devices_included = my_simulation_parameters.system_config.smart_devices_included  # True or False
    water_heating_system_installed = my_simulation_parameters.system_config.water_heating_system_installed  # Electricity, Hydrogen or False
    heating_system_installed = my_simulation_parameters.system_config.heating_system_installed
    buffer_included = my_simulation_parameters.system_config.buffer_included
    if buffer_included:
        buffer_volume = my_simulation_parameters.system_config.buffer_volume
    battery_included = my_simulation_parameters.system_config.battery_included
    if battery_included:
        battery_capacity = my_simulation_parameters.system_config.battery_capacity
    chp_included = my_simulation_parameters.system_config.chp_included
    if chp_included:
        chp_power = my_simulation_parameters.system_config.chp_power
        h2_storage_size = my_simulation_parameters.system_config.h2_storage_size
        electrolyzer_power = my_simulation_parameters.system_config.electrolyzer_power
        

        

    """BASICS"""
    # Build occupancy
    my_occupancy_config = loadprofilegenerator_connector.OccupancyConfig(profile_name=occupancy_profile.value, name='Occupancy')
    my_occupancy = loadprofilegenerator_connector.Occupancy(config=my_occupancy_config, my_simulation_parameters=my_simulation_parameters)
    my_sim.add_component(my_occupancy)
    consumption.append(my_occupancy)

    # Build Weather
    my_weather_config = weather.WeatherConfig.get_default(location_entry=location)
    my_weather = weather.Weather(config=my_weather_config, my_simulation_parameters=my_simulation_parameters)
    my_sim.add_component(my_weather)

    # Build building
    my_building_config = building.BuildingConfig.get_default_german_single_family_home()
    my_building_config.building_code = building_code.value
    my_building = building.Building(config=my_building_config, my_simulation_parameters=my_simulation_parameters)
    my_building.connect_only_predefined_connections(my_weather, my_occupancy)
    my_sim.add_component(my_building)

    # add price signal
    my_price_signal = generic_price_signal.PriceSignal(my_simulation_parameters=my_simulation_parameters)
    my_sim.add_component(my_price_signal)
    economic_parameters = json.load(open('..\hisim\modular_household\EconomicParameters.json'))

    """PV"""
    if pv_included:
        production, count = component_connections.configure_pv_system(
            my_sim=my_sim, my_simulation_parameters=my_simulation_parameters, my_weather=my_weather, production=production,
            pv_peak_power=pv_peak_power, count=count)
        production, count = component_connections.configure_pv_system(
            my_sim=my_sim, my_simulation_parameters=my_simulation_parameters, my_weather=my_weather, production=production,
            pv_peak_power=pv_peak_power, count=count)

        if economic_parameters["pv_bought"]==True:
            ccpv = json.load(open('..\hisim\modular_household\ComponentCostPV.json'))       
            pv_cost = scipy.interpolate.interp1d(ccpv["capacity_for_cost"], ccpv["cost_per_capacity"])
            pv_cost = pv_cost(pv_peak_power)
            #print("Interpolierter Preis für Kapazität:", pv_cost(pv_peak_power))
        else:
            pv_cost = 0

    """SMART DEVICES"""
    my_smart_devices, consumption, count = component_connections.configure_smart_devices(
        my_sim=my_sim, my_simulation_parameters=my_simulation_parameters,
        consumption=consumption, count=count)
    if economic_parameters["smart_devices_bought"]==True:
        ccsd = json.load(open('..\hisim\modular_household\ComponentCostSmartDevice.json'))
        smart_devices_cost = ccsd["smart_devices_cost"]
    else:
        smart_devices_cost = 0

    """SURPLUS CONTROLLER"""
    if battery_included or chp_included or heating_system_installed in [lt.HeatingSystems.HEAT_PUMP, lt.HeatingSystems.ELECTRIC_HEATING] \
            or water_heating_system_installed in [lt.HeatingSystems.HEAT_PUMP, lt.HeatingSystems.ELECTRIC_HEATING]:
        my_electricity_controller = controller_l2_energy_management_system.ControllerElectricityGeneric(
            my_simulation_parameters=my_simulation_parameters)

        my_electricity_controller.add_component_inputs_and_connect(source_component_classes=consumption,
                                                                   outputstring='ElectricityOutput',
                                                                   source_load_type=lt.LoadTypes.ELECTRICITY,
                                                                   source_unit=lt.Units.WATT,
                                                                   source_tags=[lt.InandOutputType.CONSUMPTION],
                                                                   source_weight=999)
        my_electricity_controller.add_component_inputs_and_connect(source_component_classes=production,
                                                                   outputstring='ElectricityOutput',
                                                                   source_load_type=lt.LoadTypes.ELECTRICITY,
                                                                   source_unit=lt.Units.WATT,
                                                                   source_tags=[lt.InandOutputType.PRODUCTION],
                                                                   source_weight=999)
    surplus_controller_cost=400
    """WATERHEATING"""
    count = component_connections.configure_water_heating(
        my_sim=my_sim, my_simulation_parameters=my_simulation_parameters, my_occupancy=my_occupancy,
        my_electricity_controller=my_electricity_controller, my_weather=my_weather,
        water_heating_system_installed=water_heating_system_installed, count=count)

    """HEATING"""
    if buffer_included:
        my_heater, my_buffer, count = component_connections.configure_heating_with_buffer(
            my_sim=my_sim, my_simulation_parameters=my_simulation_parameters, my_building=my_building,
            my_electricity_controller=my_electricity_controller, my_weather=my_weather, heating_system_installed=heating_system_installed,
            buffer_volume=buffer_volume, count=count)
    else:
        my_heater, count = component_connections.configure_heating(
            my_sim=my_sim, my_simulation_parameters=my_simulation_parameters, my_building=my_building,
            my_electricity_controller=my_electricity_controller, my_weather=my_weather, heating_system_installed=heating_system_installed,
            count=count)
    heater.append(my_heater)

# =============================================================================
#     if economic_parameters["heatpump_bought"]==True:
#         heating_cost_interp = scipy.interpolate.interp1d(ccb["capacity_cost"], ccb["cost"])
#         heating_cost=heating_cost_interp(battery_capacity)
#         
#         water_heating_cost_interp = scipy.interpolate.interp1d(ccb["capacity_cost"], ccb["cost"])
#         water_heating_cost=heating_cost_interp(battery_capacity)
#     else:
#         heating_system_cost = 0
#         water_heating_system_cost = 0
# =============================================================================
    


    """BATTERY"""
    if battery_included:
        count = component_connections.configure_battery(
            my_sim=my_sim, my_simulation_parameters=my_simulation_parameters, my_electricity_controller=my_electricity_controller,
            battery_capacity=battery_capacity, count=count)
        #EconomicParameters.battery_bought abfragen, ob Batterie bereits vorhanden ist
        ccb = json.load(open('..\hisim\modular_household\ComponentCostBattery.json'))
        print("Battery capacity", battery_capacity)
        
        if economic_parameters["battery_bought"]==True:
            battery_cost_interp = scipy.interpolate.interp1d(ccb["capacity_cost"], ccb["cost"])
            battery_cost=battery_cost_interp(battery_capacity)
        else:
            battery_cost = 0

    """CHP + H2 STORAGE + ELECTROLYSIS"""
    if chp_included:
        my_chp, count = component_connections.configure_elctrolysis_h2storage_chp_system(
            my_sim=my_sim, my_simulation_parameters=my_simulation_parameters, my_building=my_building,
            my_electricity_controller=my_electricity_controller, chp_power=chp_power, h2_storage_size=h2_storage_size,
            electrolyzer_power=electrolyzer_power, count=count)
        heater.append(my_chp)

        if buffer_included:
            my_buffer.add_component_inputs_and_connect(source_component_classes=heater, outputstring='ThermalPowerDelivered',
                                                       source_load_type=lt.LoadTypes.HEATING, source_unit=lt.Units.WATT,
                                                       source_tags=[lt.InandOutputType.HEAT_TO_BUFFER], source_weight=999)
        else:
            my_building.add_component_inputs_and_connect(source_component_classes=heater, outputstring='ThermalPowerDelivered',
                                                         source_load_type=lt.LoadTypes.HEATING, source_unit=lt.Units.WATT,
                                                         source_tags=[lt.InandOutputType.HEAT_TO_BUILDING], source_weight=999)

    if battery_included or chp_included or heating_system_installed in [lt.HeatingSystems.HEAT_PUMP, lt.HeatingSystems.ELECTRIC_HEATING] \
            or water_heating_system_installed in [lt.HeatingSystems.HEAT_PUMP, lt.HeatingSystems.ELECTRIC_HEATING]:
        my_sim.add_component(my_electricity_controller)

    if economic_parameters["h2system_bought"] is True:

        ccchp = json.load(open('..\hisim\modular_household\ComponentCostCHP.json'))
        chp_cost_interp = scipy.interpolate.interp1d(ccchp["capacity_for_cost"], ccchp["cost_per_capacity"])
        chp_cost = chp_cost_interp(chp_power)

        cch2 = json.load(open('..\hisim\modular_household\ComponentCostH2Storage.json'))
        h2_storage_cost_interp = scipy.interpolate.interp1d(cch2["capacity_for_cost"], cch2["cost_per_capacity"])
        h2_storage_cost = h2_storage_cost_interp(h2_storage_size)

        ccel = json.load(open('..\hisim\modular_household\ComponentCostElectrolyzer.json'))
        electrolyzer_cost_interp = scipy.interpolate.interp1d(ccel["capacity_for_cost"], ccel["cost_per_capacity"])
        electrolyzer_cost = electrolyzer_cost_interp(electrolyzer_power)
    else:
        chp_cost = 0
        h2_storage_cost=0
        electrolyzer_cost=0

    """PREDICTIVE CONTROLLER FOR SMART DEVICES"""
    # use predictive controller if smart devices are included and do not use it if it is false
    if smart_devices_included:
        my_simulation_parameters.system_config.predictive = True
        component_connections.configure_smart_controller_for_smart_devices(
            my_sim=my_sim, my_simulation_parameters=my_simulation_parameters, my_smart_devices=my_smart_devices)
    else:
        my_simulation_parameters.system_config.predictive = False

    if economic_parameters["smart_devices_bought"]==True:
        ccpcfsd = json.load(open('..\hisim\modular_household\ComponentCostPredictiveControllerforSmartDevices.json'))
        predictive_controller_for_smart_devices_cost = ccpcfsd["predictive_controller_for_smart_devices_cost"]
    else:
        predictive_controller_for_smart_devices_cost = 0

    """ELECTRIC VEHICLE"""        
    if economic_parameters["ev_bought"]==True:
        ccev = json.load(open('..\hisim\modular_household\ComponentCostElectricVehicle.json'))
        ev_cost_interp = scipy.interpolate.interp1d(ccev["capacity_for_cost"], ccev["cost_per_capacity"])
        ev_cost=ev_cost_interp(battery_capacity)
    else:
        ev_cost = 0

    """BUFFER"""        
    if economic_parameters["buffer_bought"]==True:
        ccbu = json.load(open('..\hisim\modular_household\ComponentCostBuffer.json'))
        buffer_cost_interp = scipy.interpolate.interp1d(ccbu["capacity_for_cost"], ccbu["cost_per_capacity"])
        buffer_cost=buffer_cost_interp(buffer_volume)
    else:
        buffer_cost = 0

    investment_cost= pv_cost + smart_devices_cost + battery_cost + buffer_cost + chp_cost
    + h2_storage_cost + electrolyzer_cost + predictive_controller_for_smart_devices_cost + ev_cost + surplus_controller_cost
    # +  water_heating_system_cost + heating_system_cost

    co2_cost = 1000    # CO2 von Herstellung der Komponenten plus CO2 für den Stromverbrauch der Komponenten
    injection = 1000
    autarky_rate = 1000
    self_consumption_rate = 1000

    modular_household_results = ModularHouseholdResults(
        investment_cost=investment_cost,
        co2_cost=co2_cost,
        injection=injection,
        autarky_rate=autarky_rate,
        self_consumption_rate=self_consumption_rate,
        terminationflag=lt.Termination.SUCCESSFUL)
