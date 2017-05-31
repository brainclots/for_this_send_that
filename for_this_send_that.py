#!/usr/bin/env python

'''
Purpose:    Connect to a list of devices, stored in column 1 in a spreadsheet,
            then run the commands contained in column C. Column D should
            contain rollback commands. The rollback commands will be run only
            if the script is envoked with the '-r' option.
            | DeviceName | OS_Type  | Implementation_Cmds |   Rollback_Cmds  |
            | device1    | cisco_ios| commands to run     | rollback commands|
            | device2    | juniper  | commands to run     | rollback commands|
            |   etc...   | type     | commands to run     | rollback commands|
Author:
            ___  ____ _ ____ _  _    _  _ _    ____ ___ ___
            |__] |__/ | |__| |\ |    |_/  |    |  |  |    /
            |__] |  \ | |  | | \|    | \_ |___ |__|  |   /__
            Brian.Klotz@nike.com

Version:    0.8
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
        | Column A   | Column B |     Column C        |     Column D     |
        +------------+----------+---------------------+------------------+
    Row1| DeviceName | OS_Type  | Implementation_Cmds |   Rollback_Cmds  |
    Row2| device1    | cisco_ios| commands to run     | rollback commands|
    Row3| device2    | juniper  | commands to run     | rollback commands|
    RowX|   etc...   | type     | commands to run     | rollback commands|
    (OS_Type can be either "juniper", "cisco_ios", or "cisco_ios_telnet")
    Optional: Include 'show' commands in Column E for on-screen
    verification of your implmentation commands (will be logged as well).

    Note: If the '-v' switch is given, you will be prompted to save changes,
    otherwise, changes are saved silently.
    ''')
always_required = parser.add_argument_group('always required')
always_required.add_argument("input_xlsx", nargs=1, help="Name of file containing \
                             devices and commands for each device",
                             metavar='<import_file>')
parser.add_argument('-v', '--verify',
                    help="Ask for verification before saving",
                    action="store_true")
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


def main():
    input_file = args.input_xlsx[0]
    input_info = open_file(input_file)

    username, password = get_creds()

    netmiko_exceptions = (netmiko.ssh_exception.NetMikoTimeoutException,
                          netmiko.ssh_exception.NetMikoAuthenticationException)

    # Build dictionary of devices
    for device_name in input_info.keys():
        input_device = input_info[device_name][device_name]
        device_dict = {'host': device_name,
                       'device_type': input_device['device_type'],
                       'username': username,
                       'password': password,
                       'secret': password
                       }
        print('Connecting to ' + device_dict['host'] + ' (' +
              device_dict['device_type'] + ') ...')
        try:  # Connect to device
            connection = netmiko.ConnectHandler(**device_dict)
            logger.info('Successfully connected to %s', device_dict['host'])
            connection.enable()

            # Send commands
            if args.rollback:
                print('Sending rollback commands...')
                result = connection.send_config_set(
                                    input_device['rollback_cmds'])
            else:
                print('Sending implementation commands...')
                result = connection.send_config_set(
                                    input_device['implementation_cmds'])
            indented_lines = indentem(result)
            logger.info('Actions: \n%s', indented_lines)

            # Run 'show' commands, if present
            if input_device['verification_cmds']:
                verify_config(connection, input_device['verification_cmds'])

            # Determine whether to save
            if args.verify:
                yes_or_no = ask_to_save()
                if yes_or_no == 'y':
                    print('Saving config changes...')
                    save_now(connection, device_dict['device_type'])
                    logger.info('Saved config changes on %s',
                                device_dict['host'])
                else:
                    print('Changes NOT saved!')
                    logger.info('Changes NOT saved, roll back or reboot')
            else:
                save_now(connection, device_dict['device_type'])
                logger.info('Saved changes on %s' % device_dict['host'])

            # Disconnect from device
            print('Disconnecting...')
            logger.info('Disconnecting from %s' % device_dict['host'])
            connection.disconnect()

        except netmiko_exceptions as e:
            print('Failed to connect: %s' % e)
            logger.error('Failed to connect %s', e)
    print('Completed. See "output.log" for results.')


def open_file(file):
    wb = openpyxl.load_workbook(file)
    ws = wb.active
    input_info = {}
    for row in range(2, ws.max_row + 1):
        device = ws['A' + str(row)].value
        input_info[device] = {device:
                              {'host': device,
                               'device_type': ws['B' + str(row)].value,
                               'implementation_cmds': ws['C' + str(row)].value,
                               'rollback_cmds': ws['D' + str(row)].value,
                               'verification_cmds': ws['E' + str(row)].value
                               }
                              }
    return input_info


def get_creds():  # Prompt for credentials
    username = getpass.getuser()
#   username = raw_input('User ID: ')
    password = getpass.getpass()
    return username, password


def verify_config(connection, commands):
    proof = connection.send_command(commands)
    print(proof)
    logger.info('Verifcation commands results: \n%s', proof)
    return


def ask_to_save():
    answer = raw_input('Save changes? (y/n) ')
    if answer.lower() == 'y':
        return answer


def save_now(connection, device_type):
    print('Saving config changes...')
    if device_type in ['cisco_ios', 'cisco_ios_telnet']:
        connection.send_command('write mem')
    elif device_type == 'juniper':
        connection.send_config_set('commit')


def indentem(lines):
    lines = '    ' + lines
    lines = lines.replace('\n', '\n    ')
    return lines


main()
