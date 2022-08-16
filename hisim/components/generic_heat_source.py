
# Import packages from standard library or the environment e.g. pandas, numpy etc.
from dataclasses import dataclass
from dataclasses_json import dataclass_json

# Import modules from HiSim
from hisim import component as cp
from hisim import loadtypes as lt
from hisim.simulationparameters import SimulationParameters
from hisim.components.building import Building
from hisim.components import controller_l1_generic_runtime
from hisim import log
__authors__ = "Johanna Ganglbauer - johanna.ganglbauer@4wardenergy.at"
__copyright__ = "Copyright 2021, the House Infrastructure Project"
__credits__ = ["Noah Pflugradt"]
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Vitor Hugo Bellotto Zago"
__email__ = "vitor.zago@rwth-aachen.de"
__status__ = "development"

@dataclass_json
@dataclass
class HeatSourceConfig:
    """
    HeatSource Config
    """
    name: str
    source_weight: int
    fuel : lt.LoadTypes
    power_th : float
    efficiency : float

    def __init__( self,
                  name : str,
                  source_weight : int,
                  fuel : lt.LoadTypes,
                  power_th : float,
                  efficiency : float ):
        self.name = name
        self.source_weight = source_weight
        self.fuel = fuel
        self.power_th = power_th
        self.efficiency = efficiency
            
class HeatSourceState:
    """
    This data class saves the state of the CHP.
    """

    def __init__( self, state : int = 0 ):
        self.state = state
        
    def clone( self ):
        return HeatSourceState( state = self.state )

class HeatSource( cp.Component ):
    """
    District heating implementation. District Heating transmitts heat with given efficiency.
    District heating is controlled with an on/off control oscillating within the comfort temperature band.
    """
    
    # Inputs
    l1_DeviceSignal = "l1_DeviceSignal"

    # Outputs
    ThermalPowerDelivered = "ThermalPowerDelivered"
    FuelDelivered =         "FuelDelivered"

    def __init__( self, my_simulation_parameters: SimulationParameters , config : HeatSourceConfig ):
        """
        Parameters
        ----------
        max_power : int
            Maximum power of district heating.
        efficiency : float
            Efficiency of heat transfer
        """
        
        super( ).__init__( name = 'HeatSource' + str( config.source_weight ), my_simulation_parameters = my_simulation_parameters )
        
        #introduce parameters of district heating
        self.build( config )
        
        # Inputs - Mandatories
        self.l1_DeviceSignalC: cp.ComponentInput = self.add_input(self.ComponentName,
                                                                  self.l1_DeviceSignal,
                                                                  lt.LoadTypes.ON_OFF,
                                                                  lt.Units.BINARY,
                                                                  mandatory = True)
        
        # Outputs 
        self.ThermalPowerDeliveredC : cp.ComponentOutput = self.add_output( self.ComponentName,
                                                                            self.ThermalPowerDelivered,
                                                                            lt.LoadTypes.HEATING,
                                                                            lt.Units.WATT )
        self.FuelDeliveredC: cp.ComponentOutput = self.add_output( self.ComponentName,
                                                                  self.FuelDelivered,
                                                                  self.fuel,
                                                                  lt.Units.ANY )
        
        if config.fuel == lt.LoadTypes.OIL:
            self.FuelDeliveredC.Unit = lt.Units.LITER        
        else:
            self.FuelDeliveredC.Unit = lt.Units.WATT_HOUR
        
        self.add_default_connections( controller_l1_generic_runtime.L1_Controller, self.get_l1_controller_default_connections( ) )
        
    def get_l1_controller_default_connections( self ):
        log.information("setting l1 default connections in HeatPump")
        connections = [ ]
        controller_classname = controller_l1_generic_runtime.L1_Controller.get_classname( )
        connections.append( cp.ComponentConnection( HeatSource.l1_DeviceSignal, controller_classname, controller_l1_generic_runtime.L1_Controller.l1_DeviceSignal ) )
        return connections
    
    @staticmethod
    def get_default_config_heating():
        config = HeatSourceConfig( name = 'HeatSource',
                                   source_weight =  1,
                                   fuel = lt.LoadTypes.ELECTRICITY,
                                   power_th = 6200,
                                   efficiency = 0.9 ) 
        return config
    
    @staticmethod
    def get_default_config_waterheating():
        config = HeatSourceConfig( name = 'HeatSource',
                                   source_weight =  1,
                                   fuel = lt.LoadTypes.DISTRICTHEATING,
                                   power_th = 3000,
                                   efficiency = 0.9 ) 
        return config

    def build( self, config : HeatSourceConfig ):
        """
        Assigns parameters of oil heater to class, and writes them to the report
        """
        self.name = config.name
        self.source_weight = config.source_weight
        self.fuel = config.fuel
        self.power_th = config.power_th
        self.efficiency = config.efficiency
        self.state = HeatSourceState( )
        self.previous_state = HeatSourceState( )
    

    def write_to_report( self ):
        """
        Returns
        -------
        lines : list of strings
            Text to enter report.
        """
        
        lines = []
        lines.append( "Name: {}".format( self.name + str( self.source_weight ) ) )
        lines.append( "Fuel: {}".format( self.fuel ) )
        lines.append( "Power: {:4.0f} kW".format( ( self.power_th ) * 1E-3 ) )
        lines.append( 'Efficiency : {:4.0f} %'.format( ( self.efficiency ) * 100 ) )
        return lines
    
    def i_save_state(self):
        self.previous_state = self.state.clone( )

    def i_restore_state(self):
        self.state = self.previous_state.clone( )

    def i_doublecheck(self, timestep: int, stsv: cp.SingleTimeStepValues ):
        pass
    
    def i_simulate( self, timestep: int, stsv: cp.SingleTimeStepValues,  force_convergence: bool ):
        """
        Performs the simulation of the district heating model.
        """ 
        
        # Load control signal signalC value
        signal = stsv.get_input_value( self.l1_DeviceSignalC )
        
        if signal > 0:
            signal = 1
        else:
            signal = 0
        
        # write values for output time series
        stsv.set_output_value( self.ThermalPowerDeliveredC, signal * self.power_th * self.efficiency )
        if self.fuel == lt.LoadTypes.OIL:
            #conversion from Wh oil to liter oil
            stsv.set_output_value( self.FuelDeliveredC, signal * self.power_th * 1.0526315789474e-4 * self.my_simulation_parameters.seconds_per_timestep / 3.6e3  )
        else:
            stsv.set_output_value( self.FuelDeliveredC, signal * self.power_th * self.my_simulation_parameters.seconds_per_timestep / 3.6e3 )