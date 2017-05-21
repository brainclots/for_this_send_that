#!/usr/bin/env python

'''
Purpose:    Connect to a list of devices, stored in column 1 in a csv file,
            then run the commands contained in column 3. Column 4 should
            contain rollback commands. These will be run only if the script is
            envoked with the '-r' option.
            | DeviceName | OS_Type  | Implementation_Cmds |   Rollback_Cmds  |
            | device1    | cisco    | commands to run     | rollback commands|
            | device2    | juniper  | commands to run     | rollback commands|
            |   etc...   | type     | commands to run     | rollback commands|
Author:
            ___  ____ _ ____ _  _    _  _ _    ____ ___ ___
            |__] |__/ | |__| |\ |    |_/  |    |  |  |    /
            |__] |  \ | |  | | \|    | \_ |___ |__|  |   /__
            Brian.Klotz@nike.com

Version:    0.5
Date:       May 2017
'''
import argparse
import netmiko
import getpass
import logging
import openpyxl

# Set up argument parser and help info
parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description='''\
    Connect to list of devices and run a set of commands on each.
    Format the Excel file as follows:
            | DeviceName | OS_Type  | Implementation_Cmds |   Rollback_Cmds  |
            | device1    | cisco    | commands to run     | rollback commands|
            | device2    | juniper  | commands to run     | rollback commands|
            |   etc...   | type     | commands to run     | rollback commands|
        (OS_Type can be either "juniper", "cisco_ios", or "cisco_ios_telnet")
        ''')
always_required = parser.add_argument_group('always required')
always_required.add_argument("input_xlsx", nargs=1, help="Name of file containing \
                             devices and commands for each device",
                             metavar='<import_file>')
parser.add_argument('-r', '--rollback', help="Run rollback commands",
                    action="store_true")
args = parser.parse_args()

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler('output.log')
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def open_file(file):
    wb = openpyxl.load_workbook(file)
    ws = wb.active
    devices = []
    device_type = []
    implementation_cmds = []
    rollback_cmds = []
    for row in range(2, ws.max_row):
        devices.append(ws['A' + str(row)].value)
        device_type.append(ws['B' + str(row)].value)
        implementation_cmds.append(ws['C' + str(row)].value)
        rollback_cmds.append(ws['D' + str(row)].value)
    return devices, device_type, implementation_cmds, rollback_cmds


def get_creds():  # Prompt for credentials
    username = getpass.getuser()
#   username = raw_input('User ID: ')
    password = getpass.getpass()
    return username, password


def main():
    input_file = args.input_xlsx[0]
    devices, device_type, implementation_cmds, rollback_cmds \
        = open_file(input_file)
    username, password = get_creds()

    netmiko_exceptions = (netmiko.ssh_exception.NetMikoTimeoutException,
                          netmiko.ssh_exception.NetMikoAuthenticationException)

    counter = 0
    for a_device in devices:
        device_dict = {'host': a_device,
                       'device_type': device_type[counter],
                       'username': username,
                       'password': password,
                       'secret': password
                       }
        print('Connecting to ' + device_dict['host'] + ' (' +
              device_dict['device_type'] + ') ...')
        try:
            connection = netmiko.ConnectHandler(**device_dict)
            logger.info('Successfully connected to %s', device_dict['host'])
            connection.enable()
            print('Sending commands...')
            if args.rollback:
                result = connection.send_config_set(rollback_cmds[counter])
            else:
                result = connection.send_config_set(implementation_cmds
                                                    [counter])
            logger.info('Actions: \n%s', result)
            print('Saving config changes...')
            if device_dict['device_type'] in ['cisco_ios', 'cisco_ios_telnet']:
                connection.send_command('write mem')
            elif device_dict['device_type'] == 'juniper':
                connection.send_config_set('commit')
            logger.info('Saved config changes on %s', device_dict['host'])
            print('Disconnecting')
            connection.disconnect()
            counter += 1

        except netmiko_exceptions as e:
            print('Failed to connect: %s' % e)
            logger.error('Failed to connect %s', e)
    print('Completed. See "output.log" for results.')


main()
