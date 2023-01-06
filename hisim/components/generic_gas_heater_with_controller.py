"""Gas Heater Module."""
# clean
# Owned
from typing import List, Any
from dataclasses import dataclass
from dataclasses_json import dataclass_json
import hisim.component as cp
from hisim.component import (
    SingleTimeStepValues,
    ComponentInput,
    ComponentOutput,
)
from hisim.components.building import Building
from hisim.simulationparameters import SimulationParameters
from hisim import loadtypes as lt
from hisim import utils
from hisim import log


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
class GenericGasHeaterWithControllerConfig(cp.ConfigBase):

    """Configuration of the GasHeater class."""

    @classmethod
    def get_main_classname(cls):
        """Return the full class name of the base class."""
        return GasHeaterWithController.get_full_classname()

    name: str
    is_modulating: bool
    minimal_thermal_power_in_watt: float  # [W]
    maximal_thermal_power_in_watt: float  # [W]
    delta_temperature_in_celsius: float  # [°C]
    maximal_mass_flow_in_kilogram_per_second: float  # kg/s ## -> ~0.07 P_th_max / (4180 * delta_T)
    maximal_temperature_in_celsius: float  # [°C]
    temperature_delta_in_celsius: float  # [°C]

    @classmethod
    def get_default_gasheater_config(
        cls,
    ) -> Any:
        """Get a default gasheater config."""
        config = GenericGasHeaterWithControllerConfig(
            name="Gasheater",
            temperature_delta_in_celsius=10,
            is_modulating=True,
            minimal_thermal_power_in_watt=1_000,  # [W]
            maximal_thermal_power_in_watt=12_000,  # [W]
            delta_temperature_in_celsius=25,
            maximal_mass_flow_in_kilogram_per_second=12_000
            / (4180 * 25),  # kg/s ## -> ~0.07 P_th_max / (4180 * delta_T)
            maximal_temperature_in_celsius=80,  # [°C])
        )
        return config


# class GenericGasHeaterState:

#     """Gas Heater State class.

#     It determines the state of the gas heater.

#     """

#     def __init__(
#         self,
#         start_timestep: int = 0,
#         thermal_power_delivered_in_watt: float = 0.0,
#         # cop: float = 1.0,
#         # cycle_number: Optional[int] = None,
#     ) -> None:
#         """Contruct all the necessary attributes."""
#         self.start_timestep = start_timestep
#         self.thermal_power_delivered_in_watt = thermal_power_delivered_in_watt
#         # self.cycle_number = cycle_number
#         if thermal_power_delivered_in_watt == 0.0:
#             self.activation = 0
#             self.heating_power_in_watt = 0.0
#             # self.cop = 1.0
#             # self.electricity_input_in_watt = abs(self.thermal_power_delivered_in_watt / self.cop)
#         elif self.thermal_power_delivered_in_watt > 0.0:
#             self.activation = -1
#             self.heating_power_in_watt = self.thermal_power_delivered_in_watt
#             # self.cop = cop
#             # self.electricity_input_in_watt = abs(self.thermal_power_delivered_in_watt / self.cop)
#         else:
#             raise Exception("Impossible Gas Heater State.")

#     def clone(self) -> Any:
#         """Clone gas heater state."""
#         return GenericGasHeaterState(
#             self.start_timestep,
#             self.thermal_power_delivered_in_watt,
#             # self.cop,
#             # self.cycle_number,
#         )


