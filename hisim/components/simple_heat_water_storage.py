"""Heating Water Storage Module."""
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
from hisim.simulationparameters import SimulationParameters
from hisim.components.configuration import PhysicsConfig
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
class HeatingWaterStorageConfig(cp.ConfigBase):

    """Configuration of the HeatingWaterStorage class."""

    @classmethod
    def get_main_classname(cls):
        """Return the full class name of the base class."""
        return HeatingWaterStorage.get_full_classname()

    name: str
    volume_heating_water_storage_in_liter: float
    mean_water_temperature_in_storage_in_celsius: float
    cool_water_temperature_in_storage_in_celsius: float
    hot_water_temperature_in_storage_in_celsius: float
    min_water_mixing_time_in_seconds: float

    @classmethod
    def get_default_heatingwaterstorage_config(
        cls,
    ) -> Any:
        """Get a default heatingwaterstorage config."""
        config = HeatingWaterStorageConfig(
            name="HeatingWaterStorage",
            mean_water_temperature_in_storage_in_celsius=50,
            cool_water_temperature_in_storage_in_celsius=40,
            hot_water_temperature_in_storage_in_celsius=60,
            volume_heating_water_storage_in_liter=500,
            min_water_mixing_time_in_seconds=60 * 60
        )
        return config


class HeatingWaterStorageState:

    """HeatingWaterStorageState."""

    def __init__(
        self,
        start_timestep: int,
        mean_water_temperature_in_storage_in_celsius: float,
        cool_water_temperature_in_celsius: float,
        hot_water_temperature_in_celsius: float,
    ) -> None:
        """Construct all the necessary attributes."""
        self.start_timestep = start_timestep
        self.mean_water_temperature_in_storage_in_celsius = (
            mean_water_temperature_in_storage_in_celsius
        )
        self.cool_water_temperature_in_celsius = cool_water_temperature_in_celsius
        self.hot_water_temperature_in_celsius = hot_water_temperature_in_celsius

    def clone(self) -> Any:
        """Save previous state."""
        return HeatingWaterStorageState(
            self.start_timestep,
            mean_water_temperature_in_storage_in_celsius=self.mean_water_temperature_in_storage_in_celsius,
            cool_water_temperature_in_celsius=self.cool_water_temperature_in_celsius,
            hot_water_temperature_in_celsius=self.hot_water_temperature_in_celsius,
        )


