import os

from hisim import hisim_main
from hisim.simulationparameters import SimulationParameters
from hisim import log
from hisim import utils

@utils.measure_execution_time
def test_household_ac_explicit():
    path = "../examples/air_conditioned_house_controller_pid.py"
    func = "household_ac_explicit"
    mysimpar = SimulationParameters.one_day_only(year=2019, seconds_per_timestep=60)
    hisim_main.main(path, func, mysimpar)
    log.information(os.getcwd())
    