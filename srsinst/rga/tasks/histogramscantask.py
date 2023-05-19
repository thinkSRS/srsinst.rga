
import time

from srsgui import Task
from srsgui import ListInput, IntegerInput, InstrumentInput
from srsinst.rga import HistogramScanPlot

# get_rga is imported from the path relative to the .taskconfig file
from instruments import get_rga


class HistogramScanTask(Task):
    """Task to run histogram scans.
    """

    InstrumentName = 'instrument to control'
    StartMass = 'start mass'
    StopMass = 'stop mass'
    ScanSpeed = 'scan speed'
    IntensityUnit = 'intensity unit'

    # input_parameters values can be changed interactively from GUI
    input_parameters = {
        InstrumentName: InstrumentInput(),
        StartMass: IntegerInput(1, " AMU", 0, 319, 1),
        StopMass: IntegerInput(50, " AMU", 1, 320, 1),
        ScanSpeed: IntegerInput(3, " ", 0, 9, 1),
        IntensityUnit: ListInput(['Ion current (fA)', 'Partial Pressure (Torr)']),
    }

    def setup(self):
        self._log_error_detail = False

        # Get values to use for task  from input_parameters in GUI
        self.params = self.get_all_input_parameters()

        # Get logger to use
        self.logger = self.get_logger(__name__)

        self.init_scan()

        # Set up an analog scan plot for the test
        self.ax = self.get_figure().add_subplot(111)
        self.plot = HistogramScanPlot(self, self.ax, self.rga.scan, 'Histogram')

        if self.params[self.IntensityUnit] == 0:
            self.conversion_factor = 0.1
            self.plot.set_conversion_factor(self.conversion_factor, 'fA')
        else:
            self.conversion_factor = self.rga.pressure.get_partial_pressure_sensitivity_in_torr()
            self.plot.set_conversion_factor(self.conversion_factor, 'Torr')
        self.logger.debug('Conversion factor: {:.3e}'.format(self.conversion_factor))

    def init_scan(self):
        # Get the instrument to use
        self.rga = get_rga(self, self.params[self.InstrumentName])
        self.id_string = self.rga.status.id_string
        emission_current = self.rga.ionizer.emission_current
        cem_voltage = self.rga.cem.voltage

        self.logger.info('Emission current: {:.2f} mA CEM HV: {} V'.format(emission_current, cem_voltage))
        self.rga.scan.set_parameters(self.params[self.StartMass],
                                     self.params[self.StopMass],
                                     self.params[self.ScanSpeed])

    def test(self):
        self.set_task_passed(True)
        self.add_details('{}'.format(self.rga.status.id_string), key='ID')

        while self.is_running():
            try:
                self.rga.scan.get_histogram_scan()
            except Exception as e:
                self.set_task_passed(False)
                self.logger.error('{}: {}'.format(e.__class__.__name__, e))
                if not self.rga.is_connected():
                    break

    def cleanup(self):
        self.logger.info('Task finished')


if __name__ == '__main__':
    import logging
    from srsinst.rga import RGA100 as Rga
    import matplotlib.pyplot as plt

    logging.basicConfig(level=logging.INFO)

    task = HistogramScanTask()

    rga = Rga('serial', 'COM3', 115200, True)
    rga.comm.set_callbacks(logging.info, logging.info)
    task.inst_dict = {'dut': rga}

    task.figure = plt.figure()
    task.figure_dict = {'plot': task.figure}

    task.set_input_parameter(task.InstrumentName, 'dut')

    task.start()
    time.sleep(1.0)
    task.stop()
    task.wait()
    plt.show()

