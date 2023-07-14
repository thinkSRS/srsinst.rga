##! 
##! Copyright(c) 2022, 2023 Stanford Research Systems, All rights reserved
##! Subject to the MIT License
##! 

import time
import logging
from matplotlib.axes import Axes
from srsgui import Task
from srsinst.rga.plots.basescanplot import BaseScanPlot
from srsinst.rga.plots.analysis import calculate_baseline
from srsinst.rga.instruments.rga100.scans import Scans

logger = logging.getLogger(__name__)


class AnalogScanPlot(BaseScanPlot):
    """
    Class to manage an analog scan plot with data generated from the parent task

    parameters
    -----------

        parent: Task
            It uses resources from the parent task

        scan: Scans
            an instance of Scans class in an instance of RGA100 class

        plot_name: str
            name of the plot used as title of the plot and name of the dict for scan data saving

        save_to_file: bool
            to create a table in the data file
    """

    def __init__(self, parent: Task, ax: Axes, scan: Scans, plot_name='', save_to_file=True):
        if not issubclass(type(parent), Task):
            raise TypeError('Invalid parent {} is not a Task subclass'.format(type(parent)))
        if not hasattr(ax, 'figure'):
            raise TypeError('ax has no figure attribute. type: "{}"'.format(type(ax)))

        super().__init__(parent, ax, plot_name, save_to_file)
        self.first_scan = True
        self.conversion_factor = 0.1
        self.unit = 'fA'

        self.scan = scan
        self.data = {'x': [], 'y': [], 'prev_x': [], 'prev_y': [], 'prev_baseline': []}

        self.ax.set_xlabel("Mass (AMU)")
        self.ax.set_ylabel('Intensity ({})'.format(self.unit))
        self.prev_line, = self.ax.plot(self.data['x'], self.data['y'], label='Previous')
        self.line, = self.ax.plot(self.data['x'], self.data['y'], label='Current')
        self.prev_baseline, = self.ax.plot(self.data['x'], self.data['y'], label='Prev. baseline')

        self.ax.set_ylim(1, 10000)

        self.reset()

    def reset(self):

        self.first_scan = True
        self.initial_mass = self.scan.initial_mass
        self.final_mass = self.scan.final_mass
        self.resolution = self.scan.resolution
        self.set_x_axis(self.scan.get_mass_axis(True))

        self.ax.set_xlim(self.initial_mass, self.final_mass, auto=False)
        self.scan.set_callbacks(self.scan_data_available_callback,
                                None,
                                self.scan_finished_callback)

    def scan_data_available_callback(self, index):
        self.data['x'] = self.x_axis[:index]
        self.data['y'] = self.scan.spectrum[:index] * self.conversion_factor
        self.line.set_xdata(self.data['x'])
        self.line.set_ydata(self.data['y'])

        # Tell GUI to redraw the plot
        self.parent.request_figure_update(self.ax.figure)

    def scan_finished_callback(self):
        self.data['x'] = self.x_axis
        self.data['y'] = self.scan.spectrum * self.conversion_factor
        self.data['prev_x'] = self.data['x']
        self.data['prev_y'] = self.data['y']
        self.data['prev_baseline'] = calculate_baseline(self.data['y'], 1e-5, 1e6)

        self.line.set_xdata(self.data['x'])
        self.line.set_ydata(self.data['y'])
        self.prev_line.set_xdata(self.data['prev_x'])
        self.prev_line.set_ydata(self.data['prev_y'])

        self.prev_baseline.set_xdata(self.data['prev_x'])
        self.prev_baseline.set_ydata(self.data['prev_baseline'])

        if self.first_scan:
            self.first_scan = False
            self.ax.margins(x=0.0, y=0.1)
            self.ax.relim()
            self.ax.autoscale()
            self.ax.autoscale_view()

        # Tell GUI to redraw the plot
        self.parent.request_figure_update(self.ax.figure)
        self.save_scan_data(self.scan.spectrum)

    def cleanup(self):
        """
        callback functions should be disconnected when task is finished
        """
        self.scan.set_callbacks(None, None, None)
