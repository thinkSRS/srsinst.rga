##! 
##! Coptright(c) 2022, 2023 Stanford Research Systems, All right reserved
##! Subject to the MIT License
##! 


"""
Module contains the main class for operation of SRS RGA100 series
"""

from srsgui import Instrument
from srsgui import InstCommunicationError, \
                   InstLoginFailureError, InstIdError

from srsgui import SerialInterface, TcpipInterface
from srsgui import FindListInput, Ip4Input, StringInput, PasswordInput, IntegerInput

from .scans import Scans, Scans200, Scans300
from .components import QMF, Ionizer, Filament, CEM, Pressure, Status


class Defaults:
    """
    SRS RGA default values after reset
    """
    ElectronEnergy = 70
    IonEnergy = 12
    FocusVoltage = 90
    InitialMass = 1
    ScanSpeed = 4
    StepsPerAmu = 10


class RGA100(Instrument):
    """
    Class to control and acquire data with
    `SRS RGA100, 200, 300 series <https://www.thinksrs.com/products/rga.html>`_.

    A native SRS RGA has a RS232 serial port that connects with
    baud rate of 28800, one stop bit, no parity, with RTS/CTS flow control.

    There is an option to add Ethernet communication using
    `RGA ethernet adapter <https://thinksrs.com/downloads/pdfs/manuals/REAm.pdf>`_

    RGA100 class provides methods for establishing communication,
    basic operation and scans to acquire mass spectra.

    Example
    ---------
    .. code-block:: python

        from srsinst.rga import RGA100
        r1 = RGA100('serial', 'COM3', 28800)

        # if Ethernet connection is used,
        # r1 = RGA100('tcpip', '192.168.1.100', 'userid', 'password')

        r1.set_emission_current(1.0)
        r1.set_scan_parameters()

        xs = r1.get_mass_axis()
        ys = r1.get_analog_scan()

        for x, y in zip(xs, ys):
            print(x, y)

        r1.set_emission_current(0.0)
        r1.disconnect()

    """

    _IdString = 'SRSRGA'
    _term_char = b'\r'

    available_interfaces = [
        [SerialInterface,
            {
                'port': FindListInput(),
                'baud_rate': 28800,
                'hardware_flow_control': True
            }
        ],
        [TcpipInterface,
            {
                'ip_address': Ip4Input('192.168.1.10'),
                'user_id': StringInput('admin'),
                'password': PasswordInput('admin'),
                'port': 818
            }
        ],
    ]

    def __init__(self, interface_type=None, *args):

        super().__init__(interface_type, *args)
        self.set_term_char(b'\r')
        self._m_max = Scans.MaxMass

        # Add components
        self.ionizer = Ionizer(self)
        self.filament = Filament(self)
        self.cem = CEM(self)
        self.scan = Scans(self)
        self.qmf = QMF(self)
        self.pressure = Pressure(self)
        self.status = Status(self)

    def connect(self, interface_type, *args):
        """
        Connect to an instrument over the specified communication interface

        If interface_type is 'serial',

        Parameters
        -----------
            interface_type: str
                Use **'serial'** for serial communication
            port : string
                serial port,  such as 'COM3' or '/dev/ttyUSB0'
            baud_rate : int, optional
                baud rate of the serial port, default is 114200, and SRS RGA uses 28800.
            hardware_flow_control: bool, optional
                RTS/CTS setting. The default is False, SRS RGA requires **True**.

        If interface_type is 'tcpip',

        Parameters
        -----------
            interface_type: str
                Use **'tcpip'** for Ethernet communication
            ip_address: str
                IP address of a instrument
            user_id: str
                user name for login.
            password : str
                password for login.
            port : int, optional
                TCP port number. The default is 818, which SRS RGA uses

        """
        super().connect(interface_type, *args)
        if type(self.comm) == SerialInterface:
            # Make sure the hardware flow control is set
            self.comm._serial.rtscts = True

    def check_id(self):

        self._m_max = 100
        if not self.is_connected():
            return None, None, None

        reply = self.query_text('ID?').strip()

        if len(reply) < 20:
            return None, None, None

        model_name = reply[0:9]
        firmware_version = reply[12:16]
        serial_number = reply[18:]

        if self._IdString not in reply:
            raise InstIdError("Invalid instrument: {} not in {}"
                  .format(self._IdString, model_name))
        self._id_string = reply

        try:
            self._m_max = int(reply[6:9])  # uninitialized unit has '???'
        except ValueError:
            self._m_max = 100

        self._model_name = model_name
        self._serial_number = serial_number
        self._firmware_version = firmware_version

        if self._m_max >= 300:
            self._m_max = 300
            if type(self.scan) is not Scans300:
                self.scan = Scans300(self)
        elif self._m_max >= 200:
            self._m_max = 200
            if type(self.scan) is not Scans200:
                self.scan = Scans200(self)
        elif self._m_max >= 100:
            self._m_max = 100
            if type(self.scan) is not Scans:
                self.scan = Scans(self)
        return self._model_name, self._serial_number, self._firmware_version

    def get_status(self):
        status_string = 'Emission current: {:.2f} mA\n'.format(self.ionizer.emission_current)
        status_string += 'CEM HV: {:.0f} V\n'.format(self.cem.voltage)
        status_string += self.status.get_error_text()
        return status_string

    def handle_command(self, cmd_string: str):
        cmd = cmd_string.upper()
        reply = ''
        if '?' in cmd or cmd.startswith("FL") or cmd.startswith("HV") or \
                cmd.startswith("VF") or cmd.startswith("EE")\
                or cmd.startswith("IE") or cmd.startswith("IN"):
            reply = self.query_text(cmd).strip()
        elif cmd.startswith("MR"):
            # self.send(cmd)
            try:
                mass = int(cmd[2:].strip())
                intensity = self.scan.get_single_mass_scan(mass)  # read_long()
                reply = str(intensity)
            except:
                pass
        elif cmd.startswith("SC") and len(cmd) < 10:
            self.scan.get_analog_scan()
            reply = "Scan Completed"
        elif cmd.startswith("HS"):
            self.scan.get_histogram_scan()
            reply = "Scan Completed"
        else:
            self.send(cmd)
        return reply

    def reset(self):
        self.query_text("IN2")

    # For RGA100,  RS232 DSR line should be high if RS232 cable is connected
    def check_head_online(self):
        """
        Check if SRS RGA is connected to a communication insterface

        For serial communication, it check for DSR line from SRS RGA is set high.
        For Ethernet communication, it check if the TCP socket is open.
        """
        if self.comm.type == SerialInterface.NAME:
            return self.comm._serial.dsr
        else:
            return self.is_connected()

    def get_max_mass(self):
        """
        Get maximum mass that can be used for a scan

        SRS RGA100 model has the maximum mass of 100 AMU;
        SRS RGA200, 200 AMU; and SRS RGA300, 300 AMU.

        Returns
        --------
            int
                maximum mass
        """
        return self._m_max

    def calibrate_all(self):
        """
        Calibrate all

        returns
        --------
            int
                Error status byte after calibration
        """
        reply = self.comm.query_text_with_long_timeout("CA", 120)
        error_status = int(reply)
        return error_status

    def calibrate_electrometer(self):
        """
        Calibrate electrometer's I-V response

        returns
        --------
            int
                Error status byte after calibration
        """
        reply = self.comm.query_text_with_long_timeout("CL", 120)
        error_status = int(reply)
        return error_status

    allow_run_button = [reset, calibrate_all, calibrate_electrometer]

