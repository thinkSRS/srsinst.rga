##! 
##! Copyright(c) 2022, 2023 Stanford Research Systems, All rights reserved
##! Subject to the MIT License
##! 

"""
Module to handle RGA100 error status
"""

BIT7 = 1 << 7
BIT6 = 1 << 6
BIT5 = 1 << 5
BIT4 = 1 << 4
BIT3 = 1 << 3
BIT2 = 1 << 2
BIT1 = 1 << 1
BIT0 = 1 << 0

ERROR_DICT = {
    'NE': 'No Error',
    'PS': '* 24V Power Supply Error: ',
    'PS7': 'Voltage > 26V',
    'PS6': 'Voltage < 22V',

    'DET': '* Electrometer Error: ',
    'DET7': 'ADC16 test failure',
    'DET6': 'DETECT fails to read +5nA input current',
    'DET5': 'DETECT fails to read -5nA input current',
    'DET4': 'COMPENSATE fails to read +5nA input current',
    'DET3': 'COMPENSATE fails to read -5nA input current',
    'DET1': 'OP-AMP Input Offset Voltage out of range',

    'RF': '* Quadrupole Mass Filter RF P/S error: ',
    'RF7': 'RF_CT exceeds (V_EXT- 2V) at M_MAX',
    'RF6': 'Primary current exceeds 2.0A',
    'RF4': 'Power supply in current limited mode',

    'EM': 'Electron Multiplier error: ',
    'EM7': 'No Electron Multiplier Option installed',

    'FL': '* Filament Error: ',
    'FL7': 'No filament detected',
    'FL6': 'Unable to set the requested emission current',
    'FL5': 'Vacuum Chamber pressure too high',
    'FL0': 'Single filament operation',

    'CM': '* Communications Error: ',
    'CM6': 'Parameter conflict',
    'CM5': 'Jumper protection violation',
    'CM4': 'Transmit buffer overwrite',
    'CM3': 'OVERWRITE in receiving',
    'CM2': 'Command-too-long',
    'CM1': 'Bad Parameter received',
    'CM0': 'Bad command received',
}


def query_errors(status):
    """
    Query all the status registers of RGA100

    Returns
    --------
        str
            string that contains colon separated register name and bits
    """
    error_string = ''
    status_byte = status.error_status
    if status_byte == 0:
        return 'NE'
    if status_byte & BIT6:
        result = status.error_ps
        # error_string += 'PS:'
        if result & BIT7:
            error_string += 'PS7:'
        if result & BIT6:
            error_string += 'PS6:'
    if status_byte & BIT5:
        result = status.error_detector
        # error_string += 'DET:'
        if result & BIT7:
            error_string += 'DET7:'
        if result & BIT6:
            error_string += 'DET6:'
        if result & BIT5:
            error_string += 'DET5:'
        if result & BIT4:
            error_string += 'DET4:'
        if result & BIT3:
            error_string += 'DET3:'
        if result & BIT1:
            error_string += 'DET1:'
    if status_byte & BIT4:
        result = status.error_qmf
        # error_string += 'RF:'
        if result & BIT7:
            error_string += 'RF7:'
        if result & BIT6:
            error_string += 'RF6:'
        if result & BIT4:
            error_string += 'RF4:'
    if status_byte & BIT3:
        result = status.error_cem
        # error_string += 'EM:'
        if result & BIT7:
            error_string += 'EM7:'

    if status_byte & BIT1:
        result = status.error_filament
        # error_string += 'FL:'
        if result & BIT7:
            error_string += 'FL7:'
        if result & BIT6:
            error_string += 'FL6:'
        if result & BIT5:
            error_string += 'FL5:'
        if result & BIT0:
            error_string += 'FL0:'
    if status_byte & BIT0:
        result = status.error_rs232
        # error_string += 'CM:'
        if result & BIT6:
            error_string += 'CM6:'
        if result & BIT5:
            error_string += 'CM5:'
        if result & BIT4:
            error_string += 'CM4:'
        if result & BIT3:
            error_string += 'CM3:'
        if result & BIT2:
            error_string += 'CM2:'
        if result & BIT1:
            error_string += 'CM1:'
        if result & BIT0:
            error_string += 'CM0:'
    return error_string[:-1]  # remove the last colon


def fetch_error_descriptions(error_string):
    """
    Fetch long description of each error bits from the error bit sring from
    query_errors()

    Returns
    --------
        str
            comma separated long description of error bits

    """
    err_list = error_string.split(':')
    err_description = ''
    for key in err_list:
        err_description += ERROR_DICT[key] + ', '
    return err_description[:-2]  # remove the last comma
