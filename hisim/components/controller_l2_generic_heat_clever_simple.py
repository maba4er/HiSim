# -*- coding: utf-8 -*-

# Generic/Built-in
import numpy as np
from typing import Optional

# Owned
import hisim.utils as utils
from hisim import component as cp
from hisim.loadtypes import LoadTypes, Units
from hisim.simulationparameters import SimulationParameters
from hisim.components import controller_l1_generic_runtime
from hisim.components.building import Building
from hisim.components import generic_dhw_boiler_without_heating
from hisim import log

from dataclasses import dataclass
from dataclasses_json import dataclass_json

__authors__ = "edited Johanna Ganglbauer"
__copyright__ = "Copyright 2021, the House Infrastructure Project"
__credits__ = ["Noah Pflugradt"]
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Vitor Hugo Bellotto Zago"
__email__ = "vitor.zago@rwth-aachen.de"
__status__ = "development"


@dataclass_json
@dataclass
class L2Config:
    """
    L2 Config
    """
    name : str
    source_weight : int
    T_min_heating : float
    T_max_heating : float
    T_tolerance : float
    P_threshold : float
    cooling_considered : bool
    T_min_cooling : Optional[float]
    T_max_cooling : Optional[float]
    heating_season_begin : Optional[int]
    heating_season_end : Optional[int]

    def __init__( self,
                  name : str,
                  source_weight : int,
                  T_min_heating : float,
                  T_max_heating : float,
                  T_tolerance : float,
                  P_threshold : float,
                  cooling_considered : bool,
                  T_min_cooling : Optional[float],
                  T_max_cooling : Optional[float],
                  heating_season_begin : Optional[int],
                  heating_season_end : Optional[int] ):
        self.name = name
        self.source_weight = source_weight
        self.T_min_heating = T_min_heating
        self.T_max_heating = T_max_heating
        self.T_tolerance = T_tolerance
        self.P_threshold = P_threshold
        self.cooling_considered = cooling_considered
        self.T_min_cooling = T_min_cooling
        self.T_max_cooling = T_max_cooling
        self.heating_season_begin = heating_season_begin
        self.heating_season_end = heating_season_end

class L2_ControllerState:
    """
    This data class saves the state of the heat pump.
    """

    def __init__( self, timestep_actual : int = -1, state : int = 0, compulsory : int = 0, count : int = 0 ):
        self.timestep_actual = timestep_actual
        self.state = state
        self.compulsory = compulsory
        self.count = count
        
    def clone( self ):
        return L2_ControllerState( timestep_actual = self.timestep_actual, state = self.state, compulsory = self.compulsory, count = self.count )
    
    def is_first_iteration( self, timestep ):
        if self.timestep_actual + 1 == timestep:
            self.timestep_actual += 1
            self.compulsory = 0
            self.count = 0
            return True
        else:
            return False
        
    def is_compulsory( self ):
        if self.count <= 1:
            self.compulsory = 0
        else:
            self.compulsory = 1
        
    
    def activate( self ):
        self.state = 1
        self.compulsory = 1
        self.count += 1
        
    def deactivate( self ):
        self.state = 0
        self.compulsory = 1
        self.count += 1