class GasHeaterWithController(cp.Component):

    """GasHeater class.

    Get Control Signal and calculate on base of it Massflow and Temperature of Massflow.
    """

    # Input
    State = "State"
    ReferenceMaxHeatBuildingDemand = "ReferenceMaxHeatBuildingDemand"
    InitialResidenceTemperature = "InitialResidenceTemperature"
    ResidenceTemperature = "Residence Temperature"
    # MassflowInputTemperature = "MassflowInputTemperature"

    # Output
    InitialWaterBoilerTemperatureOutput = "InitialWaterBoilerTemperatureOutput"
    WaterBoilerTemperatureOutput = "WaterBoilerTemperatureOutput"
    GasPower = "GasPower"
    ThermalPowerDelivered = "ThermalPowerDelivered"
    MaxMassFlow = "MaxMassFlow"

    @utils.measure_execution_time
    def __init__(
        self,
        my_simulation_parameters: SimulationParameters,
        config: GenericGasHeaterWithControllerConfig,
    ) -> None:
        """Construct all the neccessary attributes."""
        super().__init__(
            name=config.name, my_simulation_parameters=my_simulation_parameters
        )
        # =================================================================================================================================
        # Initialization of variables
        self.specific_heat_capacity_of_water_in_joule_per_kilogram_per_celsius = 4184
        self.mass_flow_output_in_kg: float = 0
        self.state_controller: float = 0
        self.max_mass_flow_in_kg_per_second: float = 0
        self.initial_temperature_water_boiler_in_celsius: float = 35
        self.rest_temperature_return_to_water_boiler_in_celsius = (
            self.initial_temperature_water_boiler_in_celsius
        )

        self.initial_temperature_building_in_celsius: float = 0.0
        self.mean_temperature_building_in_celsius: float = 0.0
        self.ref_max_thermal_building_demand_in_watt: float = 0.0

        # Config Values
        self.minimal_thermal_power_in_watt = config.minimal_thermal_power_in_watt
        self.maximal_thermal_power_in_watt = config.maximal_thermal_power_in_watt
        self.maximal_temperature_in_celsius = config.maximal_temperature_in_celsius
        self.temperature_delta_in_celsius = config.temperature_delta_in_celsius

        # =================================================================================================================================
        # Input channels
        self.state_channel: cp.ComponentInput = self.add_input(
            self.component_name, self.State, lt.LoadTypes.ANY, lt.Units.ANY, True
        )

        self.initial_temperature_building_channel: ComponentInput = self.add_input(
            self.component_name,
            self.InitialResidenceTemperature,
            lt.LoadTypes.TEMPERATURE,
            lt.Units.CELSIUS,
            True,
        )
        self.temperature_mean_building_channel: cp.ComponentInput = self.add_input(
            self.component_name,
            self.ResidenceTemperature,
            lt.LoadTypes.TEMPERATURE,
            lt.Units.CELSIUS,
            True,
        )
        self.ref_max_thermal_building_demand_channel: ComponentInput = self.add_input(
            self.component_name,
            self.ReferenceMaxHeatBuildingDemand,
            lt.LoadTypes.HEATING,
            lt.Units.WATT,
            True,
        )

        # Output channels
        self.water_boiler_temperature_output_channel: ComponentOutput = self.add_output(
            self.component_name,
            self.WaterBoilerTemperatureOutput,
            lt.LoadTypes.WATER,
            lt.Units.CELSIUS,
        )

        self.initial_water_boiler_temperature_output_channel: ComponentOutput = (
            self.add_output(
                self.component_name,
                self.InitialWaterBoilerTemperatureOutput,
                lt.LoadTypes.WATER,
                lt.Units.CELSIUS,
            )
        )

        self.gas_power_channel: cp.ComponentOutput = self.add_output(
            self.component_name,
            self.GasPower,
            lt.LoadTypes.HEATING,
            lt.Units.WATT,
        )

        self.max_mass_flow_channel: cp.ComponentOutput = self.add_output(
            self.component_name,
            self.MaxMassFlow,
            lt.LoadTypes.WARM_WATER,
            lt.Units.KG_PER_SEC,
        )

        self.add_default_connections(
            self.get_default_connections_gasheater_controller()
        )

    def get_default_connections_gasheater_controller(
        self,
    ) -> List[cp.ComponentConnection]:
        """Get gas heater controller default connections."""
        log.information("setting controller default connections in GasHeater")
        connections = []
        controller_classname = GasHeaterController.get_classname()
        connections.append(
            cp.ComponentConnection(
                self.State, controller_classname, GasHeaterController.State
            )
        )
        return connections

    def i_prepare_simulation(self) -> None:
        """Prepare the simulation."""
        pass

    def write_to_report(self) -> List[str]:
        """Write a report."""
        lines: List = []
        return lines

    def i_save_state(self) -> None:
        """Save the current state."""
        pass

    def i_restore_state(self) -> None:
        """Restore the previous state."""
        pass

    def i_doublecheck(self, timestep: int, stsv: SingleTimeStepValues) -> None:
        """Doublecheck."""
        pass

    def i_simulate(
        self, timestep: int, stsv: SingleTimeStepValues, force_convergence: bool
    ) -> None:
        """Simulate the gas heater."""
        self.state_controller = stsv.get_input_value(self.state_channel)
        self.initial_temperature_building_in_celsius = stsv.get_input_value(
            self.initial_temperature_building_channel
        )
        self.mean_temperature_building_in_celsius = stsv.get_input_value(
            self.temperature_mean_building_channel
        )
        self.ref_max_thermal_building_demand_in_watt = stsv.get_input_value(
            self.ref_max_thermal_building_demand_channel
        )
        # calculate max mas flow -------------------------------------------------------

        self.max_mass_flow_in_kg_per_second = (
            self.ref_max_thermal_building_demand_in_watt
            / (
                self.specific_heat_capacity_of_water_in_joule_per_kilogram_per_celsius
                * (
                    self.initial_temperature_water_boiler_in_celsius
                    - self.initial_temperature_building_in_celsius
                )
            )
        )
        stsv.set_output_value(
            self.max_mass_flow_channel, self.max_mass_flow_in_kg_per_second
        )
        stsv.set_output_value(
            self.initial_water_boiler_temperature_output_channel,
            self.initial_temperature_water_boiler_in_celsius,
        )

        # -----------------------------------------------------------------------------------

        # gas valve open or closed
        if self.state_controller == 1:
            gas_power_in_watt = self.maximal_thermal_power_in_watt
            # log.information("gas power " + str(gas_power_in_watt))

            temperature_gain_in_celsius = gas_power_in_watt / (
                self.max_mass_flow_in_kg_per_second
                * self.specific_heat_capacity_of_water_in_joule_per_kilogram_per_celsius
            )

            final_temperature_water_boiler_in_celsius = (
                self.rest_temperature_return_to_water_boiler_in_celsius
                + temperature_gain_in_celsius
            )

            stsv.set_output_value(
                self.water_boiler_temperature_output_channel,
                final_temperature_water_boiler_in_celsius,
            )

            stsv.set_output_value(self.gas_power_channel, gas_power_in_watt)

            # log.information(
            #     "water temp "
            #     + str(self.rest_temperature_return_to_water_boiler_in_celsius)
            # )
            # log.information("temperature gain " + str(temperature_gain_in_celsius))
            # log.information(
            #     "final temp water " + str(final_temperature_water_boiler_in_celsius)
            # )

        elif self.state_controller == 0:
            gas_power_in_watt = 0
            temperature_gain_in_celsius = gas_power_in_watt / (
                self.max_mass_flow_in_kg_per_second
                * self.specific_heat_capacity_of_water_in_joule_per_kilogram_per_celsius
            )

            final_temperature_water_boiler_in_celsius = (
                self.rest_temperature_return_to_water_boiler_in_celsius
                + temperature_gain_in_celsius
            )

            stsv.set_output_value(
                self.water_boiler_temperature_output_channel,
                final_temperature_water_boiler_in_celsius,
            )

            stsv.set_output_value(self.gas_power_channel, gas_power_in_watt)

            # log.information("temperature gain " + str(temperature_gain_in_celsius))
            # log.information(
            #     "final temp water " + str(final_temperature_water_boiler_in_celsius)
            # )


