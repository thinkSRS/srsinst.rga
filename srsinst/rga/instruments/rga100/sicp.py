##! 
##! Coptright(c) 2022, 2023 Stanford Research Systems, All right reserved
##! Subject to the MIT License
##! 

"""
SRS Internet Configuration Protocol (SICP) class

The RGA120 series and RGA Ethernet Adapter (REA) use the IP configuration over UDP broadcasting, SRS IP Configuration protocol (SICP). When a search
packet is broadcast, all SICP enabled devices on the Local Area Network (LAN)
will respond with a packet. From those packets, you can find available devices
on the network.

If an instrument is waiting for IP configuration, you can change
the IP settings by broadcasting another packet. For REAs, the IP setting is only
available by power-cycle with a hardware button pressed. For RGA120s, the IP setting is available when the ECU is powered while unplugged
from the probe.

Because anybody on the local area network can find instruments
with SICP, You need to change the default user id and passowrd of the instrument, while you configure IP settings.

Example
---------
    .. code-block:: python

            from srsinst.rga import Sicp
            s = Sicp()
            s.find()
            for packet in s.packet_list:
                # packet.print_info()
                if not packet.is_connected():
                    print(packet.convert_to_ip_format(packet.ip_address),
                          ' is available.')

"""

import struct
import socket


class Packet(object):
    # Status bits
    DEVICE_STATUS_CONNECTED      = 1 << 0  # TCP/IP port is occupied
    DEVICE_STATUS_CONFIG_ENABLED = 1 << 1  # IP configuration mode is enabled
    DEVICE_STATUS_DHCP_RUNNING   = 1 << 2  # DHCP client is running
    DEVICE_STATUS_DHCP_SUCESS    = 1 << 3  # DHCP was succeeded
    DEVICE_STATUS_DHCP_FAILED    = 1 << 4  # DHCP failed
    DEVICE_STATUS_IP_CONFLICT    = 1 << 5
    DEVICE_STATUS_INVALID_LENGTH = 1 << 6

    # SICP sequence number
    SICP_SEQ_CALL = 0x01
    SICP_SEQ_REPLY = 0x02
    SICP_SEQ_SET = 0x03
    SICP_SEQ_DHCP = 0x04

    PacketSize = 100

    # Status from packet
    ST_CONNECTED = 'Connected'
    ST_CONFIGURABLE = 'Configurable'
    ST_IP_CONFLICT = 'IP_conflict'
    ST_DHCP_RUNNING = 'DHCP running'
    ST_DHCP_FAILED = 'DHCP failed'
    ST_DATA_LENGTH_INVALID = 'Error during SICP'
    ST_AVAILABLE = 'Available'

    def __init__(self, data):
        self.input_data = data
        self.data = bytearray(self.input_data)
        if len(self.data) != Packet.PacketSize:
            raise ValueError(f'Packet size is not {Packet.PacketSize}, but {len(self.data)}')
        self.decode()

    def set_name(self, name: str):
        length = 15
        if len(name) < length:
            length = len(name)
        index = 22
        for d in name:
            self.data[index] = ord(d)
            index += 1
        self.data[index] = 0

    def set_ip_address(self, ip:str):
        s = ip.split('.')
        if len(s) == 4:
            index = 38
            for n in s:
                self.data[index] = int(n)
                index += 1
        else:
            raise ValueError(f'Invalid IP address string: {ip}')

    def set_password_reset(self, value=True):
        if value:
            self.data[60:64] = b'\x01\x01\x01\xff'
        else:
            self.data[60] = 0xff

    def decode(self):
        if self.data[0:4] == b'SRS\0':
            self.class_id, self.device_id, self.sequence_number \
                = struct.unpack('>3h', self.data[4:10])
            self.serial_number, = struct.unpack('>1l', self.data[10:14])
            self.mac_address    = self.data[14:20]
            self.device_status, = struct.unpack('>1h', self.data[20:22])
            self.device_name    = self.data[22:38].split(b"\0")[0].decode()  # Get null-terminated string
            self.ip_address     = self.data[38:42]
            self.subnet_mask    = self.data[42:46]
            self.gateway        = self.data[46:50]
            self.dns_server     = self.data[50:54]
            self.version        = self.data[54:60].split(b"\0")[0].decode()
        else:
            raise AssertionError('Invalid header from the packet')

    def get_ip_address_string(self):
        return self.convert_to_ip_format(self.ip_address)

    def get_mac_address_string(self):
        return self.convert_to_mac_format(self.mac_address)

    def is_connected(self):
        return self.device_status & Packet.DEVICE_STATUS_CONNECTED != 0

    def is_configurable(self):
        return self.device_status & Packet.DEVICE_STATUS_CONFIG_ENABLED != 0

    def is_dhcp_running(self):
        return self.device_status & Packet.DEVICE_STATUS_DHCP_RUNNING != 0

    def is_dhcp_successful(self):
        return self.device_status & Packet.DEVICE_STATUS_DHCP_SUCESS != 0

    def is_dhcp_failed(self):
        return self.device_status & Packet.DEVICE_STATUS_DHCP_FAILED != 0

    def is_ip_conflicted(self):
        return self.device_status & Packet.DEVICE_STATUS_IP_CONFLICT != 0

    def is_data_length_invalid(self):
        return self.device_status & Packet.DEVICE_STATUS_INVALID_LENGTH != 0

    @staticmethod
    def convert_to_ip_format(s):
        if len(s) == 4:
            return "%d.%d.%d.%d"%(s[0], s[1], s[2], s[3])
        else:
            return ""

    @staticmethod
    def convert_to_mac_format(s):
        if len(s) == 6:
            return "%02x-%02x-%02x-%02x-%02x-%02x" % (s[0], s[1], s[2], s[3], s[4], s[5])
        else:
            return ""

    def print_raw(self):
        for i, d in enumerate(self.data):
            if 47 < d < 58 or 63 < d < 91 or 96 < d < 123:
                print(f"'{chr(d)}'", end='')
            else:
                print(f'{d:02x} ', end='')
            if (i+1) % 16 == 0:
                print('')
        print('')

    def print_info(self):
        self.decode()
        print("Class ID     : {}".format(self.class_id))
        print("Device ID    : {}".format(self.device_id))
        print("SICP Seq. No.: {}".format(self.sequence_number))
        print("Serial No.   : {}".format(self.serial_number))
        print("MAC address  : {}".format(self.convert_to_mac_format(self.mac_address)))
        print("Device name  : {}".format(self.device_name))
        print("IP address   : {}".format(self.convert_to_ip_format(self.ip_address)))
        print("Subnet mask  : {}".format(self.convert_to_ip_format(self.subnet_mask)))
        print("Gateway      : {}".format(self.convert_to_ip_format(self.gateway)))
        print("DNS server   : {}".format(self.convert_to_ip_format(self.dns_server)))
        print("Version      : {}".format(self.version))

        print("Connected to a client  : {}".format(self.is_connected()))
        print("Config. enabled        : {}".format(self.is_configurable()))
        print("DHCP running           : {}".format(self.is_dhcp_running()))
        print("DHCP success           : {}".format(self.is_dhcp_successful()))
        print("DHCP failed            : {}".format(self.is_dhcp_failed()))
        print("IP address conflict    : {}".format(self.is_ip_conflicted()))
        print("Invalid packet length  : {}".format(self.is_data_length_invalid()))
        print("Device status : {}".format(self.device_status))
        print("===============================")

    def get_short_status_from_packet(self):
        if self.is_connected():
            return Packet.ST_CONNECTED
        elif self.is_configurable():
            return Packet.ST_CONFIGURABLE
        elif self.is_ip_conflicted():
            return Packet.ST_IP_CONFLICT
        elif self.is_dhcp_running():
            return Packet.ST_DHCP_RUNNING
        elif self.is_dhcp_failed():
            return Packet.ST_DHCP_FAILED
        elif self.is_data_length_invalid():
            return Packet.ST_DATA_LENGTH_INVALID
        else:
            return Packet.ST_AVAILABLE

    def set_sequence_number(self, number: int):
        if number == Packet.SICP_SEQ_SET or number == Packet.SICP_SEQ_DHCP:
            self.data[8:10] = 0x0, number
        else:
            raise ValueError(f'Invalid sequence number: {number}')


