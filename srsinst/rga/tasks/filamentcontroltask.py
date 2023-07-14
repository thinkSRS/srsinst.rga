##! 
##! Copyright(c) 2022, 2023 Stanford Research Systems, All rights reserved
##! Subject to the MIT License
##! 

from srsgui import Task
from srsgui.task.inputs import FloatInput, InstrumentInput

# get_rga is imported from the path relative to the .taskconfig file
from instruments import get_rga


class FilamentControlTask(Task):
    """
    Task to set filament emission current
    """
    # Input parameter name
    InstrumentName = 'instrument to control'
    EmissionCurrent = 'emission current'

    # input_parameters values are used to change interactively from GUI
    input_parameters = {
        InstrumentName: InstrumentInput(),
        EmissionCurrent: FloatInput(1.0, " mA", 0.0, 3.5, 0.02),
    }

    def setup(self):
        # Get the logger to use
        self.logger = self.get_logger(__name__)

        # Get the input parameters from GUI
        self.params = self.get_all_input_parameters()

        # Get rga from the instrument
        self.rga = get_rga(self, self.params[self.InstrumentName])

    def test(self):
        try:
            self.logger.info('Filament emission current before change: {} mA'.format(self.rga.ionizer.emission_current))
            self.logger.info('Setting emission current to {} mA'.format(self.params[self.EmissionCurrent]))

            # Clear filament error before changing emission current
            print('Previous errors: {}'.format(self.rga.status.get_error_text()))

            self.rga.ionizer.emission_current = self.params[self.EmissionCurrent]
            error_bits = self.rga.status.get_errors()
            self.logger.info('Errors after setting emission current:  {}'
                             .format(self.rga.status.get_error_text(error_bits)))
            if 'FL' not in error_bits:
                self.set_task_passed(True)
        except Exception as e:
            self.logger.error(e)

    def cleanup(self):
        self.logger.info('Task finished')


if __name__ == '__main__':
    import logging
    from srsinst.rga import RGA100 as Rga
    from srsgui.task.callbacks import Callbacks
    import matplotlib.pyplot as plt

    logging.basicConfig(level=logging.INFO)
    
    task = FilamentControlTask()
    task.set_callback_handler(Callbacks())

    # rga = Rga('serial', 'COM3', 115200, True)
    rga = Rga('tcpip', '172.25.70.181', 'admin', 'admin')

    rga.comm.set_callbacks(logging.info, logging.info)
    task.inst_dict = {'dut': rga}

    task.figure = plt.figure()
    task.figure_dict = {'plot': task.figure}

    task.set_input_parameter(task.EmissionCurrent, 0.5)
    task.set_input_parameter(task.InstrumentName, 'dut')

    task.start()
    task.wait()

