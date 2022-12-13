"""Gas Heater Module."""

# Owned
from typing import List
from dataclasses import dataclass
from dataclasses_json import dataclass_json
from hisim.component import (
    Component,
    SingleTimeStepValues,
    ComponentInput,
    ComponentOutput,
)
from hisim.simulationparameters import SimulationParameters
from hisim import loadtypes as lt
from hisim import utils


__authors__ = "Frank Burkrad, Maximilian Hillen"
__copyright__ = "Copyright 2021, the House Infrastructure Project"
__credits__ = ["Noah Pflugradt"]
__license__ = ""
__version__ = ""
__maintainer__ = "Maximilian Hillen"
__email__ = "maximilian.hillen@rwth-aachen.de"
__status__ = ""


@dataclass_json
@dataclass
class GenericGasHeaterConfig:

    """Configuration of the GasHeater class."""

    is_modulating: bool
    minimal_thermal_power_in_watt: float  # [W]
    maximal_thermal_power_in_watt: float  # [W]
    eff_th_min: float  # [-]
    eff_th_max: float  # [-]
    delta_temperature_in_celsius: float  # [°C]
    maximal_mass_flow_in_kilogram_per_second: float  # kg/s ## -> ~0.07 P_th_max / (4180 * delta_T)
    maximal_temperature_in_celsius: float  # [°C]
    temperature_delta_in_celsius: float  # [°C]
    maximal_power_in_watt: float  # [W]


class GasHeater(Component):

    """GasHeater class.

    Gets Control Signal and calculates on base of it Massflow and Temperature of Massflow.
    """

    # Input
    ControlSignal = (
        "ControlSignal"  # at which Procentage is the GasHeater modulating [0..1]
    )
    MassflowInputTemperature = "MassflowInputTemperature"

    # Output
    MassflowOutput = "Hot Water Energy Output"
    MassflowOutputTemperature = "MassflowOutputTemperature"
    GasDemand = "GasDemand"
    ThermalOutputPower = "ThermalOutputPower"

    @utils.graph_call_path_factory(max_depth=2, memory_flag=True, file_name="call_path")
    def __init__(
        self,
        my_simulation_parameters: SimulationParameters,
        config: GenericGasHeaterConfig,
    ) -> None:
        """Constructs all the neccessary attributes."""
        super().__init__(
            name="GasHeater", my_simulation_parameters=my_simulation_parameters
        )
        self.control_signal_channel: ComponentInput = self.add_input(
            self.component_name,
            GasHeater.ControlSignal,
            lt.LoadTypes.ANY,
            lt.Units.PERCENT,
            True,
        )
        self.mass_flow_input_tempertaure_channel: ComponentInput = self.add_input(
            self.component_name,
            GasHeater.MassflowInputTemperature,
            lt.LoadTypes.WATER,
            lt.Units.CELSIUS,
            True,
        )

        self.mass_flow_output_channel: ComponentOutput = self.add_output(
            self.component_name,
            GasHeater.MassflowOutput,
            lt.LoadTypes.WATER,
            lt.Units.KG_PER_SEC,
        )
        self.mass_flow_output_temperature_channel: ComponentOutput = self.add_output(
            self.component_name,
            GasHeater.MassflowOutputTemperature,
            lt.LoadTypes.WATER,
            lt.Units.CELSIUS,
        )
        self.gas_demand_channel: ComponentOutput = self.add_output(
            self.component_name, GasHeater.GasDemand, lt.LoadTypes.GAS, lt.Units.KWH
        )
        self.thermal_output_power_channel: ComponentOutput = self.add_output(
            object_name=self.component_name,
            field_name=self.ThermalOutputPower,
            load_type=lt.LoadTypes.HEATING,
            unit=lt.Units.WATT,
        )

        self.minimal_thermal_power_in_watt = config.minimal_thermal_power_in_watt
        self.maximal_thermal_power_in_watt = config.maximal_power_in_watt
        self.eff_th_min = config.eff_th_min
        self.eff_th_max = config.eff_th_max
        self.maximal_temperature_in_celsius = config.maximal_temperature_in_celsius
        self.temperature_delta_in_celsius = config.temperature_delta_in_celsius

    @staticmethod
    def get_default_config():
        """Gets a default gas heater."""
        config = GenericGasHeaterConfig(
            temperature_delta_in_celsius=10,
            maximal_power_in_watt=12_000,
            is_modulating=True,
            minimal_thermal_power_in_watt=1_000,  # [W]
            maximal_thermal_power_in_watt=12_000,  # [W]
            eff_th_min=0.60,  # [-]
            eff_th_max=0.90,  # [-]
            delta_temperature_in_celsius=25,
            maximal_mass_flow_in_kilogram_per_second=12_000
            / (4180 * 25),  # kg/s ## -> ~0.07 P_th_max / (4180 * delta_T)
            maximal_temperature_in_celsius=80,  # [°C])
        )
        return config

    def i_prepare_simulation(self) -> None:
        """Prepares the simulation."""
        pass

    def write_to_report(self) -> List[str]:
        """Writes a report."""
        lines: List = []
        return lines

    def i_save_state(self) -> None:
        """Saves the current state."""
        pass

    def i_restore_state(self) -> None:
        """Restores the previous state."""
        pass

    def i_doublecheck(self, timestep: int, stsv: SingleTimeStepValues) -> None:
        """Doublechecks."""
        pass

    def i_simulate(
        self, timestep: int, stsv: SingleTimeStepValues, force_convergence: bool
    ) -> None:
        """Simulates the gas heater."""
        control_signal = stsv.get_input_value(self.control_signal_channel)
        if control_signal > 1:
            raise Exception("Expected a control signal between 0 and 1")
        if control_signal < 0:
            raise Exception("Expected a control signal between 0 and 1")

        # Calculate Eff
        d_eff_th = self.eff_th_max - self.eff_th_min

        if control_signal * self.maximal_thermal_power_in_watt < self.minimal_thermal_power_in_watt:
            maximum_power = self.minimal_thermal_power_in_watt
            eff_th_real = self.eff_th_min
        else:
            maximum_power = control_signal * self.maximal_thermal_power_in_watt
            eff_th_real = self.eff_th_min + d_eff_th * control_signal

        gas_power = maximum_power * eff_th_real * control_signal
        c_w = 4182
        mass_out_temp = self.temperature_delta_in_celsius + stsv.get_input_value(self.mass_flow_input_tempertaure_channel)
        mass_out = gas_power / (c_w * self.temperature_delta_in_celsius)
        # p_th = (
        #     c_w * mass_out * (mass_out_temp - stsv.get_input_value(self.mass_flow_input_tempertaure_channel))
        # )

        stsv.set_output_value(self.thermal_output_power_channel, gas_power)  # efficiency
        stsv.set_output_value(self.mass_flow_output_temperature_channel, mass_out_temp)  # efficiency
        stsv.set_output_value(self.mass_flow_output_channel, mass_out)  # efficiency
        stsv.set_output_value(self.gas_demand_channel, gas_power)  # gas consumption
