# -*- coding: utf-8 -*-
from typing import Optional
from dataclasses import dataclass
from dataclasses_json import dataclass_json

from utspclient.helpers.lpgdata import (
    TransportationDeviceSets,
    TravelRouteSets,
    Households,
)
from utspclient.helpers.lpgpythonbindings import JsonReference
from hisim.loadtypes import Locations, BuildingCodes, HeatingSystems


@dataclass_json
@dataclass
class ArcheTypeConfig:

    """Defines the system config for the modular household."""

    location: Locations = Locations.AACHEN
    occupancy_profile: JsonReference = Households.CHR01_Couple_both_at_Work
    building_code: BuildingCodes = BuildingCodes.DE_N_SFH_05_GEN_REEX_001_002
    water_heating_system_installed: HeatingSystems = HeatingSystems.HEAT_PUMP
    heating_system_installed: HeatingSystems = HeatingSystems.HEAT_PUMP
    mobility_set: JsonReference = TransportationDeviceSets.Bus_and_two_30_km_h_Cars
    mobility_distance: Optional[
        JsonReference
    ] = TravelRouteSets.Travel_Route_Set_for_10km_Commuting_Distance


# def create_archetype_config_file() -> None:
#     """Component Cost file is created."""

#     config_file=ArcheTypeConfig()
#     config_file_written = config_file.to_json()

#     with open('arche_type_config.json', 'w', encoding="utf-8") as outfile:
#         outfile.write(config_file_written)
