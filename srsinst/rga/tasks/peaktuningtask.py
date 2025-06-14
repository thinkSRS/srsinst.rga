##!
##! Copyright(c) 2022, 2023, 2025 Stanford Research Systems, All rights reserved
##! Subject to the MIT License
##!

import math
import time
import copy
import numpy as np
from scipy.signal import ricker, find_peaks, find_peaks_cwt, peak_widths, butter, filtfilt

from srsgui import Task
from srsgui import FloatInput, IntegerInput, StringInput

from srsinst.rga.plots.analysis import calculate_baseline

# get_rga is imported from the path relative to the .taskconfig file
from instruments import get_rga


class PeakTuningTask(Task):
    """<b>Change peak tuning parameters (RF slope, RF offset, DC slope, DC offset, and Peak threshold)
manually while scanning.</b><br>
Change parameters to get peak poisiton errors horizontally aligned around 0,
peak widths horizontally aligned around 0.6, and adjust peak threshold to control number of peaks selected. <br>
Before start, select the maximum mass you want to see in the plot.
    """

    RFSlope = 'RF slope'
    RFOffset = 'RF offset'
    DCSlope = 'DC slope'
    DCOffset = 'DC offset'
    PeakThreshold = 'Peak threshold'
    MassLimit = 'Mass upper limit'

    # input_parameters values can be changed interactively from GUI
    input_parameters = {
        MassLimit: IntegerInput(50, " AMU", 20, 200, 1),
        RFSlope: FloatInput(1000.0, "", 600, 1700, .01),
        RFOffset: FloatInput(-0.5, "", -86, 86, 0.001),
        DCSlope: FloatInput(0.0951, "", -0.85, 0.85, .0001),
        DCOffset: IntegerInput(125, "", 0, 255, 1),
        PeakThreshold: FloatInput(1e4, "", 10, 1000000, 1),
    }

    def setup(self):
        self.logger = self.get_logger(__name__)

        # deepcopy need to have separate items  for multi-instances
        # self.input_parameters = copy.deepcopy(AutoPeakTuningTest.input_parameters)
        self.data_dict['x'] = []
        self.data_dict['y'] = []
        self.data_dict['prev_x'] = []
        self.data_dict['prev_y'] = []

        self.mass_limit_value = self.get_input_parameter(self.MassLimit)

        self.rga = get_rga(self)
        print(self.rga.comm.query_text('id?'))  # clear buffer
        self.id_string = self.rga.comm.query_text('id?')

        self.start_value = 1
        self.stop_value = self.mass_limit_value
        self.speed_value = 3
        self.step_value = 20
        self.rga.scan.set_parameters(self.start_value,
                                     self.stop_value,
                                     self.speed_value,
                                     self.step_value)

        self.logger.info('Start: {} Stop: {} Speed: {} Step: {}'.format(
            self.start_value, self.stop_value, self.speed_value, self.step_value))

        self.reps_value = 10000

        self.init_plot()
        self.notify_data_available(self.data_dict)

        self.rga.scan.set_callbacks(self.update_callback, None, self.scan_finished_callback)
        self.rga.scan.set_data_callback_period(0.5)


        # get current tuning parameters and update input_parameters
        self.rf_slope_value = self.rga.qmf.rf.slope
        self.rf_offset_value = self.rga.qmf.rf.offset
        self.dc_slope_value = self.rga.qmf.dc.slope
        self.dc_offset_value = self.rga.qmf.dc.offset

        self.set_input_parameter(self.RFSlope, self.rf_slope_value)
        self.set_input_parameter(self.RFOffset, self.rf_offset_value)
        self.set_input_parameter(self.DCSlope, self.dc_slope_value)
        self.set_input_parameter(self.DCOffset, self.dc_offset_value)
        self.notify_parameter_changed()

        self.logger.info('RF slope: {} RF offset: {} DC slope: {} DC offset {}'.format(
            self.rf_slope_value, self.rf_offset_value,
            self.dc_slope_value, self.dc_offset_value))

        self.add_details('Initial cal values', '\n1')
        self.add_details(f'{self.rf_slope_value:.1f}', 'RF slope')
        self.add_details(f'{self.dc_slope_value}', 'DC slope')
        self.add_details(f'{self.rf_offset_value:.4f}', 'RF offset')
        self.add_details(f'{self.dc_offset_value}', 'DC offset')


    def init_plot(self):
        self.ax = self.figure.subplots(nrows=2, ncols=2, sharex=True,
                                       gridspec_kw={'width_ratios': [3, 2],
                                                    'height_ratios': [1, 1]})
        # Real time data plot
        self.ax[0][0].set_title(self.__class__.__name__)
        self.ax[0][0].set_xlim(self.start_value, self.stop_value)
        self.ax[0][0].set_ylim(-10000, 1000000)
        self.line000, = self.ax[0][0].plot(self.data_dict['x'], self.data_dict['y'])

        # Peak position error plot
        self.ax[0][1].set_title("Peak Pos Error")
        self.ax[0][1].set_ylabel("AMU")
        self.ax[0][1].set_ylim(-0.5, 0.5)

        self.ax[1][0].set_xlabel("Mass (AMU)")
        self.ax[1][0].set_ylabel('Ion Current(0.1 fA)')
        self.ax[1][0].set_ylim(1e2, 1e7)
        self.ax[1][0].set_yscale('log')

        self.ax[1][1].set_title("Peak Width")
        self.ax[1][1].set_ylabel("AMU")
        self.ax[1][1].set_ylim(0.0, 1.5)

    def test(self):
        try:
            x = self.data_dict['x']
            y = self.data_dict['y']
            number_of_iteration = 1000  # self.reps_value
            self.mass_axis = self.rga.scan.get_mass_axis()

            #self.data_dict['x'] = self.mass_axis
            # self.save_result(','.join(map(str, self.data_dict['x'])))

            for i in range(number_of_iteration):
                if not self.is_running():
                    if i > 0:
                        self.set_task_passed(True)
                    break

                self.rga.scan.get_analog_scan()
                self.logger.info('scan {} finished'.format(i))

                # Get value to use for test from input_parameters
                self.rf_slope_value  = self.input_parameters[self.RFSlope].value
                self.rf_offset_value  = self.input_parameters[self.RFOffset].value
                self.dc_slope_value  = self.input_parameters[self.DCSlope].value
                self.dc_offset_value  = self.input_parameters[self.DCOffset].value

                self.rga.qmf.rf.slope = self.rf_slope_value
                self.rga.qmf.rf.offset = self.rf_offset_value
                self.rga.qmf.dc.slope = self.dc_slope_value
                self.rga.qmf.dc.offset = self.dc_offset_value

            self.add_details('Final cal values', '\n2')
            self.add_details(f'{self.rf_slope_value:.1f}', 'RF slope')
            self.add_details(f'{self.dc_slope_value}', 'DC slope')
            self.add_details(f'{self.rf_offset_value:.4f}', 'RF offset')
            self.add_details(f'{self.dc_offset_value}', 'DC offset')

            table_name = 'Mass spectra'
            self.create_table(table_name, 'Mass(AMU)', 'Intensity (0.1 fA)')
            for x, y in zip(self.mass_axis, self.data_dict['prev_y']):
                self.add_data_to_table(table_name, round(x, 2), y)

        except Exception as e:
            self.logger.error(e)

    def update_callback(self, index):
        self.data_dict['x'] = self.mass_axis[:index]
        self.data_dict['y'] = self.rga.scan.spectrum[:index]

        self.line000.set_xdata(self.data_dict['x'])
        self.line000.set_ydata(self.data_dict['y'])
        self.notify_data_available()

    def scan_finished_callback(self):
        try:
            w_height = 0.5
            peak_threshold = self.get_input_parameter(self.PeakThreshold)
            prominence_value = peak_threshold

            x = self.mass_axis
            yr = self.rga.scan.previous_spectrum

            mi = x[0]
            sa = round(1.0 / (x[1] - x[0]))

            signal_offset = calculate_baseline(yr, lam=1e8)

            y = yr - signal_offset

            widths = np.arange(0.8, 8, 0.2)
            peaks_cwt_raw = find_peaks_cwt(y, widths, wavelet=ricker, min_snr=3)

            peaks_cwt = np.array([], dtype=np.int32)
            for i in peaks_cwt_raw:
                if y[i] > peak_threshold:
                    peaks_cwt = np.append(peaks_cwt, i)
            # self.write_text(peaks_cwt_raw)
            # self.write_text(peaks_cwt)

            peaks, properties = find_peaks(y, distance=10, width=9, wlen=41, rel_height=w_height,
                                           height=peak_threshold, prominence=prominence_value)
            widths = peak_widths(y, peaks, rel_height=w_height)

            if len(peaks) == 0:
                self.write_text("No peaks found")
                return
            if len(widths) == 0:
                self.write_text("No width found")
                return

            peak_positions = peaks / sa + mi
            peak_wids = widths[0] / sa
            width_heights = widths[1]
            width_x_min = widths[2] / sa + mi
            width_x_max = widths[3] / sa + mi

            peak_deviation = []
            for i in peak_positions:
                peak_deviation.append(i - round(i))

            peaks_cwt_real = peaks_cwt / sa + mi
            dev = [(i - round(i)) for i in peaks_cwt_real]

            ymin, ymax = self.ax[0][1].get_ylim()
            self.ax[0][1].clear()
            self.ax[0][1].set_title("Peak Pos Error")
            self.ax[0][1].set_ylabel("AMU")
            self.ax[0][1].set_ylim(ymin, ymax)
            self.ax[0][1].plot(peaks_cwt_real, dev, color="#ff0000a0", linewidth=0, marker="o")
            self.ax[0][1].plot(peak_positions, peak_deviation, "bx")

            ymin, ymax = self.ax[1][1].get_ylim()
            self.ax[1][1].clear()
            self.ax[1][1].set_title("Peak Width")
            self.ax[1][1].set_ylabel("AMU")
            self.ax[1][1].set_ylim(ymin, ymax)
            self.ax[1][1].plot(peak_positions, peak_wids, "r+")
            self.ax[1][1].plot(peak_positions, properties['widths'] / sa, "b_")

            ymin, ymax = self.ax[1][0].get_ylim()
            self.ax[1][0].clear()
            self.ax[1][0].set_xlabel("Mass (AMU)")
            self.ax[1][0].set_ylabel('Ion Current(0.1 fA)')
            self.ax[1][0].set_yscale('log')
            self.ax[1][0].set_ylim(ymin, ymax)
            # self.ax[1][0].plot(self.data_dict['prev_x'], self.data_dict['prev_y'],
            self.ax[1][0].plot(x, y, color="#808020", linewidth=1)
            self.ax[1][0].plot(peak_positions, y[peaks], "bx")
            self.ax[1][0].plot(peaks_cwt / sa + mi, y[peaks_cwt], "r.")
            self.ax[1][0].hlines(width_heights, width_x_min, width_x_max, color="red")
            self.ax[1][0].hlines(properties['width_heights'], properties['left_ips'] / sa + mi,
                                 properties['right_ips'] / sa + mi, color="blue")

            self.notify_data_available(self.data_dict)
        except Exception as e:
            self.logger.error('update_on_scan_finished error: {}'.format(e))

    def cleanup(self):
        self.logger.info('Task finished')
