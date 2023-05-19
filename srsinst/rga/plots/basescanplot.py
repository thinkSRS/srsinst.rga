
import time
import logging
from matplotlib.axes import Axes
from srsgui import Task

logger = logging.getLogger(__name__)


class BaseScanPlot:
    def __init__(self, parent: Task, ax: Axes, plot_name='', save_to_file=False):
        self.type = self.__class__.__name__
        self.parent = parent
        self.ax = ax
        self.name = plot_name.strip()

        self.conversion_factor = 1
        self.unit = ''

        self.save_to_file = False
        if hasattr(self.parent, 'session_handler') and self.parent.session_handler:
            self.save_to_file = save_to_file
        else:
            logger.error('parent has no session_handler')

        self.mass_axis = []
        self.data = {}

        self.round_float_resolution = 4
        self.header_saved = False
        self.initial_time = time.time()

        self.ax.set_title(self.name)

    def set_conversion_factor(self, factor=0.1, unit='fA'):
        old_factor = self.conversion_factor
        self.conversion_factor = factor
        self.unit = unit
        if self.parent:
            self.parent.add_details(' {:.4e} '.format(self.conversion_factor), 'Conversion factor')
            self.parent.add_details(' {} '.format(self.unit), 'Converted unit')

        factor_ratio = self.conversion_factor / old_factor
        bottom, top = self.ax.get_ylim()
        self.ax.set_ylim(bottom * factor_ratio, top * factor_ratio)
        self.ax.set_ylabel('Intensity ({})'.format(self.unit))

    def set_x_axis(self, x_axis):
        self.x_axis = x_axis
        self.ax.set_xlim(min(self.x_axis), max(self.x_axis))

    def save_scan_data(self, data_list):
        if not self.save_to_file:
            return
        if not self.header_saved:
            self.parent.session_handler.add_dict_to_file(self.name, self.get_plot_info())
            self.parent.create_table_in_file(self.name, 'Elapsed time', *map(self.round_float, self.x_axis))
            self.header_saved = True

        # write the spectrum in to the data file
        elapsed_time = self.round_float(time.time() - self.initial_time)
        # timestamp = datetime.now().strftime('%H:%M:%S')
        self.parent.add_to_table_in_file(self.name, elapsed_time, *data_list)

    def round_float(self, number):
        # set the resolution of the number with self.round_float_resolution
        fmt = '{{:.{}e}}'.format(self.round_float_resolution)
        return float(fmt.format(number))

    def get_plot_info(self):
        return {
            'type': self.type,
            'name': self.name,
            'xunit': 'AMU',
            'yunit': self.unit,
            'axes_title': self.ax.get_title(),
            'axes_xlabel': self.ax.get_xlabel(),
            'axes_ylabel': self.ax.get_ylabel(),
            'axes_xlim': self.ax.get_xlim(),
            'axes_ylim': self.ax.get_ylim(),
            'axes_xsclae': self.ax.get_xscale(),
            'axes_yscale': self.ax.get_yscale(),
        }

    def cleanup(self):
        raise NotImplementedError('cleanup is not implemented')
