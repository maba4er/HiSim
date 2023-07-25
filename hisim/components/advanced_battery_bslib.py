""" Battery implementation built upon the bslib library. It contains a Battery Class together with its Configuration and State. """

# Import packages from standard library or the environment e.g. pandas, numpy etc.
from typing import List, Any, Tuple
from dataclasses import dataclass
from bslib import bslib as bsl
from dataclasses_json import dataclass_json

# Import modules from HiSim
from hisim.component import (
    Component,
    ComponentInput,
    ComponentOutput,
    SingleTimeStepValues,
    ConfigBase,
)
from hisim.loadtypes import LoadTypes, Units, InandOutputType, ComponentType
from hisim.simulationparameters import SimulationParameters
from typing import Optional

__authors__ = "Tjarko Tjaden, Hauke Hoops, Kai Rösken"
__copyright__ = "Copyright 2021, the House Infrastructure Project"
__credits__ = "..."
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Tjarko Tjaden"
__email__ = "tjarko.tjaden@hs-emden-leer.de"
__status__ = "development"


@dataclass_json
@dataclass
class BatteryConfig(ConfigBase):
    """Battery Configuration."""

    @classmethod
    def get_main_classname(cls):
        """Return the full class name of the base class."""
        return Battery.get_full_classname()

    #: name of the device
    name: str
    #: priority of the device in hierachy: the higher the number the lower the priority
    source_weight: int
    #: name of battery to search in database (bslib)
    system_id: str
    #: charging and discharging power in Watt
    p_inv_custom: float
    #: battery capacity in in kWh
    e_bat_custom: float
    #: CO2 footprint of investment in kg
    co2_footprint: float
    #: cost for investment in Euro
    cost: float
    #: lifetime of battery in years
    lifetime: float

    @classmethod
    def get_default_config(cls) -> "BatteryConfig":
        """Returns default configuration of battery."""
        p_inv_custom: float = 5
        config = BatteryConfig(
            name="Battery",
            p_inv_custom=p_inv_custom,
            e_bat_custom=10,
            source_weight=1,
            system_id="SG1",
            co2_footprint=p_inv_custom * 130.7,  # value from emission_factros_and_costs_devices.csv
            cost=p_inv_custom * 535.81,  # value from emission_factros_and_costs_devices.csv
            lifetime=10  # todo set correct values
        )
        return config


class Battery(Component):
    """
    Simulate state of charge and realized power of a ac coupled battery
    storage system with the bslib library. Relevant simulation parameters
    are loaded within the init for a specific or generic battery type.

    Components to connect to:
    (1) Energy Management System
    """

    # Inputs
    LoadingPowerInput = "LoadingPowerInput"  # W

    # Outputs
    AcBatteryPower = "AcBatteryPower"  # W
    DcBatteryPower = "DcBatteryPower"  # W
    StateOfCharge = "StateOfCharge"  # [0..1]

    @staticmethod
    def get_cost_capex(config: BatteryConfig) -> Tuple[float, float, float]:
        """Returns investment cost, CO2 emissions and lifetime."""
        # Todo: think about livetime in cycles not in years
        return config.cost, config.co2_footprint, config.lifetime

    def __init__(
        self, my_simulation_parameters: SimulationParameters, config: BatteryConfig
    ):
        """
        Loads the parameters of the specified battery storage.
        """
        self.battery_config = config
        super().__init__(
            name=self.battery_config.name
            + "_w"
            + str(self.battery_config.source_weight),
            my_simulation_parameters=my_simulation_parameters,
            my_config=config,
        )

        self.source_weight = self.battery_config.source_weight

        self.system_id = self.battery_config.system_id

        self.p_inv_custom = self.battery_config.p_inv_custom

        self.e_bat_custom = self.battery_config.e_bat_custom

        # Component has states
        self.state = BatteryState()
        self.previous_state = self.state.clone()

        # Load battery object with parameters from bslib database
        self.BAT = bsl.ACBatMod(
            system_id=self.system_id,
            p_inv_custom=self.p_inv_custom,
            e_bat_custom=self.e_bat_custom,
        )

        # Define component inputs
        self.p_set: ComponentInput = self.add_input(
            object_name=self.component_name,
            field_name=self.LoadingPowerInput,
            load_type=LoadTypes.ELECTRICITY,
            unit=Units.WATT,
            mandatory=True,
        )

        # Define component outputs
        self.p_bs: ComponentOutput = self.add_output(
            object_name=self.component_name,
            field_name=self.AcBatteryPower,
            load_type=LoadTypes.ELECTRICITY,
            unit=Units.WATT,
            postprocessing_flag=[
                InandOutputType.CHARGE_DISCHARGE,
                ComponentType.BATTERY,
            ],
            output_description=f"here a description for {self.AcBatteryPower} will follow.",
        )

        self.p_bat: ComponentOutput = self.add_output(
            object_name=self.component_name,
            field_name=self.DcBatteryPower,
            load_type=LoadTypes.ELECTRICITY,
            unit=Units.WATT,
            output_description=f"here a description for {self.DcBatteryPower} will follow.",
        )

        self.soc: ComponentOutput = self.add_output(
            object_name=self.component_name,
            field_name=self.StateOfCharge,
            load_type=LoadTypes.ANY,
            unit=Units.ANY,
            postprocessing_flag=[InandOutputType.STORAGE_CONTENT],
            output_description=f"here a description for {self.StateOfCharge} will follow.",
        )

    def i_save_state(self) -> None:
        self.previous_state = self.state.clone()

    def i_restore_state(self) -> None:
        self.state = self.previous_state.clone()

    def i_doublecheck(self, timestep: int, stsv: SingleTimeStepValues) -> None:
        pass

    def i_prepare_simulation(self) -> None:
        """Prepares the simulation."""
        pass

    def i_simulate(
        self, timestep: int, stsv: SingleTimeStepValues, force_convergence: bool
    ) -> None:

        # Parameters
        dt = self.my_simulation_parameters.seconds_per_timestep

        # Load input values
        p_set = stsv.get_input_value(self.p_set)
        soc = self.state.soc

        # Simulate on timestep
        results = self.BAT.simulate(p_load=p_set, soc=soc, dt=dt)
        p_bs = results[0]
        p_bat = results[1]
        soc = results[2]

        # write values for output time series
        stsv.set_output_value(self.p_bs, p_bs)
        stsv.set_output_value(self.p_bat, p_bat)
        stsv.set_output_value(self.soc, soc)

        # write values to state
        self.state.soc = soc

    def write_to_report(self) -> List[str]:
        return self.battery_config.get_string_dict()


@dataclass
class BatteryState:
    #: state of charge of the battery
    soc: float = 0

    def clone(self):
        "Creates a copy of the Battery State."
        return BatteryState(soc=self.soc)
