""" For setting the post processing options. """
# clean
from enum import IntEnum


class PostProcessingOptions(IntEnum):

    """Enum class for enabling / disabling parts of the post processing."""

    PLOT_LINE = 1
    PLOT_CARPET = 2
    PLOT_SANKEY = 3
    PLOT_SINGLE_DAYS = 4
    PLOT_BAR_CHARTS = 5
    OPEN_DIRECTORY_IN_EXPLORER = 6
    EXPORT_TO_CSV = 7
    MAKE_NETWORK_CHARTS = 8
    GENERATE_PDF_REPORT = 9
    WRITE_COMPONENTS_TO_REPORT = 10
    WRITE_ALL_OUTPUTS_TO_REPORT = 11
    WRITE_NETWORK_CHARTS_TO_REPORT = 12
    COMPUTE_AND_WRITE_KPIS_TO_REPORT = 13
    PLOT_SPECIAL_TESTING_SINGLE_DAY = 14
    GENERATE_CSV_FOR_HOUSING_DATA_BASE = 15
    INCLUDE_CONFIGS_IN_PDF_REPORT = 16
    INCLUDE_IMAGES_IN_PDF_REPORT = 17
    PROVIDE_DETAILED_ITERATION_LOGGING = 18
    PREPARE_OUTPUTS_FOR_SCENARIO_EVALUATION_WITH_PYAM = 19
