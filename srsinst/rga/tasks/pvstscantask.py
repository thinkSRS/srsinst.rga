##! 
##! Copyright(c) 2022, 2023 Stanford Research Systems, All rights reserved
##! Subject to the MIT License
##! 

from srsgui import Task
from srsgui.task.inputs import ListInput, IntegerInput, StringInput, InstrumentInput

from srsinst.rga.plots.timeplot import TimePlot

# get_rga is imported from the path relative to the .taskconfig file
from instruments import get_rga


class PvsTScanTask(Task):
    """Task to measure continuously ion intensity for multiple masses
    """
    InstrumentName = 'instrument to control'
    MassesToMeasure = 'masses to measure'
    ScanSpeed = 'scan speed'
    IntensityUnit = 'intensity unit'

    # input_parameters values can be changed interactively from GUI
    input_parameters = {
        InstrumentName: InstrumentInput(),
        MassesToMeasure: StringInput("2, 18, 28, 44"),
        ScanSpeed: IntegerInput(3, " ", 0, 9, 1),
        IntensityUnit: ListInput(['Ion current (fA)', 'Partial Pressure (Torr)']),
    }

    def setup(self):
        # Get values to use for task  from input_parameters in GUI
        self.params = self.get_all_input_parameters()

        # Get logger to use
        self.logger = self.get_logger(__name__)

        self.mass_list = list(map(int, self.params[self.MassesToMeasure].split(',')))
        self.rga = get_rga(self, self.params[self.InstrumentName])
        self.id_string = self.rga.status.id_string
        self.rga.scan.speed = self.params[self.ScanSpeed]        
        emission_current = self.rga.ionizer.emission_current
        cem_voltage = self.rga.cem.voltage
        self.logger.info('Emission current: {:.2f} mA CEM HV: {} V'.format(emission_current, cem_voltage))

        # Set a time plot
        self.ax = self.get_figure().add_subplot(111)
        key_list = list(map(str, self.mass_list))
        self.plot = TimePlot(self, self.ax, 'P vs T Scan', key_list)
        self.plot.ax.set_yscale('log')

        if self.params[self.IntensityUnit] == 0:
            self.conversion_factor = 0.1
            self.plot.set_conversion_factor(self.conversion_factor, 'fA')
        else:
            self.conversion_factor = self.rga.pressure.get_partial_pressure_sensitivity_in_torr()
            self.plot.set_conversion_factor(self.conversion_factor, 'Torr')

    def test(self):
        while self.is_running():
            intensity_list = self.rga.scan.get_multiple_mass_scan(*self.mass_list)
            self.plot.add_data(intensity_list, True)

    def cleanup(self):
        pass
    
