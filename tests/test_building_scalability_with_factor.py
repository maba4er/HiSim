"""Test for scalability in building module with a factor.

The aim is to make the building module scalable via a factor which takes absolute conditioned floor area to the conditioned floor area given by tabula."""

import datetime
import numpy as np
import pandas as pd
from hisim import component
from hisim.components import loadprofilegenerator_connector
from hisim.components import weather
from hisim.components import building
from hisim.simulationparameters import SimulationParameters
from hisim import log
from hisim import utils
from tests import functions_for_testing as fft


@utils.measure_execution_time
def test_building():
    """Test function for the building module."""

    # Sets inputs
    my_occupancy_profile = "CH01"
    building_code = "DE.N.SFH.05.Gen.ReEx.001.001"
    building_heat_capacity_class = "medium"
    absolute_conditioned_floor_area_in_m2 = 121.2
    seconds_per_timestep = 60
    my_simulation_parameters = SimulationParameters.full_year(
        year=2021, seconds_per_timestep=seconds_per_timestep
    )

    repo = component.SimRepository()
            
    # # check on all TABULA buildings -> run test over all building_codes
    # d_f = pd.read_csv(
    #     utils.HISIMPATH["housing"],
    #     decimal=",",
    #     sep=";",
    #     encoding="cp1252",
    #     low_memory=False,
    # )

    # for building_code in d_f["Code_BuildingVariant"]:
    #     if isinstance(building_code, str):
    # Set Residence
    my_residence_config = (
        building.BuildingConfig.get_default_german_single_family_home()
    )
    my_residence_config.building_heat_capacity_class = building_heat_capacity_class
    my_residence_config.building_code = building_code
    my_residence_config.absolute_conditioned_floor_area_in_m2 = (
        absolute_conditioned_floor_area_in_m2
    )
    my_residence = building.Building(
        config=my_residence_config,
        my_simulation_parameters=my_simulation_parameters,
    )
    my_residence.set_sim_repo(repo)
    my_residence.i_prepare_simulation()

    log.information(building_code)

    # Set Occupancy
    my_occupancy_config = loadprofilegenerator_connector.OccupancyConfig(
        profile_name=my_occupancy_profile, name="Occupancy-1"
    )
    my_occupancy = loadprofilegenerator_connector.Occupancy(
        config=my_occupancy_config,
        my_simulation_parameters=my_simulation_parameters,
    )
    my_occupancy.set_sim_repo(repo)
    my_occupancy.i_prepare_simulation()

    # Set Weather
    my_weather_config = weather.WeatherConfig.get_default(
        location_entry=weather.LocationEnum.Aachen
    )
    my_weather = weather.Weather(
        config=my_weather_config, my_simulation_parameters=my_simulation_parameters
    )
    my_weather.set_sim_repo(repo)
    my_weather.i_prepare_simulation()

    number_of_outputs = fft.get_number_of_outputs(
        [my_occupancy, my_weather, my_residence]
    )
    stsv: component.SingleTimeStepValues = component.SingleTimeStepValues(
        number_of_outputs
    )
    my_residence.temperature_outside_channel.source_output = (
        my_weather.air_temperature_output
    )
    my_residence.altitude_channel.source_output = my_weather.altitude_output
    my_residence.azimuth_channel.source_output = my_weather.azimuth_output
    my_residence.direct_normal_irradiance_channel.source_output = (
        my_weather.DNI_output
    )
    my_residence.direct_horizontal_irradiance_channel.source_output = (
        my_weather.DHI_output
    )
    my_residence.occupancy_heat_gain_channel.source_output = (
        my_occupancy.heating_by_residentsC
    )

    fft.add_global_index_of_components(
        [my_occupancy, my_weather, my_residence]
    )

    log.information("Seconds per Timestep: " + str(seconds_per_timestep))
    log.information(
        "Absolute conditioned floor area "
        + str(my_residence_config.absolute_conditioned_floor_area_in_m2)
    )
    my_residence.seconds_per_timestep = seconds_per_timestep

    # Simulates
    stsv.values[my_residence.thermal_mass_temperature_channel.global_index] = 23

    my_occupancy.i_simulate(0, stsv, False)
    my_weather.i_simulate(0, stsv, False)
    my_residence.i_simulate(0, stsv, False)

    log.information(f"Occupancy Outputs: {stsv.values[0:4]}")
    log.information(f"Weather Outputs: {stsv.values[4:13]}")
    log.information(f"Residence Outputs: {stsv.values[13:17]}\n")

    max_thermal_heat_demand_in_watt_without_scaling = stsv.values[my_residence.var_max_thermal_building_demand_channel.global_index]

    # check building test with different absolute conditioned floor areas
    absolute_conditioned_floor_area_in_m2_scaled = 10 * absolute_conditioned_floor_area_in_m2
    log.information(
        "Absolute conditioned floor area upscaled "
        + str(absolute_conditioned_floor_area_in_m2_scaled)
    )
    my_residence_config.absolute_conditioned_floor_area_in_m2 = (
    absolute_conditioned_floor_area_in_m2_scaled
    )
    my_residence = building.Building(
        config=my_residence_config,
        my_simulation_parameters=my_simulation_parameters,
    )
    my_residence.set_sim_repo(repo)
    my_residence.i_prepare_simulation()
    my_residence.i_simulate(0,stsv,False)
    max_thermal_heat_demand_in_watt_with_scaling = stsv.values[my_residence.var_max_thermal_building_demand_channel.global_index]
    # test if max heat demand of building scales with conditioned floor area
    np.testing.assert_allclose(
        max_thermal_heat_demand_in_watt_without_scaling*10, max_thermal_heat_demand_in_watt_with_scaling,
        rtol=0.01,
    )
