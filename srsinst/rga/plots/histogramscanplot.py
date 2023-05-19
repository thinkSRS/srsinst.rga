
import logging
import numpy
from matplotlib.axes import Axes
from srsgui import Task
from srsinst.rga.plots.basescanplot import BaseScanPlot

from srsinst.rga.instruments.rga100.scans import Scans



logger = logging.getLogger(__name__)


class HistogramScanPlot(BaseScanPlot):
    def __init__(self, parent: Task, ax: Axes, scan: Scans, plot_name='', save_to_file=True):
        if not issubclass(type(parent), Task):
            raise TypeError('Invalid parent {} is not a Task subclass'.format(type(parent)))
        if not hasattr(ax, 'figure'):
            raise TypeError('ax has no figure attribute. type: "{}"'.format(type(ax)))
        super().__init__(parent, ax, plot_name, save_to_file)

        self.conversion_factor = 0.1
        self.unit = 'fA'

        self.scan = scan
        self.mass_axis = self.scan.get_mass_axis(False)

        x = self.mass_axis
        y = numpy.zeros_like(x)
        self.data = {'x': x, 'y': y, 'prev_x': x, 'prev_y': y}

        self.ax.set_title(plot_name)
        self.ax.set_xlabel("Mass (AMU)")
        self.ax.set_ylim(1, 100000)
        self.ax.set_ylabel('Intensity ({})'.format(self.unit))

        self.prev_rects = self.ax.bar(self.data['x'], self.data['y'])
        self.rects = self.ax.bar(self.data['x'], self.data['y'])

        self.reset()

    def reset(self):
        self.initial_mass = self.scan.initial_mass
        self.final_mass = self.scan.final_mass
        self.set_x_axis(self.scan.get_mass_axis(False))

        self.data['x'] = self.mass_axis
        self.data['y'] = numpy.zeros_like(self.mass_axis)

        self.ax.set_xlim(self.initial_mass, self.final_mass, auto=False)
        self.scan.set_callbacks(self.update_callback,
                                self.scan_started_callback,
                                self.scan_finished_callback)

    # The scan calls this callback when data is available
    def update_callback(self, index):
        i = self.last_index
        while i <= index:
            # Update rectangles for new data
            inten = self.scan.spectrum[i] * self.conversion_factor
            self.rects[i].set_height(inten)
            self.data['y'].append(inten)
            i += 1

        self.last_index = index
        self.parent.request_figure_update(self.ax.figure)

    def scan_started_callback(self):
        self.last_index = 0

        # Initialize the rectangles in the bar plot when a scan started
        for rect1, rect2 in zip(self.prev_rects, self.rects):
            rect1.set_height(rect2.get_height())
        self.data['prev_y'] = self.scan.previous_spectrum * self.conversion_factor

        for rect in self.rects:
            rect.set_height(0)
            self.data['y'] = []

        # Tell GUI to redraw the plot
        self.parent.request_figure_update(self.ax.figure)

    def scan_finished_callback(self):
        self.save_scan_data(self.scan.spectrum)

    def cleanup(self):
        """
        callback functions should be disconnected when task is finished
        """
        self.scan.set_callbacks(None, None, None)