class GasHeaterController(cp.Component):

    """Gas Heater Controller.

    It takes data from other
    components and sends signal to the gas heater for
    activation or deactivation.

    Parameters
    ----------
    t_air_heating: float
        Minimum comfortable temperature for residents
    offset: float
        Temperature offset to compensate the hysteresis
        correction for the building temperature change
    mode : int
        Mode index for operation type for this gas heater

    """

    # Inputs
    ResidenceTemperature = "ResidenceTemperature"
    WaterBoilerTemperatureInput = "WaterBoilerTemperatureInput"
    # Outputs
    State = "State"

    # Similar components to connect to:
    # 1. Building
    @utils.measure_execution_time
    def __init__(
        self,
        my_simulation_parameters: SimulationParameters,
        set_heating_temperature_building_in_celsius: float = 0.0,
        set_heating_temperature_water_boiler_in_celsius: float = 0.0,
        offset: float = 0.0,
        mode: int = 1,
    ) -> None:
        """Construct all the neccessary attributes."""
        super().__init__(
            "GasHeaterController", my_simulation_parameters=my_simulation_parameters
        )
        self.state_controller: int = 0
        self.build(
            set_heating_temperature_residence_in_celsius=set_heating_temperature_building_in_celsius,
            set_heating_temperature_water_boiler_in_celsius=set_heating_temperature_water_boiler_in_celsius,
            offset=offset,
            mode=mode,
        )

        self.mean_residence_temperature_channel: cp.ComponentInput = self.add_input(
            self.component_name,
            self.ResidenceTemperature,
            lt.LoadTypes.TEMPERATURE,
            lt.Units.CELSIUS,
            True,
        )
        self.water_boiler_temperature_input_channel: cp.ComponentInput = self.add_input(
            self.component_name,
            self.WaterBoilerTemperatureInput,
            lt.LoadTypes.WATER,
            lt.Units.CELSIUS,
            True,
        )
        self.state_channel: cp.ComponentOutput = self.add_output(
            self.component_name, self.State, lt.LoadTypes.ANY, lt.Units.ANY
        )

        self.add_default_connections(self.get_default_connections_from_building())
        self.controller_gas_valve_mode: str = "close"
        self.previous_controller_gas_valve_mode: str = "close"

    def get_default_connections_from_building(self) -> List[cp.ComponentConnection]:
        """Get building default connections."""
        log.information("setting building default connections in Heatpumpcontroller")
        connections = []
        building_classname = Building.get_classname()
        connections.append(
            cp.ComponentConnection(
                GasHeaterController.ResidenceTemperature,
                building_classname,
                Building.TemperatureMean,
            )
        )
        return connections

    def build(
        self,
        set_heating_temperature_residence_in_celsius: float,
        set_heating_temperature_water_boiler_in_celsius: float,
        offset: float,
        mode: float,
    ) -> None:
        """Build function.

        The function sets important constants and parameters for the calculations.
        """
        # Sth
        self.controller_gas_valve_mode = "off"
        self.previous_controller_gas_valve_mode = self.controller_gas_valve_mode

        # Configuration
        self.set_heating_temperature_residence_in_celsius = (
            set_heating_temperature_residence_in_celsius
        )
        self.set_temperature_water_boiler_in_celsius = (
            set_heating_temperature_water_boiler_in_celsius
        )
        self.offset = offset
        self.mode = mode

    def i_prepare_simulation(self) -> None:
        """Prepare the simulation."""
        pass

    def i_save_state(self) -> None:
        """Save the current state."""
        self.previous_controller_gas_valve_mode = self.controller_gas_valve_mode

    def i_restore_state(self) -> None:
        """Restore the previous state."""
        self.controller_gas_valve_mode = self.previous_controller_gas_valve_mode

    def i_doublecheck(self, timestep: int, stsv: cp.SingleTimeStepValues) -> None:
        """Doublecheck."""
        pass

    def write_to_report(self) -> List[str]:
        """Write important variables to report."""
        lines = []
        lines.append("Gas Heater Controller")
        # todo: add more useful stuff here
        lines.append("tbd")
        return lines

    def i_simulate(
        self, timestep: int, stsv: cp.SingleTimeStepValues, force_convergence: bool
    ) -> None:
        """Simulate the gas heater controller."""
        if force_convergence:
            pass
        else:
            # Retrieves inputs
            mean_residence_temperature_in_celsius = stsv.get_input_value(
                self.mean_residence_temperature_channel
            )
            water_boiler_temperature_in_celsius = stsv.get_input_value(
                self.water_boiler_temperature_input_channel
            )
            # log.information(
            #     "residence temp " + str(mean_residence_temperature_in_celsius)
            # )
            # mode = [1,2] for different controller modes, here mode only 1
            if self.mode == 1:
                self.conditions_for_opening_or_shutting_gas_valve(
                    mean_residence_temperature_in_celsius,
                    water_boiler_temperature_in_celsius,
                )

        if self.controller_gas_valve_mode == "open":
            self.state_controller = 1
        if self.controller_gas_valve_mode == "close":
            self.state_controller = 0
        stsv.set_output_value(self.state_channel, self.state_controller)
        # log.information("gas valve" + self.controller_gas_valve_mode)

    def conditions_for_opening_or_shutting_gas_valve(
        self,
        residence_temperature: float,
        water_boiler_temperature: float,
    ) -> None:
        """Set conditions for the gas valve in gas heater."""
        # offset to close gas valve even before max heating temp is reached (try to imitate anticipator resistor)
        maximum_residence_set_temperature = (
            self.set_heating_temperature_residence_in_celsius
        )
        maxium_water_boiler_set_temperature = (
            self.set_temperature_water_boiler_in_celsius
        )

        if self.controller_gas_valve_mode == "open":
            if (
                residence_temperature >= maximum_residence_set_temperature - self.offset
                or water_boiler_temperature
                >= maxium_water_boiler_set_temperature - self.offset
            ):
                self.controller_gas_valve_mode = "close"
                return

        if self.controller_gas_valve_mode == "close":
            if (
                residence_temperature < maximum_residence_set_temperature
                and water_boiler_temperature < maxium_water_boiler_set_temperature
            ):
                self.controller_gas_valve_mode = "open"
            else:
                self.controller_gas_valve_mode = "close"
