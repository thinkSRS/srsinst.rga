##! 
##! Coptright(c) 2022, 2023 Stanford Research Systems, All right reserved
##! Subject to the MIT License
##! 

"""
RGA100 remote commands allow no space between a set command and the following parameter.
Following NSCommand (no space command) classes are derived from
`Command classes <https://thinksrs.github.io/srsgui/srsgui.inst.html#module-srsgui.inst.commands>`_
in `srsgui <https://thinksrs.github.io/srsgui/index.html>`_
to meet the requirement.
"""

from srsgui.inst.exceptions import InstCommunicationError, InstSetError, InstQueryError

from srsgui.inst.commands import IntCommand, IntGetCommand, FloatCommand, \
                                 BoolSetCommand

# Set command format with no space between a command and the following parameter.
SetCommandFormat = '{}{}'


class IntNSCommand(IntCommand):
    _set_command_format = SetCommandFormat


class FloatNSCommand(FloatCommand):
    _set_command_format = SetCommandFormat


class BoolSetNSCommand(BoolSetCommand):
    _set_command_format = SetCommandFormat


class RgaIntCommand(IntNSCommand):
    """
    Descriptor for an RGA100 remote command to
    **set** and **query** an **integer** value.
    Setting a value returns a status byte, which is stored as last_set_status
    """

    def __set__(self, instance, value):
        if instance is None:
            return

        set_string = self.remote_command
        try:

            if callable(self._set_convert_function):
                converted_value = self._set_convert_function(value)
            else:
                converted_value = value
            set_string = self._set_command_format.format(self.remote_command, converted_value)
            reply = int(instance.comm.query_text_with_long_timeout(set_string))
            instance.last_set_status = reply
        except InstCommunicationError:
            raise InstSetError('Error during setting: CMD:{} '.format(set_string))
        except ValueError:
            raise InstSetError('Error during conversion: CMD: {}'
                               .format(set_string))


class RgaFloatCommand(FloatNSCommand):
    """
    Descriptor for an RGA100 remote command to
    **set** and **query** a **float** value.
    Setting a value returns a status byte, which is stored as last_set_status
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._get_convert_function = float
        self._set_convert_function = float

    def __set__(self, instance, value):
        if instance is None:
            return

        set_string = self.remote_command
        try:

            if callable(self._set_convert_function):
                converted_value = self._set_convert_function(value)
            else:
                converted_value = value
            set_string = self._set_command_format.format(self.remote_command, converted_value)
            reply = int(instance.comm.query_text_with_long_timeout(set_string))
            instance.last_set_status = reply
        except InstCommunicationError:
            raise InstSetError('Error during setting: CMD:{} '.format(set_string))
        except ValueError:
            raise InstSetError('Error during conversion: CMD: {}'
                               .format(set_string))


class RgaIonEnergyCommand(RgaIntCommand):
    """
    Descriptor for a RGA100 remote command
    to  **set**  and **query** ion energy. only 8 and 12 eV are allowed.
    Setting a value returns a status byte, which is stored as last_set_status
   """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._get_convert_function = lambda a: 12 if int(a) != 0 else 8
        self._set_convert_function = lambda a: 1 if a >= 12 else 0


class RgaTotalPressureCommand(IntGetCommand):
    """
    Descriptor for a RGA100 remote command to **query** total pressure value
    returned as a binary long integer. To set a value is not allowed.
   """

    def __get__(self, instance, instance_type):
        query_string = self._get_command_format.format(self.remote_command)
        reply = None
        try:
            with instance.comm.get_lock():
                instance.comm._send(query_string)
                intensity = instance.comm._read_long()
            self._value = intensity
        except InstCommunicationError:
            raise InstQueryError('Error during querying: CMD: {}'.format(query_string))
        except ValueError:
            raise InstQueryError('Error during conversion CMD: {} Reply: {}'
                                 .format(query_string, reply))
        return self._value


class RgaStoredCEMGainCommand(FloatNSCommand):
    """
    Descriptor for a RGA100 remote command
    to  **set**  and **query** Cem gain stored.
    The raw data is stored as the gain divided by 1000.
    And the descriptor converts back to the original value
   """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._get_convert_function = lambda a: float(a) * 1000.0
        self._set_convert_function = lambda a: float(a) / 1000.0