class L2_Controller( cp.Component ):
    
    """ L2 heat pump controller. Processes signals ensuring comfort temperature of building.
    Gets available surplus electricity and the temperature of the storage or building to control as input,
    and outputs control signal 0/1 for turn off/switch on based on comfort temperature limits and available electricity.
    It optionally has different modes for cooling and heating selected by the time of the year.

    Parameters
    --------------
    source_weight : int, optional
        Weight of component, relevant if there is more than one component of same type, defines hierachy in control. The default is 1.
    T_min_heating: float, optional
        Minimum comfortable temperature for residents during heating period, in °C. The default is 19 °C.
    T_max_heating: float, optional
        Maximum comfortable temperature for residents during heating period, in °C. The default is 23 °C.
    T_tolerance : float, optional
        Temperature difference the building may go below or exceed the comfort temperature band with, because of recommendations from L3. The default is 1 °C.
    P_threshold : float, optional
        Estimated power to drive heat source. The defauls is 1500 W.
    T_min_cooling: float, optional
        Minimum comfortable temperature for residents during cooling period, in °C. The default is 23 °C.
    T_max_cooling: float, optional
        Maximum comfortable temperature for residents during cooling period, in °C. The default is 26 °C.
    heating_season_begin : int, optional
        Day( julian day, number of day in year ), when heating season starts - and cooling season ends. The default is 270.
    heating_season_end : int, optional
        Day( julian day, number of day in year ), when heating season ends - and cooling season starts. The default is 150.
    """
    # Inputs
    ReferenceTemperature = "ReferenceTemperature"
    ElectricityTarget = "ElectricityTarget"
    l1_RunTimeSignal = "l1_RunTimeSignal"

    # Outputs
    l2_DeviceSignal = "l2_DeviceSignal"
    
    # #Forecasts
    # HeatPumpLoadForecast = "HeatPumpLoadForecast"

    # Similar components to connect to:
    # 1. Building
    # 2. HeatPump
    
    @utils.measure_execution_time
    def __init__( self, my_simulation_parameters : SimulationParameters, config = L2Config ):
                  
        super().__init__( config.name + str( config.source_weight ), my_simulation_parameters = my_simulation_parameters )
        self.build( config )
        
        #Component Outputs
        self.l2_DeviceSignalC: cp.ComponentOutput = self.add_output(self.ComponentName,
                                                                    self.l2_DeviceSignal,
                                                                    LoadTypes.ON_OFF,
                                                                    Units.BINARY)

        #Component Inputs
        self.ReferenceTemperatureC: cp.ComponentInput = self.add_input(self.ComponentName,
                                                                       self.ReferenceTemperature,
                                                                       LoadTypes.TEMPERATURE,
                                                                       Units.CELSIUS,
                                                                       mandatory = True)
        self.l1_RunTimeSignalC: cp.ComponentInput = self.add_input(self.ComponentName,
                                                                   self.l1_RunTimeSignal,
                                                                   LoadTypes.ANY,
                                                                   Units.ANY,
                                                                   mandatory = False)
        
        self.add_default_connections( Building, self.get_building_default_connections( ) )
        self.add_default_connections( generic_dhw_boiler_without_heating.Boiler, self.get_boiler_default_connections( ) )
        self.add_default_connections( controller_l1_generic_runtime.L1_Controller, self.get_l1_default_connections( ) )
        
        self.ElectricityTargetC : cp.ComponentInput = self.add_input( self.ComponentName,
                                                                      self.ElectricityTarget,
                                                                      LoadTypes.ELECTRICITY,
                                                                      Units.WATT,
                                                                      mandatory = True )

    def get_building_default_connections( self ):
        log.information("setting building default connections in L2 Controller")
        connections = [ ]
        building_classname = Building.get_classname( )
        connections.append( cp.ComponentConnection( L2_Controller.ReferenceTemperature, building_classname, Building.TemperatureMean ) )
        return connections
    
    def get_boiler_default_connections( self ):
        log.information("setting boiler default connections in L2 Controller")
        connections = [ ]
        boiler_classname = generic_dhw_boiler_without_heating.Boiler.get_classname( )
        connections.append( cp.ComponentConnection( L2_Controller.ReferenceTemperature, boiler_classname, generic_dhw_boiler_without_heating.Boiler.TemperatureMean ) )
        return connections
    def get_l1_default_connections( self ):
        log.information("setting L1 default connections in L2 Controller")
        connections = [ ]
        l1_classname = controller_l1_generic_runtime.L1_Controller.get_classname( )
        connections.append( cp.ComponentConnection( L2_Controller.l1_RunTimeSignal, l1_classname, controller_l1_generic_runtime.L1_Controller.l1_RunTimeSignal ) )
        return connections
    
    @staticmethod
    def get_default_config_heating():
        config = L2Config( name = 'L2HeatPump',
                           source_weight =  1,
                           T_min_heating = 20.0,
                           T_max_heating = 22.0,
                           T_tolerance = 1.0,
                           P_threshold = 1500,
                           cooling_considered = True,
                           T_min_cooling = 23.0,
                           T_max_cooling = 25.0,
                           heating_season_begin = 270,
                           heating_season_end = 150 ) 
        return config
    
    @staticmethod
    def get_default_config_waterheating():
        config = L2Config( name = 'L2HeatPump',
                           source_weight =  1,
                           T_min_heating = 50.0,
                           T_max_heating = 80.0,
                           T_tolerance = 5.0,
                           P_threshold = 1500,
                           cooling_considered = False,
                           T_min_cooling = None,
                           T_max_cooling = None,
                           heating_season_begin = None,
                           heating_season_end = None ) 
        return config

    def build( self, config ): 
        self.name = config.name
        self.source_weight = config.source_weight   
        self.T_min_heating = config.T_min_heating
        self.T_max_heating = config.T_max_heating
        self.T_tolerance = config.T_tolerance
        self.P_threshold = config.P_threshold
        self.cooling_considered = config.cooling_considered
        if self.cooling_considered:
            self.T_min_cooling = config.T_min_cooling
            self.T_max_cooling = config.T_max_cooling
            self.heating_season_begin = config.heating_season_begin * 24 * 3600 / self.my_simulation_parameters.seconds_per_timestep
            self.heating_season_end = config.heating_season_end * 24 * 3600 / self.my_simulation_parameters.seconds_per_timestep
        self.state = L2_ControllerState( )
        self.previous_state = L2_ControllerState( )
        
    def control_cooling( self, T_control, T_min_cooling, T_max_cooling, l3state ):
        if T_control > T_max_cooling:
            #start cooling if temperature exceeds upper limit
            self.state.activate( )
            self.previous_state.activate( )

        elif T_control < T_min_cooling:
            #stop cooling if temperature goes below lower limit
            self.state.deactivate( )
            self.previous_state.deactivate( )

        else:
            if self.state.compulsory == 1:
                #use previous state if it is compulsory
                pass
            elif self.ElectricityTargetC.SourceOutput is not None:
                #use recommendation from l3 if available and not compulsory
                self.state.state = l3state
            else:
                #use previous state if l3 was not available
                self.state = self.previous_state.clone( )
                
    def control_heating( self, T_control, T_min_heating, T_max_heating, l3state ):
        if T_control > T_max_heating:
            #stop heating if temperature exceeds upper limit
            self.state.deactivate( )
            self.previous_state.deactivate( )

        elif T_control < T_min_heating:
            #start heating if temperature goes below lower limit
            self.state.activate( )
            self.previous_state.activate( )
        else:
            if self.state.compulsory == 1:
                #use previous state if it compulsory
                pass
            elif self.ElectricityTargetC.SourceOutput is not None:
                #use recommendation from l3 if available and not compulsory
                self.state.state = l3state
            else:
                #use revious state if l3 was not available
                self.state = self.previous_state.clone( )

    def i_save_state(self):
        self.previous_state = self.state.clone( )

    def i_restore_state(self):
        self.state = self.previous_state.clone( )

    def i_doublecheck(self, timestep: int, stsv: cp.SingleTimeStepValues):
        pass

    def i_simulate(self, timestep: int, stsv: cp.SingleTimeStepValues,  force_convergence: bool):
        # check demand, and change state of self.has_heating_demand, and self._has_cooling_demand
        T_control = stsv.get_input_value( self.ReferenceTemperatureC )  
        if self.my_simulation_parameters.system_config.predictive == True:
            RunTimeSignal = stsv.get_input_value( self.l1_RunTimeSignalC )
        else:
            RunTimeSignal = 0
        if force_convergence:
            pass
            # if self.cooling_considered:
            #     if timestep < self.heating_season_begin and timestep > self.heating_season_end:
            #         if T_control > ( self.T_max_cooling + self.T_min_cooling ) / 2 :
            #             stsv.set_output_value( self.l2_DeviceSignalC, 1 )
            #         else:
            #             stsv.set_output_value( self.l2_DeviceSignalC, 0 )
            #     else:
            #         if T_control < ( self.T_max_heating + self.T_min_heating ) / 2 :
            #             stsv.set_output_value( self.l2_DeviceSignalC, 1 )
            #         else:
            #             stsv.set_output_value( self.l2_DeviceSignalC, 0 )
                
            # else:
            #     if T_control < ( self.T_max_heating + self.T_min_heating ) / 2 :
            #         stsv.set_output_value( self.l2_DeviceSignalC, 1 )
            #     else:
            #         stsv.set_output_value( self.l2_DeviceSignalC, 0 )
        
        else:
            #get l3 recommendation if available
            if self.ElectricityTargetC.SourceOutput is not None:
                electricity_target = stsv.get_input_value( self.ElectricityTargetC )
                if electricity_target >= self.P_threshold:
                    l3state = 1
                else:
                    l3state = 0
            
                #reset temperature limits if recommended from l3
                if self.cooling_considered:  
                    if l3state == 1 :
                        if RunTimeSignal > 0:
                            T_min_cooling = self.T_min_cooling - self.T_tolerance
                        else:
                            T_min_cooling = ( self.T_min_cooling + self.T_max_cooling ) / 2
                        T_max_cooling = self.T_max_cooling
                    elif l3state == 0:
                        T_max_cooling = self.T_max_cooling + self.T_tolerance
                        T_min_cooling = self.T_min_cooling 
                        
                if l3state == 1:
                    if RunTimeSignal > 0:
                        T_max_heating = self.T_max_heating + self.T_tolerance
                    else:
                        T_max_heating = ( self.T_min_heating + self.T_max_heating ) / 2
                    T_min_heating = self.T_min_heating
                    self.state.is_compulsory( )
                    self.previous_state.is_compulsory( )
                elif l3state == 0:
                     T_max_heating = self.T_max_heating 
                     T_min_heating = self.T_min_heating - self.T_tolerance
                     self.state.is_compulsory( )
                     self.previous_state.is_compulsory( )
            else:
                T_max_heating = self.T_max_heating 
                T_min_heating = self.T_min_heating
                T_max_cooling = self.T_max_cooling
                T_min_cooling = self.T_min_cooling 
    
            #check if it is the first iteration and reset compulsory and timestep_of_last_activation in state and previous_state
            if self.state.is_first_iteration( timestep ):
                self.previous_state.is_first_iteration( timestep )
            
            if self.cooling_considered:
                #check out during cooling season
                if timestep < self.heating_season_begin and timestep > self.heating_season_end:
                    self.control_cooling( T_control = T_control, T_min_cooling = T_min_cooling, T_max_cooling = T_max_cooling, l3state = l3state )
                #check out during heating season
                else:
                    self.control_heating( T_control = T_control, T_min_heating = T_min_heating, T_max_heating = T_max_heating, l3state = l3state )
                        
            #check out during heating season
            else:
                self.control_heating( T_control = T_control, T_min_heating = T_min_heating, T_max_heating = T_max_heating, l3state = l3state )
            stsv.set_output_value( self.l2_DeviceSignalC, self.state.state )
        
    def write_to_report( self ):
        lines = []
        lines.append("Name: {}".format(self.name + str( self.source_weight ) ) )
        lines.append("upper set temperature: {:4.0f} °C".format( ( self.T_max_heating ) ) )
        lines.append( "lower set temperature: {:4.0f} °C".format( self.T_min_heating ) )
        lines.append( "tolerance: {:4.0f} °C".format( self.T_tolerance))
        return lines

    def prin1t_outpu1t(self, t_m, state):
        log.information("==========================================")
        log.information("T m: {}".format(t_m))
        log.information("State: {}".format(state))