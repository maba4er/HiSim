"""Result Path Provider Module."""

# clean
import os
import datetime
import enum
from typing import Any, Optional

from hisim.sim_repository_singleton import SingletonMeta


class ResultPathProviderSingleton(metaclass=SingletonMeta):

    """ResultPathProviderSingleton class.

    According to your storting options and your input information a result path is created.
    """

    def __init__(
        self,
    ):
        """Initialize the class."""

        self.datetime_string: str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    def set_important_result_path_information(
        self,
        module_directory: str,
        model_name: str,
        variant_name: Optional[str],
        sorting_option: Any,
    ) -> None:
        """Set important result path information."""
        self.set_base_path(module_directory=module_directory)
        self.set_model_name(model_name=model_name)
        self.set_variant_name(variant_name=variant_name)
        self.set_sorting_option(sorting_option=sorting_option)

    def set_base_path(self, module_directory) -> None:
        """Set base path."""
        self.base_path: str = os.path.join(module_directory, "results")

    def set_model_name(self, model_name) -> None:
        """Set model name."""
        self.model_name = model_name

    def set_variant_name(self, variant_name) -> None:
        """Set variant name."""
        if variant_name is None:
            variant_name = ""
        self.variant_name = variant_name

    def set_sorting_option(self, sorting_option) -> None:
        """Set sorting option."""
        self.sorting_option = sorting_option

    def set_time_resolution(self, time_resolution_in_seconds) -> None:
        """Set time resolution."""
        self.time_resolution_in_seconds = time_resolution_in_seconds

    def set_simulation_duration(self, simulation_duration_in_days) -> None:
        """Set simulation duration."""
        self.simulation_duration_in_days = simulation_duration_in_days

    def get_result_directory_name(self) -> str:  # *args
        """Get the result directory path."""

        if self.sorting_option == SortingOptionEnum.DEEP:
            path = os.path.join(
                self.base_path, self.model_name, self.variant_name, self.datetime_string
            )
        elif self.sorting_option == SortingOptionEnum.MASS_SIMULATION:
            # schauen ob verzeichnis schon da und aufsteigende nummer anängen
            idx = 1
            path = os.path.join(
                self.base_path, self.model_name, self.variant_name + "_" + str(idx)
            )
            while os.path.exists(path):
                idx = idx + 1
                path = os.path.join(
                    self.base_path, self.model_name, self.variant_name + "_" + str(idx)
                )
        elif self.sorting_option == SortingOptionEnum.FLAT:
            path = os.path.join(
                self.base_path,
                self.model_name + "_" + self.variant_name + "_" + self.datetime_string,
            )
        return path


class SortingOptionEnum(enum.Enum):

    """A SortingOptionEnum class."""

    DEEP = 1
    MASS_SIMULATION = 2
    FLAT = 3