class HeatingWaterStorage(cp.Component):

    """HeatingWaterStorage class."""

    # Input

    WaterTemperatureFromHeatDistributionSystem = (
        "WaterTemperatureFromHeatDistributionSystem"
    )
    WaterTemperatureFromHeatGenerator = "WaterTemperaturefromHeatGenerator"
    WaterMassFlowRateFromHeatGenerator = "WaterMassFlowRateFromHeatGenerator"
    WaterMassFlowRateFromHeatDistributionSystem = "WaterMassFlowRateFromHeatDistributionSystem"

    # Output

    MeanWaterTemperatureInWaterStorage = "MeanWaterTemperatureInWaterStorage"

    @utils.measure_execution_time
    def __init__(
        self,
        my_simulation_parameters: SimulationParameters,
        config: HeatingWaterStorageConfig,
    ) -> None:
        """Construct all the neccessary attributes."""
        super().__init__(
            name=config.name, my_simulation_parameters=my_simulation_parameters
        )
        # =================================================================================================================================
        # Initialization of variables
        self.waterstorageconfig = config
        self.state = HeatingWaterStorageState(
            start_timestep=int(0),
            mean_water_temperature_in_storage_in_celsius=self.waterstorageconfig.mean_water_temperature_in_storage_in_celsius,
            cool_water_temperature_in_celsius=self.waterstorageconfig.cool_water_temperature_in_storage_in_celsius,
            hot_water_temperature_in_celsius=self.waterstorageconfig.hot_water_temperature_in_storage_in_celsius,
        )
        self.previous_state = self.state.clone()
        self.seconds_per_timestep = my_simulation_parameters.seconds_per_timestep
        self.min_water_mixing_time_in_timesteps = self.waterstorageconfig.min_water_mixing_time_in_seconds / self.seconds_per_timestep
        self.water_temperature_from_heat_distribution_system_in_celsius: float = (
            self.waterstorageconfig.cool_water_temperature_in_storage_in_celsius
        )
        self.water_temperature_from_heat_generator_in_celsius: float = (
            self.waterstorageconfig.hot_water_temperature_in_storage_in_celsius
        )
        self.mean_water_temperature_in_water_storage_in_celsius: float = 0.0
        self.water_mass_flow_rate_from_heat_generator_in_kg_per_second: float = 0.0
        self.water_mass_flow_rate_from_heat_distribution_system_in_kg_per_second: float = 0.0

        self.build()

        # =================================================================================================================================
        # Input channels

        self.water_temperature_heat_distribution_system_input_channel: ComponentInput = self.add_input(
            self.component_name,
            self.WaterTemperatureFromHeatDistributionSystem,
            lt.LoadTypes.TEMPERATURE,
            lt.Units.CELSIUS,
            True,
        )
        self.water_temperature_heat_generator_input_channel: ComponentInput = (
            self.add_input(
                self.component_name,
                self.WaterTemperatureFromHeatGenerator,
                lt.LoadTypes.TEMPERATURE,
                lt.Units.CELSIUS,
                True,
            )
        )

        self.water_mass_flow_rate_heat_generator_input_channel: ComponentInput = (
            self.add_input(
                self.component_name,
                self.WaterMassFlowRateFromHeatGenerator,
                lt.LoadTypes.WARM_WATER,
                lt.Units.KG_PER_SEC,
                True,
            )
        )

        self.water_mass_flow_rate_heat_distrution_system_input_channel: ComponentInput = (
            self.add_input(
                self.component_name,
                self.WaterMassFlowRateFromHeatDistributionSystem,
                lt.LoadTypes.WARM_WATER,
                lt.Units.KG_PER_SEC,
                True,
            )
        )
        # Output channels

        self.mean_water_temperature_water_storage_output_channel: ComponentOutput = (
            self.add_output(
                self.component_name,
                self.MeanWaterTemperatureInWaterStorage,
                lt.LoadTypes.WATER,
                lt.Units.CELSIUS,
                output_description=f"here a description for {self.MeanWaterTemperatureInWaterStorage} will follow.",
            )
        )

    def i_prepare_simulation(self) -> None:
        """Prepare the simulation."""
        pass

    def write_to_report(self) -> List[str]:
        """Write a report."""
        lines = []
        for config_string in self.waterstorageconfig.get_string_dict():
            lines.append(config_string)
        return lines

    def i_save_state(self) -> None:
        """Save the current state."""
        self.previous_state = self.state.clone()

    def i_restore_state(self) -> None:
        """Restore the previous state."""
        self.state = self.previous_state.clone()

    def i_doublecheck(self, timestep: int, stsv: SingleTimeStepValues) -> None:
        """Doublecheck."""
        pass

    def i_simulate(
        self, timestep: int, stsv: SingleTimeStepValues, force_convergence: bool
    ) -> None:
        """Simulate the heating water storage."""
        start_water_temperature_in_storage_in_celsius = (
            self.state.mean_water_temperature_in_storage_in_celsius
        )
        # Get inputs --------------------------------------------------------------------------------------------------------
        self.water_temperature_from_heat_distribution_system_in_celsius = (
            stsv.get_input_value(
                self.water_temperature_heat_distribution_system_input_channel
            )
        )
        self.water_temperature_from_heat_generator_in_celsius = stsv.get_input_value(
            self.water_temperature_heat_generator_input_channel
        )
        self.water_mass_flow_rate_from_heat_generator_in_kg_per_second = stsv.get_input_value(
            self.water_mass_flow_rate_heat_generator_input_channel
        )
        self.water_mass_flow_rate_from_heat_distribution_system_in_kg_per_second = stsv.get_input_value(
            self.water_mass_flow_rate_heat_distrution_system_input_channel
        )
        if self.water_temperature_from_heat_distribution_system_in_celsius == 0 and self.water_temperature_from_heat_generator_in_celsius == 0:
            """first iteration --> random numbers"""
            self.water_temperature_from_heat_distribution_system_in_celsius = 50
            self.water_temperature_from_heat_generator_in_celsius = 50

        # Calculations ------------------------------------------------------------------------------------------------------

        if timestep >= self.state.start_timestep + self.min_water_mixing_time_in_timesteps:
            self.mean_water_temperature_in_water_storage_in_celsius = self.calculate_mean_water_temperature_in_water_storage(
                water_temperature_from_heat_distribution_system_in_celsius=self.water_temperature_from_heat_distribution_system_in_celsius,
                water_temperature_from_heat_generator_in_celsius=self.water_temperature_from_heat_generator_in_celsius,
                water_mass_flow_rate_from_heat_generator_in_kg_per_second=self.water_mass_flow_rate_from_heat_generator_in_kg_per_second,
                water_mass_flow_rate_from_heat_distribution_system_in_kg_per_second=self.water_mass_flow_rate_from_heat_distribution_system_in_kg_per_second,
                water_mass_in_storage_in_kg=self.water_mass_in_storage_in_kg,
                previous_mean_water_temperature_in_water_storage_in_celsius=start_water_temperature_in_storage_in_celsius,
                seconds_per_timestep=self.seconds_per_timestep,
            )
            self.state = HeatingWaterStorageState(start_timestep=timestep,
                                          mean_water_temperature_in_storage_in_celsius=self.mean_water_temperature_in_water_storage_in_celsius,
                                          cool_water_temperature_in_celsius=self.water_temperature_from_heat_distribution_system_in_celsius,
                                          hot_water_temperature_in_celsius=self.water_temperature_from_heat_generator_in_celsius)

        # Set outputs -------------------------------------------------------------------------------------------------------
        # log.information("hws timestep " + str(timestep))
        # log.information("hws cool water temp from hds " + str(self.state.cool_water_temperature_in_celsius))
        # log.information("hws hot water temp from hp " + str(self.state.hot_water_temperature_in_celsius))
        # log.information("hws mean water temp in hws " + str(self.state.mean_water_temperature_in_storage_in_celsius))

        stsv.set_output_value(
            self.mean_water_temperature_water_storage_output_channel,
            self.state.mean_water_temperature_in_storage_in_celsius,
        )

    def build(self):
        """Build function.

        The function sets important constants an parameters for the calculations.
        """
        self.specific_heat_capacity_of_water_in_joule_per_kilogram_per_celsius = (
            PhysicsConfig.water_specific_heat_capacity_in_joule_per_kilogram_per_kelvin
        )
        self.density_water_at_60_degree_celsius_in_kg_per_liter = 0.98
        self.water_mass_in_storage_in_kg = (
            self.density_water_at_60_degree_celsius_in_kg_per_liter
            * self.waterstorageconfig.volume_heating_water_storage_in_liter
        )

    def calculate_mean_water_temperature_in_water_storage(
        self,
        water_temperature_from_heat_distribution_system_in_celsius,
        water_temperature_from_heat_generator_in_celsius,
        water_mass_flow_rate_from_heat_generator_in_kg_per_second,
        water_mass_flow_rate_from_heat_distribution_system_in_kg_per_second,
        water_mass_in_storage_in_kg,
        previous_mean_water_temperature_in_water_storage_in_celsius,
        seconds_per_timestep,
    ):
        """Calculate the mean temperature of the water in the water boiler."""

        mass_of_input_water_flows_from_heat_generator_in_kg = (
            water_mass_flow_rate_from_heat_generator_in_kg_per_second * seconds_per_timestep
        )
        mass_of_input_water_flows_from_heat_distribution_system_in_kg = (
            water_mass_flow_rate_from_heat_distribution_system_in_kg_per_second * seconds_per_timestep
        )
        self.mean_water_temperature_in_water_storage_in_celsius = (
            water_mass_in_storage_in_kg
            * previous_mean_water_temperature_in_water_storage_in_celsius
            + mass_of_input_water_flows_from_heat_generator_in_kg
            * water_temperature_from_heat_generator_in_celsius
            + mass_of_input_water_flows_from_heat_distribution_system_in_kg
            * water_temperature_from_heat_distribution_system_in_celsius
        ) / (
            water_mass_in_storage_in_kg
            + mass_of_input_water_flows_from_heat_generator_in_kg
            + mass_of_input_water_flows_from_heat_distribution_system_in_kg
        )

        return self.mean_water_temperature_in_water_storage_in_celsius
