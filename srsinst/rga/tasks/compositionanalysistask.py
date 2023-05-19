##! 
##! Coptright(c) 2022, 2023 Stanford Research Systems, All right reserved
##! Subject to the MIT License
##! 

from srsgui import Task
from srsgui.task.inputs import StringInput, IntegerInput, InstrumentInput

from srsinst.rga.plots.analysis import get_peak_from_analog_scan
from srsinst.rga.plots.analogscanplot import AnalogScanPlot
from srsinst.rga.plots.timeplot import TimePlot

import numpy as np
from scipy.optimize import nnls

# get_rga is imported from the path relative to the .taskconfig file
from instruments import get_rga


class CompositionAnalysisTask(Task):
    """
Task to run analog scans and analyze composition with a list of gas name \
from a gas library file.
    """
    InstrumentName = 'instrument to control'
    StartMass = 'start mass'
    StopMass = 'stop mass'
    ScanSpeed = 'scan speed'
    StepSize = 'step per AMU'
    GasList = 'gas list'

    CompPlot = 'composition_plot'
    DerivedPvsTPlot = 'derived_pvst'

    # input_parameters values can be changed interactively from GUI
    input_parameters = {
        InstrumentName: InstrumentInput(),
        StartMass: IntegerInput(2, " AMU", 0, 319, 1),
        StopMass: IntegerInput(50, " AMU", 1, 320, 1),
        ScanSpeed: IntegerInput(3, " ", 0, 9, 1),
        StepSize: IntegerInput(20, " steps per AMU", 10, 80, 1),
        GasList: StringInput('water, nitrogen, oxygen, hydrogen, argon, carbon dioxide'),
    }

    additional_figure_names = [CompPlot, DerivedPvsTPlot]
    
    def setup(self):
        # Get values to use for task  from input_parameters in GUI
        self.params = self.get_all_input_parameters()
        gas_list = self.params[self.GasList].split(',')
        self.gas_list = [gas.strip().lower() for gas in gas_list]
        print(self.gas_list)

        # Get logger to use
        self.logger = self.get_logger(__name__)

        self.init_scan()

        self.lib = self.read_gas_library()
        self.mat = self.build_coeff_matrix(self.lib, self.params[self.StartMass], 
                                           self.params[self.StopMass], self.gas_list)

        # Set up an derived P vs T plot
        self.init_plot = True
        self.ax_pvst = self.get_figure(self.DerivedPvsTPlot).add_subplot(111)
        self.pvst_plot = TimePlot(self, self.ax_pvst, 'PP vs T', self.gas_list)
        self.pvst_plot.ax.set_yscale('log')

        # Set up a composition analysis plot for the last full analog scan
        self.ax_comp = self.get_figure(self.CompPlot).add_subplot(111)
        self.ax_comp.set_title('Composition analysis')
        self.ax_comp.set_xlabel('Mass (AMU)')
        self.ax_comp.set_ylabel('Intensity (Torr)')
        self.line_comp, = self.ax_comp.plot([], [])
        self.ax_comp.set_xlim(self.params[self.StartMass], self.params[self.StopMass])
        self.ax_comp.set_ylim(1e-12, 1e-7)
        self.bar_x = np.arange(self.params[self.StartMass], self.params[self.StopMass] + 1)
        self.bar_y = np.zeros_like(self.bar_x)

        self.rect_dict = {}
        for gas in self.gas_list:
            self.rect_dict[gas] = self.ax_comp.bar(self.bar_x, self.bar_y, label=gas, alpha=0.6)

        # Setup patch-toggling legend
        self.legend = self.ax_comp.legend()
        self.patchd = {}
        for legpatch, patch_container in zip(self.legend.get_patches(), self.rect_dict.values()):
            legpatch.set_picker(True)
            self.patchd[legpatch] = patch_container
        self.ax_comp.figure.canvas.mpl_connect('pick_event', self.on_pick)

        # Set up an analog scan plot for the test
        self.ax = self.get_figure().add_subplot(111)
        self.plot = AnalogScanPlot(self, self.ax, self.rga.scan, 'Analog Scan')

        self.conversion_factor = self.rga.pressure.get_partial_pressure_sensitivity_in_torr()
        self.plot.set_conversion_factor(self.conversion_factor, 'Torr')
        self.pvst_plot.set_conversion_factor(1.0, 'Torr')

    def on_pick(self, event):
        """
        Toggle patch visibility by clicking a patch in the legend
        """
        legpatch = event.artist
        patch_container = self.patchd[legpatch]
        visible = not patch_container[0].get_visible()
        for patch in patch_container:
            patch.set_visible(visible)
        legpatch.set_alpha(1.0 if visible else 0.3)
        self.request_figure_update(self.ax_comp.figure)

    def init_scan(self):
        # Get the instrument to use
        self.rga = get_rga(self, self.params[self.InstrumentName])
        self.id_string = self.rga.status.id_string
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
                if not self.rga.is_connected():
                    self.logger.error('"{}" is disconnected'.format(self.params[self.InstrumentName]))
                    break

            # manually update self.line_comp
            self.line_comp.set_xdata(self.plot.data['prev_x'])
            corrected_y = self.plot.data['prev_y'] - self.plot.data['prev_baseline']
            self.line_comp.set_ydata(corrected_y)
            if self.init_plot:
                self.ax_comp.set_ylim(self.ax.get_ylim())
                self.init_plot = False
            ys = np.array([get_peak_from_analog_scan(self.plot.data['prev_x'],
                                                     corrected_y, mass)
                          for mass in self.bar_x])

            # Non-negative least square fit
            c, res = nnls(self.mat, ys)
            # c, res, _, _ = np.linalg.lstsq(self.mat, ys, rcond=None)

            self.display_result('', True)
            for n, pp in zip(self.gas_list, c): 
                self.display_result(f'{n}: {pp:.2e} torr')

            self.display_result(f'Residual: {res:.2e}')  # for nnls
            # self.display_result(f'Residual: {np.sqrt(res)[0]:.3e}')  # for lstsq

            self.pvst_plot.add_data(c, True)

            # Update stacked bar graph
            bottom = np.zeros_like(self.bar_x, dtype=np.float64)
            for i, gas in enumerate(self.gas_list):
                ys = self.mat[:, i] * c[i]
                for k, y in enumerate(ys):
                    self.rect_dict[gas][k].set_height(y)
                    self.rect_dict[gas][k].set_y(bottom[k])
                bottom += ys
            self.request_figure_update(self.ax_comp.figure)

    def cleanup(self):
        self.logger.info('Task finished')
        self.plot.cleanup()  # Detach callback functions

    def read_gas_library(self, file_name='gaslib.dat'):
        """
        Read gaslib.dat file as a dict
        """
        d = {}
        with open(file_name, 'rt') as f:
            count = 0
            for line in f:
                line = line.strip()
                if line.startswith('#'):
                    continue
                if len(line.split()) == 0:
                    continue
                rem = count % 3
                if rem == 0:
                    first = line.split('"')
                    name = first[1].lower()
                    sens = first[2].split()
                    sensitivity = float(sens[0])
                    reduction_factor = float(sens[1])
                elif rem == 1:
                    mass = line.split()
                else:
                    inten = line.split()
                    if len(mass) != len(inten):
                        raise IndexError(f'{name} has mal-formatted peak(s).')
                    peaks = [(int(m), float(f)) for m, f in zip(mass, inten)]
                    d[name] = (sensitivity, reduction_factor, peaks)
                count += 1

        self.logger.info('Number of gas read from {}: {}'.format(file_name, count//3))
        return d

    def build_coeff_matrix(self, gas_library, start_mass=1, stop_mass=50, 
                           gas_name_list=('Water', 'Nitrogen', 'Oxygen', 'Carbon dioxide')):
        """
        Build a least square fit coefficient matrix based on mass range  and 
        reference gas histogram spectra.
        """
        mat = np.array([np.zeros(stop_mass - start_mass + 1)])
        for gas in gas_name_list:
            gas_vector = np.array([np.zeros(stop_mass - start_mass + 1)])
            first_sens = gas_library[gas][0]
            second_sens = gas_library[gas][1] / 100.0
            total_sens = first_sens * second_sens
            for peak in gas_library[gas][2]:
                if start_mass <= peak[0] <= stop_mass:
                    gas_vector[0][peak[0] - start_mass] = total_sens * peak[1]
            mat = np.append(mat, gas_vector, axis=0)
        A = mat[1:].T
        return A
 