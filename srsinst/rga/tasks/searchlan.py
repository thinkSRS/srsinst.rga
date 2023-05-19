
from srsgui import Task
from srsgui.task.inputs import ListInput
from srsinst.rga import SICP


class SearchLanTask(Task):
    """Search for RGAs on the local area network (LAN) using SICP.
It may not work if a computer firewall blocks UDP port 818 used for broadcast.
    """

    # Input parameter name
    DisplayOption = 'display option'

    # input_parameters values are used to change interactively from GUI
    input_parameters = {
        DisplayOption: ListInput(['Short', 'Full']),
    }

    def setup(self):
        # Get the logger to use
        self.logger = self.get_logger(__name__)

        # Get the input parameters from GUI
        self.params = self.get_all_input_parameters()

    def test(self):
        sicp = SICP()
        self.logger.info('SICP search for RGAs started..')
        sicp.find()

        if len(sicp.packet_list) == 0:
            self.logger.info('No RGAs found')
            self.set_task_passed(True)
            return

        self.display_result('\nAvailable RGAs')
        self.display_result('================')
        for p in sicp.packet_list:
            if self.params[self.DisplayOption] == 0:
                self.logger.info('Name: {:20s}, SN: {}, IP: {}, Status: {}'
                                 .format(p.device_name, p.serial_number,
                                         p.convert_to_ip_format(p.ip_address),
                                         p.get_short_status_from_packet()))
            else:
                p.print_info()

            if p.get_short_status_from_packet() == p.ST_AVAILABLE:
                self.display_result('Name: {:20s}, SN: {:10d}, IP: {:16s}'
                                    .format(p.device_name, p.serial_number,
                                            p.convert_to_ip_format(p.ip_address)))
        self.set_task_passed(True)

    def cleanup(self):
        self.logger.info('Search completed')

