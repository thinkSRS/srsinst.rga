##! 
##! Coptright(c) 2022, 2023 Stanford Research Systems, All right reserved
##! Subject to the MIT License
##! 

from srsgui import Task
from srsgui import ListInput, IntegerInput, InstrumentInput
from srsinst.rga import AnalogScanPlot

# get_rga is imported from the path relative to the .taskconfig file
from instruments import get_rga


class AnalogScanTask(Task):
    """
    Task to run analog scans.
    """

    InstrumentName = 'instrument to control'
    StartMass = 'start mass'
    StopMass = 'stop mass'
    ScanSpeed = 'scan speed'
    StepSize = 'step per AMU'
    IntensityUnit = 'intensity unit'

    # input_parameters values can be changed interactively from GUI
    input_parameters = {
        InstrumentName: InstrumentInput(),
        StartMass: IntegerInput(1, " AMU", 0, 319, 1),
        StopMass: IntegerInput(50, " AMU", 1, 320, 1),
        ScanSpeed: IntegerInput(3, " ", 0, 9, 1),
        StepSize: IntegerInput(20, " steps per AMU", 10, 80, 1),
        IntensityUnit: ListInput(['Ion current (fA)', 'Partial Pressure (Torr)']),
    }

    def setup(self):
        # Get values to use for task  from input_parameters in GUI
        self.params = self.get_all_input_parameters()

        # Get the instrument to use
        self.rga = get_rga(self, self.params[self.InstrumentName])
        self.id_string = self.rga.status.id_string

        # Get logger to use
        self.logger = self.get_logger(__name__)

        self.init_scan()

        # Set up an analog scan plot
        self.ax = self.get_figure().add_subplot(111)
        self.plot = AnalogScanPlot(self, self.ax, self.rga.scan, 'Analog Scan')

        if self.params[self.IntensityUnit] == 0:
            self.conversion_factor = 0.1
            self.plot.set_conversion_factor(self.conversion_factor, 'fA')
        else:
            self.conversion_factor = self.rga.pressure.get_partial_pressure_sensitivity_in_torr()
            self.plot.set_conversion_factor(self.conversion_factor, 'Torr')

    def init_scan(self):
        emission_current = self.rga.ionizer.emission_current
        cem_voltage = self.rga.cem.voltage

        self.logger.info('Emission current: {:.2f} mA CEM HV: {} V'.format(emission_current, cem_voltage))

        self.rga.scan.set_parameters(self.params[self.StartMass],
                                     self.params[self.StopMass],
                                     self.params[self.ScanSpeed],
                                     self.params[self.StepSize])

    def test(self):
        self.set_task_passed(True)
        self.add_details('{}'.format(self.id_string), key='ID')

        while self.is_running():
            try:
                self.rga.scan.get_analog_scan()
            except Exception as e:
                self.set_task_passed(False)
                self.logger.error('{}: {}'.format(e.__class__.__name__, e))
                if not self.rga.is_connected():  # Check if RGA is connected.
                    self.logger.error('"{}" is disconnected'.format(self.params[self.InstrumentName]))
                    break

    def cleanup(self):
        self.logger.info('Task finished')
        self.plot.cleanup()  # Detach callback functions used in the plot


if __name__ == '__main__':
    import time
    import logging

    from srsinst.rga import RGA100 as Rga
    from srsgui.task.callbacks import Callbacks
    import matplotlib.pyplot as plt

    logging.basicConfig(level=logging.INFO)

    task = AnalogScanTask()
    task.set_callback_handler(Callbacks())
    
    rga = Rga('serial', 'COM3', 115200, True)
    # rga = Rga('tcpip','172.25.70.141','admin','admin')

    task.inst_dict = {'dut': rga}
    task.set_input_parameter(task.InstrumentName, 'dut')

    task.figure = plt.figure()
    task.figure_dict = {'plot': task.figure}

    task.start()
    time.sleep(1.0)
    task.stop()
    task.wait()
    plt.show()

