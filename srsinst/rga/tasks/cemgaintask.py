##! 
##! Copyright(c) 2022, 2023 Stanford Research Systems, All rights reserved
##! Subject to the MIT License
##! 

import sys
import math
import time
import math
import numpy as np

from srsgui import Task
from srsgui import IntegerInput, InstrumentInput

# get_rga is imported from the path relative to the .taskconfig file
from instruments import get_rga


class CEMGainTask(Task):
    """Task to measure CEM gain at different CEM voltage
    """

    InstrumentName = 'instrument to control'
    GainToSet = 'gain to set'
    MassToMeasure = 'mass to measure'
    StartVoltage = 'start cem voltage'
    StopVoltage = 'stop cem voltage'
    StepVoltage = 'step size'
    ScanSpeed = 'scan speed'

    WaitTime = 'wait time'
    Notes = 'notes'

    # input_parameters values can be changed interactively from GUI
    input_parameters = {
        InstrumentName: InstrumentInput(),
        GainToSet: IntegerInput(1000, " ", 100, 1000000, 100),
        MassToMeasure: IntegerInput(28, " AMU", 1, 320, 1),
        ScanSpeed: IntegerInput(3, " ", 0, 7, 1),
        WaitTime: IntegerInput(2, " s", 1, 100, 1),
    }

    def setup(self):
        self.logger = self.get_logger(__name__)

        self.data_dict['x'] = []
        self.data_dict['y'] = []

        self.data_dict['t'] = []  # time
        self.data_dict['i'] = []  # intensity

        # Get value to use for test from input_parameters
        self.params = self.get_all_input_parameters()
        self.mass_to_measure_value = self.get_input_parameter(self.MassToMeasure)
        self.wait_time_value = self.get_input_parameter(self.WaitTime)

        # minimum Faraday cup ion current to run calibration
        self.minimum_intensity = 200.0  # fA

        self.start_voltage_value = 800
        self.stop_voltage_value = 2000
        self.step_voltage_value = 160

        self.init_plot()
        self.init_rga()

    def init_plot(self):
        self.ax1 = self.figure.add_subplot(121)
        self.ax1.set_title(self.__class__.__name__)
        self.ax1.set_xlabel("CEM HV (V)")
        self.ax1.set_ylabel('Gain')

        self.line1, = self.ax1.plot(self.data_dict['x'], self.data_dict['y'])
        self.ax1.set_xlim(self.start_voltage_value, self.stop_voltage_value, auto=False)
        self.ax1.set_ylim(1, 100000, auto=False)
        self.ax1.set_yscale('log')

        self.ax2 = self.figure.add_subplot(122)
        self.ax2.set_title('Ion current measurement')
        self.ax2.set_xlabel("Time (s)")
        self.ax2.set_ylabel('Intensity (0.1fA)')
        self.line2, = self.ax2.plot(self.data_dict['t'], self.data_dict['i'])
        self.ax2.set_xlim(0, self.wait_time_value * 1.2)
        self.ax2.set_ylim(10, 1e9)
        self.ax2.set_yscale('log')

    def init_rga(self):
        self.rga = get_rga(self, self.params[self.InstrumentName])
        print(self.rga.status.id_string)
        self.id_string = self.rga.status.id_string
        self.old_speed = self.rga.scan.speed
        self.old_hv = self.rga.cem.voltage

    def test(self):
        self.rga.scan.speed = self.params[self.ScanSpeed]
        self.rga.cem.voltage = 0

        # Measure Faraday cup ion current as a reference
        rep = 4
        total = self.measure_intensity_with_delay(self.params[self.WaitTime])
        for i in range(rep):
            total += self.measure_intensity_with_delay(0.0)
        fc_intensity = total / (rep + 1)

        if fc_intensity < self.minimum_intensity:  # if smaller than minimum_intensity
            raise ValueError('FC reading {:.2f} fA is smaller than {} fA. Need more intensity to calibrate'.format(
                fc_intensity, self.minimum_intensity))

        self.logger.info('FC reading is {:.2f} fA at {} AMU and NF= {}'.format(
            fc_intensity, self.mass_to_measure_value, self.params[self.ScanSpeed]
        ))

        # Create a table to save data
        table_name = 'Gain vs. HV'
        self.create_table(table_name, 'CEM HV (V)', 'Gain')

        # Loop to measure CEM gains
        current_voltage = self.start_voltage_value
        gain = 0
        while (current_voltage <= self.stop_voltage_value) and \
              (gain < self.params[self.GainToSet]):
            if not self.is_running():
                break
            start_time = time.time()
            elapsed_time = 0
            self.data_dict['t'] = []
            self.data_dict['i'] = []
            self.notify_data_available(self.data_dict)

            self.rga.cem.voltage = current_voltage

            while elapsed_time <= self.params[self.WaitTime]:
                elapsed_time = time.time() - start_time
                intensity = self.rga.scan.get_single_mass_scan(self.mass_to_measure_value) / 10.0
                self.data_dict['t'].append(elapsed_time)
                self.data_dict['i'].append(intensity)
                self.notify_data_available(self.data_dict)

            gain = self.data_dict['i'][-1] / fc_intensity
            gain_ratio = self.params[self.GainToSet] / gain

            self.data_dict['x'].append(current_voltage)
            self.data_dict['y'].append(gain)

            self.notify_data_available(self.data_dict)

            self.add_data_to_table(table_name, round(current_voltage, 0), round(gain, 1))
            self.logger.info(f'CEM voltage: {current_voltage} Gain: {gain:.1f} Gain ratio: {gain_ratio:.1f}')

            # Calculate the next CEM voltage
            if gain_ratio > 20 or gain < 0:
                voltage_ratio = 1.16
            elif gain_ratio > 5:
                voltage_ratio = 1.08
            elif gain_ratio > 2.5:
                voltage_ratio = 1.04
            else:
                voltage_ratio = 1.02
            current_voltage = int(current_voltage * voltage_ratio)

        # Interpolate the CEM voltage from of measured data
        log_gain = math.log10(self.params[self.GainToSet])
        self.data_dict['log_y'] = [math.log10(a) if a > 0 else 0.001 for a in self.data_dict['y']]
        hv_to_set = int(np.interp(log_gain, self.data_dict['log_y'], self.data_dict['x']))
        self.logger.info(f'HV for gain {self.params[self.GainToSet]} : {hv_to_set:.0f}')

        # Measure the gain at the calculated CEM voltage
        measured_gain = self.measure_gain_at_voltage(hv_to_set)
        self.logger.info(f'Measured gain at HV {hv_to_set:.0f} V : {measured_gain:.0f}')

        # If the gain error is larger than 10 %, set it to fail
        error = abs(measured_gain - self.params[self.GainToSet]) / self.params[self.GainToSet]
        if error <= 0.10:
            self.rga.cem.voltage = hv_to_set
            self.rga.cem.stored_gain = round(measured_gain, 1)
            self.rga.cem.stored_voltage = round(hv_to_set)
            self.set_task_passed(True)
            self.add_details(f'Gain at {hv_to_set:.0f} V : {measured_gain:.0f}')
        else:
            self.set_task_passed(False)

    def update(self, data_dict):
        """
        Override Task.update.
        It will run when self.notify_data_available() is called.
        """
        try:
            if not data_dict['t']:
                self.line2, = self.ax2.plot([], [])
            else:
                self.line1.set_xdata(data_dict['x'])
                self.line1.set_ydata(data_dict['y'])

                self.line2.set_xdata(data_dict['t'])
                self.line2.set_ydata(data_dict['i'])
            self.request_figure_update()

        except Exception as e:
            self.logger.error('update error: {}'.format(e))

    def cleanup(self):
        self.rga.scan.speed = self.old_speed
        self.rga.cem.voltage = self.old_hv
        self.rga.query_int('HV0')
        self.logger.info('Cleaned up')

    def measure_gain_at_voltage(self, voltage):
        self.rga.cem.voltage = 0
        time.sleep(2.0)
        fc_intensity = self.measure_intensity_with_delay(self.params[self.WaitTime])
        self.rga.cem.voltage = voltage
        time.sleep(2.0)
        cem_intensity = self.measure_intensity_with_delay(self.params[self.WaitTime])
        return cem_intensity / fc_intensity

    def measure_intensity_with_delay(self, delay):
        start_time = time.time()
        elapsed_time = 0
        d = 0.0 if delay < 0.0 else delay
        while elapsed_time <= d:
            elapsed_time = time.time() - start_time
            intensity = self.rga.scan.get_single_mass_scan(self.mass_to_measure_value) / 10.0
        return intensity


if __name__ == '__main__':
    import logging
    import matplotlib.pyplot as plt

    from srsinst.rga import RGA100 as Rga
    from srsgui.task.callbacks import Callbacks

    logging.basicConfig(level=logging.DEBUG)

    task = CEMGainTask()
    task.set_callback_handler(Callbacks())

    rga = Rga('serial', 'COM3', 115200, True)
    # rga = Rga('tcpip','172.25.70.141','admin','admin')
    rga.comm.set_callbacks(logging.info, logging.info)
    task.inst_dict = {'dut': rga}

    task.figure = plt.figure()
    task.figure_dict = {'plot': task.figure}

    task.set_input_parameter(task.GainToSet, 500)
    
    task.start()
    task.wait()
    task.update(task.data_dict)
    plt.show()

