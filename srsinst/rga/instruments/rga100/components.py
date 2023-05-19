
from srsgui import InstException
from srsgui import Component
from srsgui import GetCommand, IntGetCommand

from .commands import FloatNSCommand, BoolSetNSCommand,\
                      RgaIntCommand, RgaFloatCommand, \
                      RgaIonEnergyCommand, RgaTotalPressureCommand, \
                      RgaStoredCEMGainCommand
from .errors import query_errors, fetch_error_descriptions


class Ionizer(Component):
    electron_energy = RgaIntCommand('EE', 'eV', 25, 105, 1, 70)
    ion_energy = RgaIonEnergyCommand('IE', 'eV', 8, 12, 4, 12)
    focus_voltage = RgaIntCommand('VF', 'V', 0, 150, 1, 90)
    emission_current = RgaFloatCommand('FL', 'mA', 0.0, 3.5, 0.01, 2, 1.0)
    """
    For typical operation, set emission current to 1 (mA).
    When the emission current is set to 0, the filament will be turned off
    """

    last_set_status = 0
    """
    RgaCommand returns status byte with set operations
    Check this variable after ionizer set commands 
    """

    def get_parameters(self):
        """
        Get electron energy, ion energy, focus voltage setting values

        Returns
        --------
            tuple
                (electron_energy, ion_energy, focus_voltage)
        """

        return self.electron_energy, self.ion_energy, self.focus_voltage

    def set_parameters(self, electron_energy, ion_energy, focus_voltage):
        """
        Set electron energy, ion energy and focus voltage

        Parameters
        -----------
            electron_energy : int
                electron energy electron impact ionization
            ion_energy : int
                ion energy, 12 eV or 8 eV
            focus_voltage : int
                focus plate voltage

        Returns
        --------
            int
                error status after setting
        """

        self.electron_energy = electron_energy
        self.ion_energy = ion_energy
        self.focus_voltage = focus_voltage
        return self.last_set_status


class Filament(Component):
    last_set_status = 0
    """
    RgaCommand returns status byte with set operations
    Check this value after ionizer set commands 
    """

    def turn_on(self, target_emission_current=1.0):
        """
        Turn on filament to the target emission current

        Parameters
        -----------
            target_emission_current : int, optional
                Default is 1.0 mA

        Returns
        --------
            error_status : int
                Error status byte
        """
        self._parent.ionizer.emission_current = target_emission_current
        return self.last_set_status

    def turn_off(self):
        """
        Turn off the filament
        """
        self._parent.ionizer.emission_current = 0.0
        return self.last_set_status

    def start_degas(self, degas_minute=3):
        """
        Start degas. Subsequent commands are blocked until the degas is over for RGA100.
        """
        print('Degas starting')
        self.comm.query_text_with_long_timeout('DG{}'.format(degas_minute), degas_minute * 65)
        print('Degas finished')

    allow_run_button = [turn_on, turn_off]


class CEM(Component):
    voltage = RgaIntCommand('HV', 'V', 0, 2290, 1, 0)
    stored_voltage = FloatNSCommand('MV', 'V', 0, 2290, 1, 0)

    stored_gain = RgaStoredCEMGainCommand('MG', '', 0, 2000000, 1, 3, 0)
    """ 
    Stored CEM gain. Underlying remote command 'MG' returns 
    the gain divided by 1000. This descriptor generates
    the original value,  1000 times of the raw remote command value.    
     """

    def turn_on(self):
        """
        Set CEM HV to the stored CEM voltage
        """
        self.voltage = self.stored_voltage

    def turn_off(self):
        """
        Set CEM HV to the stored CEM voltage
        """
        self.voltage = 0

    allow_run_button = [turn_on, turn_off]


class Pressure(Component):
    partial_pressure_sensitivity = FloatNSCommand('SP', 'mA/Torr', 0.0, 10.0, 0.001, 2, 0.1)
    """
    Partial pressure sensitivity is used to convert a spectrum 
    in current unit to partial pressure unit. 
    The partial pressure sensitivity in the unit of mA/Torr        
    """

    total_pressure_sensitivity = FloatNSCommand('ST', 'mA/Torr', 0.0, 100.0, 0.001, 2, 0.01)
    """
    Total pressure sensitivity is used to convert total pressure measured   
    in current unit to pressure unit. 
    The total pressure sensitivity in the unit of mA/Torr
    """

    total_pressure_enable = BoolSetNSCommand('TP')
    total_pressure = RgaTotalPressureCommand('TP', 'x 10^-16 A')
    """
    Total pressure measured in  ion current in 0.1 fA 
    """

    def get_total_pressure_in_torr(self):
        factor = 1e-13 / self.total_pressure_sensitivity
        if self._parent.cem.voltage > 10:
            factor /= self._parent.cem.stored_gain
        return self.total_pressure * factor

    def get_partial_pressure_sensitivity_in_torr(self):
        """
        Sensitivity factor is multiplied to a raw ion current value (in 1e-16 A unit)
        to calculate the partial pressure in Torr
        """
        factor = 1e-13 / self.partial_pressure_sensitivity
        if self._parent.cem.voltage > 10:
            factor /= self._parent.cem.stored_gain
        return factor


class QMF(Component):
    class RF(Component):
        slope = FloatNSCommand('RS')
        offset = FloatNSCommand('RI')

    class DC(Component):
        slope = FloatNSCommand('DS')
        offset = FloatNSCommand('DI')

    def __init__(self, parent):
        super().__init__(parent)
        self.rf = QMF.RF(self)
        self.dc = QMF.DC(self)


class Status(Component):
    id_string = GetCommand('ID')
    error_status = IntGetCommand('ER')
    error_ps = IntGetCommand('EP')
    error_detector = IntGetCommand('ED')
    error_qmf = IntGetCommand('EQ')
    error_cem = IntGetCommand('EC')
    error_filament = IntGetCommand('EF')
    error_rs232 = IntGetCommand('EC')

    def get_errors(self):
        """
        Get RGA100 error bits in a string
        Call get_status() with the returned error bis string to get human friendy message

        Returns
        --------
            str
                error bits coded in a string
        """
        return query_errors(self)

    def get_error_text(self, error_bits=''):
        """
        Get human-firendly error message

        Parameters
        -----------
            error_bits : str, optional
                error bits in string obtained with get_errors()
        """
        if error_bits:
            return fetch_error_descriptions(error_bits)
        return fetch_error_descriptions(self.get_errors())
