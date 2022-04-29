from typing import Optional, List, Union
import hisim.components.random_numbers
from hisim.simulator import SimulationParameters
from hisim.components import loadprofilegenerator_connector
from hisim.components import generic_price_signal
from hisim.components import weather
from hisim.components import generic_gas_heater
from hisim.components import controller_l3_predictive
from hisim.components import generic_smart_device_2
from hisim.components import building
from hisim.components import generic_in_and_output_testing
from hisim.components import generic_dhw_boiler
from hisim.components.random_numbers import RandomNumbers
from hisim.components.example_transformer import Transformer
from hisim.components.set_in_and_outputs import DynamicComponent
from hisim import loadtypes as lt

def basic_household_explicit(my_sim, my_simulation_parameters: Optional[SimulationParameters] = None):
    year = 2018
    seconds_per_timestep = 60 * 15
    if my_simulation_parameters is None:
        my_simulation_parameters = SimulationParameters.full_year_all_options(year=year,
                                                                                 seconds_per_timestep=seconds_per_timestep)
    my_sim.SimulationParameters = my_simulation_parameters
    # Build occupancy
    in_and_output_testing = generic_in_and_output_testing.Test_InandOutputs(my_simulation_parameters=my_simulation_parameters)

    my_gas_heater = generic_gas_heater.GasHeater(my_simulation_parameters=my_simulation_parameters)
    my_rn1 = RandomNumbers(name="Random numbers 100-200",
                           timesteps=my_simulation_parameters.timesteps,
                           minimum=100,
                           maximum=200, my_simulation_parameters=my_simulation_parameters)
    my_sim.add_component(my_rn1)

    # Create second RandomNumbers object and adds to simulator
    my_rn2 = RandomNumbers(name="Random numbers 80-200",
                           timesteps=my_simulation_parameters.timesteps,
                           minimum=80,
                           maximum=200, my_simulation_parameters=my_simulation_parameters)
    my_sim.add_component(my_rn2)

    my_rn3 = RandomNumbers(name="Random numbers 5-200",
                           timesteps=my_simulation_parameters.timesteps,
                           minimum=5,
                           maximum=200, my_simulation_parameters=my_simulation_parameters)
    my_sim.add_component(my_rn3)

    in_and_output_testing.connect_input(in_and_output_testing.TempInput,
                                         my_rn3.ComponentName,
                                         my_rn3.RandomOutput)
    my_gas_heater.connect_input(my_gas_heater.MassflowInputTemperature,
                                         my_rn3.ComponentName,
                                         my_rn3.RandomOutput)
    in_and_output_testing.add_component_input_and_connect( source_component_class=my_rn1,
                                               source_component_output=my_rn1.RandomOutput,
                                               source_load_type= lt.LoadTypes.Any,
                                               source_unit= lt.Units.Any,
                                               source_tags=[lt.ComponentType.HeatPump,lt.InandOutputType.Massflow],
                                               source_weight=1)
    in_and_output_testing.add_component_input_and_connect( source_component_class=my_rn2,
                                               source_component_output=my_rn2.RandomOutput,
                                               source_load_type= lt.LoadTypes.Any,
                                               source_unit= lt.Units.Any,
                                               source_tags=[lt.ComponentType.HeatPump,lt.InandOutputType.Massflow],
                                               source_weight=2)
    output_control_signal = in_and_output_testing.add_component_output(source_output_name=lt.InandOutputType.ControlSignal,
                                               source_tags=[lt.ComponentType.GasHeater],
                                               source_load_type= lt.LoadTypes.Any,
                                               source_unit= lt.Units.Percent)


    my_gas_heater.connect_dynamic_input(input_fieldname=generic_gas_heater.GasHeater.ControlSignal,
                                        src_object=output_control_signal)

    in_and_output_testing.add_component_output(source_output_name=lt.InandOutputType.ControlSignal,
                                               source_tags=[lt.ComponentType.HeatPump],
                                               source_load_type= lt.LoadTypes.Any,
                                               source_unit= lt.LoadTypes.Any)

    my_sim.add_component(in_and_output_testing)
    my_sim.add_component(my_gas_heater)
