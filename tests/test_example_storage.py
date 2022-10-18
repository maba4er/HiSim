"""Test for the example storage."""

from hisim import component as cp
from hisim.components import example_storage
from hisim.simulationparameters import SimulationParameters
from hisim import loadtypes as lt
from tests import functions_for_testing as fft


def test_example_storage():
    """Test for the example storage."""

    mysim:  SimulationParameters = SimulationParameters.full_year(year=2021, seconds_per_timestep=60)

    my_example_storage_config = example_storage.SimpleStorageConfig.get_default_thermal_storage()
    my_example_storage = example_storage.SimpleStorage(config=my_example_storage_config, my_simulation_parameters=mysim)

    # Define outputs
    charging_output = cp.ComponentOutput(object_name="source", field_name="charging", load_type=lt.LoadTypes.WARM_WATER, unit=lt.Units.KWH)
    discharging_output = cp.ComponentOutput(object_name="source", field_name="discharging", load_type=lt.LoadTypes.WARM_WATER, unit=lt.Units.KWH)

    my_example_storage.charging_input.source_output = charging_output
    my_example_storage.discharging_input.source_output = discharging_output

    number_of_outputs = fft.get_number_of_outputs([my_example_storage, charging_output, discharging_output])
    stsv: cp.SingleTimeStepValues = cp.SingleTimeStepValues(number_of_outputs)

    # Add Global Index and set values for fake Inputs
    fft.add_global_index_of_components([my_example_storage, charging_output, discharging_output])
    stsv.values[charging_output.global_index] = 40  # charg output
    stsv.values[discharging_output.global_index] = -10  # discharg output

    timestep = 300
    # Simulate
    assert 0 == stsv.values[my_example_storage.current_fill.global_index]
    my_example_storage.i_restore_state()
    my_example_storage.i_simulate(timestep, stsv, False)
    # my_example_storage.i_save_state()

    # Charging of the storage
    assert 40 == stsv.values[charging_output.global_index]
    # Discharging of the storage
    assert -10 == stsv.values[discharging_output.global_index]
    # Result of current storage fill state
    assert 30 == stsv.values[my_example_storage.current_fill.global_index]

    timestep = 301
    # my_example_storage.i_restore_state()
    my_example_storage.i_simulate(timestep, stsv, False)
    # Result of current storage fill state
    assert 40 == stsv.values[my_example_storage.current_fill.global_index]

    # # Test for charging
    # stsv.values[charging_output.global_index] = 2000  # charg output
    # timestep = 300
    # # Simulate for timestep 300
    # assert my_example_storage.state.fill == 0
    # log.information("state.fill at first " + str(my_example_storage.state.fill))
    # my_example_storage.i_restore_state()
    # log.information("state.fill after restore " + str(my_example_storage.state.fill))
    # my_example_storage.i_simulate(timestep, stsv, False)
    # log.information("state.fill after simulate " + str(my_example_storage.state.fill))
    # assert my_example_storage.state.fill == 2000

    # stsv.values[charging_output.global_index] = 2000  # charg output
    # timestep = 301
    # # Simulate for timestep 301
    # my_example_storage.i_simulate(timestep, stsv, False)
    # assert my_example_storage.state.fill == 4000  # should be two times 2000

    # # Test for discharging
    # stsv.values[discharging_output.global_index] = 2000  # discharg output
    # timestep = 300
    # # Simulate for timestep 300
    # assert my_example_storage.state.fill == 4000
    # my_example_storage.i_restore_state()
    # my_example_storage.i_simulate(timestep, stsv, False)
    # assert my_example_storage.state.fill == 2000

    # stsv.values[discharging_output.global_index] = 2000  # discharg output
    # timestep = 301
    # # Simulate for timestep 301
    # my_example_storage.i_simulate(timestep, stsv, False)
    # assert my_example_storage.state.fill == 0   # should withdraw two times 2000 to reach 0


if __name__ == "__main__":
    test_example_storage()
