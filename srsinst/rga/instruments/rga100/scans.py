##! 
##! Copyright(c) 2022, 2023 Stanford Research Systems, All rights reserved
##! Subject to the MIT License
##! 

import time
import numpy as np

from srsgui.inst.communications import Interface, SerialInterface, TcpipInterface
from srsgui.inst.component import Component
from srsgui.inst.commands import IntGetCommand

from .commands import IntNSCommand
from .components import Defaults


class Scans(Component):
    """
    Component for scan setup and data acquisition for RGA100 class
    """

    MaxMass = 100

    initial_mass = IntNSCommand('MI', 'AMU', 1, MaxMass, 1, 1)
    final_mass = IntNSCommand('MF', 'AMU', 1, MaxMass, 1, MaxMass)
    speed = IntNSCommand('NF', '', 0, 7, 1, 4)
    resolution = IntNSCommand('SA', 'points/AMU', 10, 25, 1, 10)
    total_points_analog = IntGetCommand('AP', 'points')
    total_points_histogram = IntGetCommand('HP', 'points')

    def __init__(self, parent):
        super().__init__(parent)

        self.scan_type = None

        self.mass_axis = np.array([], dtype=np.double)
        self.spectrum = np.array([], dtype=np.double)
        self.previous_spectrum = self.spectrum
        self.total_current = 0

        self.analog_scan_command = 'SC1'
        self.histogram_scan_command = 'HS1'
        self.single_mass_scan_command = 'MR{}'
        self.scan_read = self.read_long
        self.scan_convert = self.convert_to_long
        self.check_buffer_overrun = True

        self._data_callback_period = 0.25
        self.set_callbacks()

    def set_callbacks(self, data_available=None, scan_started=None, scan_finished=None):
        """
        Set callback functions to be called when data is available, when a scan is started,
        or when the scan is finished. The measurement program that owns the communication
        interface to the instrument can set the callbacks to run tasks for the events.

        :param  data_available: Optional function called when new scan data is available
        :type data_available: function(available_data_points:int) or None
        :param scan_started: Optional function called when a scan is started
        :type scan_started: function() or None
        :param  scan_finished: Optional function called after the scan is finished
        :type scan_finished: function() or None
        """

        if callable(data_available):
            self._data_available_callback = data_available
        else:
            self._data_available_callback = None

        if callable(scan_started):
            self._scan_started_callback = scan_started
        else:
            self._scan_started_callback = None

        if callable(scan_finished):
            self._scan_finished_callback = scan_finished
        else:
            self._scan_finished_callback = None

    def set_data_callback_period(self, period):
        """
        Set how often data_available_callback function needs to be called during a scan

        It depends on how fast the data display can be redrawn.
        As data size gets larger, it takes loner time to redraw and
        a longer period reduces CPU load to handle display update

        :param int period: time in second
        """
        self._data_callback_period = period

    def get_data_callback_period(self, period):
        """
        Get the current data_available call back period during a scan
        """
        return self._data_callback_period

    def get_max_mass(self):
        """
        Get maximum mass available to a scan

        :rtype: int
        """
        reply = self.comm.query_text('id?')
        return int(reply[6:9])

    def get_parameters(self):
        """
        Get the current scan parameters.

        Returns
        ---------
            (int, int, int, int)
                tuple of (initial_mass, final_mass, scan_speed, steps_per_amu)
        """
        return self.initial_mass, self.final_mass, self.speed, self.resolution

    def set_parameters(self,
                       initial_mass=Defaults.InitialMass,
                       final_mass=65,
                       scan_speed=Defaults.ScanSpeed,
                       steps_per_amu=Defaults.StepsPerAmu):
        """
        Set scan parameters

        Parameters
        -------------
            initial_mass: int, optional
                the initial mass of an analog or histogram scan. The default is 1 AMU
            final_mass: int, optional
                the final mass of an analog or histogram scan. The default is 65 AMU
            scan_speed: int, optional
                0 for the slowest scan, 7 for the fastest scan. The default is 4
            steps_per_amu: int, optional
                steps for 1 AMU in analog scan, between 10 and 25. The default is 10.
                For a histogram scan, it is 1
        """

        self.final_mass = self.get_max_mass()
        self.initial_mass = initial_mass
        self.final_mass = final_mass
        temp = self.final_mass  # To add a pause
        self.speed = scan_speed
        self.resolution = steps_per_amu

    def read_long(self):
        data = self.comm._read_binary(4)
        intensity = self.convert_to_long(data)
        return intensity

    @staticmethod
    def convert_to_long(data):
        num = int.from_bytes(data, 'little', signed=True)
        return num

    def get_mass_axis(self, for_analog_scan=True):
        """
        Calculate mass axis array based on the initial mass, final mass, and steps per amu values
        To be consistent, get_mass_axis after running analog scans or histogram scans.

        :param for_analog_scan: True  if it is for analog scan, False if it is for histogram scan
        :type for_analog_scan: bool
        :rtype: NumPy array
        """

        if for_analog_scan:
            step = 1.0 / self.resolution
        else:
            step = 1.0

        self.mass_axis = np.arange(self.initial_mass, self.final_mass + step / 2.0, step)
        return self.mass_axis

    def get_analog_scan(self):
        """
        Run an analog scan

        Set_scan_parameters() before running
        """
        self.scan_type = 'analog_scan'
        try:
            self.comm.query_text('id?')
            total_points = self.total_points_analog
        except:
            self.comm.query_text('IN0')
            total_points = self.total_points_analog

        self.spectrum = np.zeros([total_points])
        with self.comm.get_lock():
            self.comm._send(self.analog_scan_command)
            if self._scan_started_callback:
                self._scan_started_callback()
            start_time = time.time()
            for index in range(total_points):
                self.spectrum[index] = self.scan_read()
                current_time = time.time()
                if self._data_available_callback and current_time - start_time > self._data_callback_period:
                    self._data_available_callback(index)
                    start_time = current_time
            if self.check_buffer_overrun:
                self.total_current = 0  # if the total current is 0, there are missing bytes.
                last_data = self.comm._recv()  # Read the last
            else:
                self.total_current = 0
                self.total_current = self.scan_read()

        # fix RGA100 comm buffer overflow bug
        if self.check_buffer_overrun:
            length = len(last_data)
            # print('final word: {}'.format(length))
            if length > 4:
                print('Communication buffer reset')
                self.comm.query_text('IN0')    # if there is extra bytes, reset the RGA
            elif length == 4:
                self.total_current = self.convert_to_long(last_data)

        self.previous_spectrum = self.spectrum
        if self._scan_finished_callback:
            self._scan_finished_callback()

        return self.spectrum

    def get_histogram_scan(self):
        """  Run a histogram scan
        """
        self.scan_type = 'histogram_scan'
        total_points = self.total_points_histogram
        self.spectrum = np.zeros([total_points])
        with self.comm.get_lock():
            self.comm._send(self.histogram_scan_command)
            if self._scan_started_callback:
                self._scan_started_callback()

            start_time = time.time()
            for index in range(total_points):
                self.spectrum[index] = self.scan_read()
                current_time = time.time()
                if self._data_available_callback and current_time - start_time > self._data_callback_period:
                    self._data_available_callback(index)
                    start_time = current_time

            self.total_current = 0
            self.total_current = self.scan_read()

        self.previous_spectrum = self.spectrum
        if self._scan_finished_callback:
            self._scan_finished_callback()
        return self.spectrum

    def get_multiple_mass_scan(self, *mass_list):
        """
        Run a multi mass scan

        :param list[int] mass_list: list of masses to measure ion current
        :rtype: NumPy array
        """

        self.scan_type = 'multiple_mass_scan'
        self.spectrum = np.zeros(len(mass_list))
        for index, amu in enumerate(mass_list):
            intensity = self.get_single_mass_scan(amu)
            self.spectrum[index] = intensity
        return self.spectrum

    def get_single_mass_scan(self, mass):
        """
        Measure ion intensity for a single mass

        :param int mass: mass to measure ion current
        :rtype: float
        """

        self.scan_type = 'single_mass_scan'
        intensity = 0
        with self.comm.get_lock():
            self.comm._send(self.single_mass_scan_command.format(mass))
            intensity = self.scan_read()
        return intensity

    def set_mass_lock(self, mass):
        """
        fix mass filter to a mass

        :param int mass: the mass to fix mass filter
        """
        self.comm.send('ML{}'.format(mass))

    def get_partial_pressure_corrected_spectrum(self, spectrum):
        """
        Convert a spectrum in current unit (0.1 fA) to one in Torr
        """
        factor = self._parent.pressure.get_partial_pressure_sensitivity_in_torr()
        return factor * spectrum

    def get_peak_from_analog_scan(self, mass, fit=False):
        x = self.mass_axis
        y = self.spectrum
        distance = 0.5
        m = np.where((x > mass - distance) & (x < mass + distance))[0]
        if len(m) < 5:
            return 0.0
        p = np.max(y[m])
        if not fit:
            return p
        arg = m[0] + np.argmax(y[m])
        x1 = x[arg - 2:arg + 4]
        y1 = y[arg - 2:arg + 4]
        c = np.polyfit(x1, y1, 2)  # fit the points around the max
        roots = np.roots(c)
        pp = (roots[0] + roots[1]) / 2.0  # peak position
        pp = pp.real
        pi = np.polyval(c, pp)  # c[0] + c[1] * pp + c[2] * pp ** 2  # peak intensity
        return pi


class Scans200(Scans):
    MaxMass = 200
    """
    Scans for RGA200
    """
    initial_mass = IntNSCommand('MI', 'AMU', 1, MaxMass, 1, 1)
    final_mass = IntNSCommand('MF', 'AMU', 1, MaxMass, 1, MaxMass)


class Scans300(Scans):
    MaxMass = 300
    """
    Scans for RGA200
    """
    initial_mass = IntNSCommand('MI', 'AMU', 1, MaxMass, 1, 1)
    final_mass = IntNSCommand('MF', 'AMU', 1, MaxMass, 1, MaxMass)