class SICP(object):
    BROADCAST_ADDRESS = b"255.255.255.255"
    PORT = 818
    CALL_MSG_RGA_REA = b"SRS\x00\x00\x01\x00\x04\x00\x01"
    CALL_MSG_RGA_ALL = b"SRS\x00\x00\x01\x00\xFF\x00\x01"

    def __init__(self):
        self.packet_list = []
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def _call(self, msg = CALL_MSG_RGA_ALL):
        self.socket.sendto(msg, (SICP.BROADCAST_ADDRESS, SICP.PORT))

    def _get_replies(self, timeout=3):
        old_timeout = self.socket.gettimeout()
        self.socket.settimeout(timeout)
        self.packet_list=[]
        while True:
            try:
                data, address = self.socket.recvfrom(128)
                packet = Packet(data)
                self.packet_list.append(packet)
            except:
                break
        self.socket.settimeout(old_timeout)

    def find(self, timeout=3):
        self._call()
        self._get_replies(timeout)

    def send_packet(self, packet, timeout=3):
        old_timeout = self.socket.gettimeout()
        self.socket.settimeout(timeout)
        self.socket.sendto(packet.data, (SICP.BROADCAST_ADDRESS, SICP.PORT))
        data, address = self.socket.recvfrom(128)
        self.socket.settimeout(old_timeout)
        return Packet(data)


if __name__ == "__main__":
    s = SICP()
    s.find()
    for packet in s.packet_list:
        packet.print_info()
        #packet.print_raw()
