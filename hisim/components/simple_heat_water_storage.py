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
# from hisim import log


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
    # temperature_of_warm_water_extratcion :float
    # ambient_temperature :float
    water_temperature_in_storage_in_celsius: float

    @classmethod
    def get_default_heatingwaterstorage_config(
        cls,
    ) -> Any:
        """Get a default heatingwaterstorage config."""
        config = HeatingWaterStorageConfig(
            name="HeatingWaterStorage",
            water_temperature_in_storage_in_celsius=40,
            volume_heating_water_storage_in_liter=1000,
        )
        return config


class HeatStorageState:

    """HeatStorageState."""

    def __init__(self, water_temperature_in_storage_in_celsius: float) -> None:
        """Construct all the necessary attributes."""
        self.water_temperature_in_storage_in_celsius = (
            water_temperature_in_storage_in_celsius
        )

    def clone(self) -> Any:
        """Save previous state."""
        return HeatStorageState(
            water_temperature_in_storage_in_celsius=self.water_temperature_in_storage_in_celsius
        )


class HeatingWaterStorage(cp.Component):

    """HeatingWaterStorage class."""

    # Input

    CooledWaterTemperatureFromHeatDistributionSystem = (
        "CooledWaterTemperatureFromHeatDistributionSystem"
    )
    HeatedWaterTemperaturefromHeatGenerator = "HeatedWaterTemperaturefromHeatGenerator"
    MaxWaterMassFlowRate = "MaxWaterMassFlow"

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
        self.state = HeatStorageState(
            self.waterstorageconfig.water_temperature_in_storage_in_celsius
        )
        self.seconds_per_timestep = my_simulation_parameters.seconds_per_timestep
        self.cooled_water_temperature_from_heat_distribution_system_in_celsius: float = (
            0
        )
        self.heated_water_temperature_from_heat_generator_in_celsius: float = 0
        self.max_water_mass_flow_rate_in_kg_per_second: float = 0
        self.mean_water_temperature_in_water_storage_in_celsius: float = 0
        self.mix_water_temperature_from_input_flows_in_celsius: float = 0
        self.build()

        # =================================================================================================================================
        # Input channels

        self.cooled_water_temperature_heat_distribution_system_input_channel: ComponentInput = self.add_input(
            self.component_name,
            self.CooledWaterTemperatureFromHeatDistributionSystem,
            lt.LoadTypes.TEMPERATURE,
            lt.Units.CELSIUS,
            True,
        )
        self.heated_water_temperature_heat_generator_input_channel: ComponentInput = (
            self.add_input(
                self.component_name,
                self.HeatedWaterTemperaturefromHeatGenerator,
                lt.LoadTypes.TEMPERATURE,
                lt.Units.CELSIUS,
                True,
            )
        )

        self.max_water_mass_flow_rate_input_channel: ComponentInput = self.add_input(
            self.component_name,
            self.MaxWaterMassFlowRate,
            lt.LoadTypes.WARM_WATER,
            lt.Units.KG_PER_SEC,
            True,
        )
        # Output channels

        self.mean_water_temperature_water_storage_output_channel: ComponentOutput = (
            self.add_output(
                self.component_name,
                self.MeanWaterTemperatureInWaterStorage,
                lt.LoadTypes.WATER,
                lt.Units.CELSIUS,
            )
        )

    def i_prepare_simulation(self) -> None:
        """Prepare the simulation."""
        pass

    def write_to_report(self) -> List[str]:
        """Write a report."""
        lines: List = []
        lines.append("Heating Water Storage")
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
        """Simulate the heating water storage."""
        start_water_temperature_in_storage_in_celsius = (
            self.state.water_temperature_in_storage_in_celsius
        )
        # Get inputs --------------------------------------------------------------------------------------------------------
        self.cooled_water_temperature_from_heat_distribution_system_in_celsius = (
            stsv.get_input_value(
                self.cooled_water_temperature_heat_distribution_system_input_channel
            )
        )
        self.heated_water_temperature_from_heat_generator_in_celsius = (
            stsv.get_input_value(
                self.heated_water_temperature_heat_generator_input_channel
            )
        )
        self.max_water_mass_flow_rate_in_kg_per_second = stsv.get_input_value(
            self.max_water_mass_flow_rate_input_channel
        )

        # Calculations ------------------------------------------------------------------------------------------------------

        self.calculate_mix_water_temperature_from_input_flows(
            cooled_water_temperature_in_celsius=self.cooled_water_temperature_from_heat_distribution_system_in_celsius,
            heated_water_temperature_in_celsius=self.heated_water_temperature_from_heat_generator_in_celsius,
        )

        self.mean_water_temperature_in_water_storage_in_celsius = self.calculate_mean_water_temperature_in_water_storage(
            mix_water_temperature_from_input_flows_in_celsius=self.mix_water_temperature_from_input_flows_in_celsius,
            mass_flow_rate_water_in_kg_per_second=self.max_water_mass_flow_rate_in_kg_per_second,
            water_mass_in_storage_in_kg=self.water_mass_in_storage_in_kg,
            previous_mean_water_temperature_in_water_storage_in_celsius=start_water_temperature_in_storage_in_celsius,
            seconds_per_timestep=self.seconds_per_timestep,
        )

        # Set outputs -------------------------------------------------------------------------------------------------------

        stsv.set_output_value(
            self.mean_water_temperature_water_storage_output_channel,
            self.mean_water_temperature_in_water_storage_in_celsius,
        )

        self.state.water_temperature_in_storage_in_celsius = (
            self.mean_water_temperature_in_water_storage_in_celsius
        )

    def build(self):
        """Build function.

        The function sets important constants an parameters for the calculations.
        """
        self.specific_heat_capacity_of_water_in_joule_per_kilogram_per_celsius = PhysicsConfig.water_specific_heat_capacity_in_joule_per_kilogram_per_kelvin
        self.density_water_at_60_degree_celsius_in_kg_per_liter = 0.98
        self.water_mass_in_storage_in_kg = (
            self.density_water_at_60_degree_celsius_in_kg_per_liter
            * self.waterstorageconfig.volume_heating_water_storage_in_liter
        )

    def calculate_mix_water_temperature_from_input_flows(
        self,
        cooled_water_temperature_in_celsius,
        heated_water_temperature_in_celsius,
    ):
        """Calculate the mean temperature of the water in the water boiler."""
        # the water mass flow rate is equal and constant
        self.mix_water_temperature_from_input_flows_in_celsius = (
            cooled_water_temperature_in_celsius + heated_water_temperature_in_celsius
        ) / 2

    def calculate_mean_water_temperature_in_water_storage(
        self,
        mix_water_temperature_from_input_flows_in_celsius,
        mass_flow_rate_water_in_kg_per_second,
        water_mass_in_storage_in_kg,
        previous_mean_water_temperature_in_water_storage_in_celsius,
        seconds_per_timestep,
    ):
        """Calculate the mean temperature of the water in the water boiler."""
        # the water mass flow is equal and constant
        mass_of_input_water_flows_in_kg = (
            2 * mass_flow_rate_water_in_kg_per_second * seconds_per_timestep
        )

        self.mean_water_temperature_in_water_storage_in_celsius = (
            water_mass_in_storage_in_kg
            * previous_mean_water_temperature_in_water_storage_in_celsius
            + mass_of_input_water_flows_in_kg
            * mix_water_temperature_from_input_flows_in_celsius
        ) / (water_mass_in_storage_in_kg + mass_of_input_water_flows_in_kg)

        return self.mean_water_temperature_in_water_storage_in_celsius
