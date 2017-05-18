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

Version:    0.1
Date:       May 2017
'''
import argparse
import netmiko
import getpass
import logging
import csv

# Set up argument parser and help info
parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description='''\
    Connect to list of devices and run a set of commands on each.
    Format the csv file as follows:
            | DeviceName | OS_Type  | Implementation_Cmds |   Rollback_Cmds  |
            | device1    | cisco    | commands to run     | rollback commands|
            | device2    | juniper  | commands to run     | rollback commands|
            |   etc...   | type     | commands to run     | rollback commands|
        ''')
always_required = parser.add_argument_group('always required')
always_required.add_argument("input_csv", nargs=1, help="Name of file containing \
                             devices and command files for each device",
                             metavar='<import_file>')
parser.add_argument('-r', '--rollback', help="Run rollback commands",
                    action="store_true")
args = parser.parse_args()

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler('output.log')
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(message)s\n')
handler.setFormatter(formatter)
logger.addHandler(handler)


def open_file(file):
    devices = []
    device_type = []
    implementation_cmds = []
    rollback_cmds = []
    with open(file, 'rbU') as f:
        reader = csv.reader(f, dialect='excel')
        counter = 0
        for row in reader:
            if counter >= 1:
                if row[0]:
                    devices.append(row[0])
                    device_type.append(row[1])
                    implementation_cmds.append(row[2])
                    rollback_cmds.append(row[3])
            counter += 1
        f.close()
        return devices, device_type, implementation_cmds, rollback_cmds


def get_creds():  # Prompt for credentials
    username = getpass.getuser()
#   username = raw_input('User ID: ')
    password = getpass.getpass()
    return username, password


def main():
    csvfile = args.input_csv[0]
    devices, device_type, implementation_cmds, rollback_cmds \
        = open_file(csvfile)
    username, password = get_creds()

    netmiko_exceptions = (netmiko.ssh_exception.NetMikoTimeoutException,
                          netmiko.ssh_exception.NetMikoAuthenticationException)

    counter = 0
    for a_device in devices:
        if device_type[counter].lower() == 'cisco':
            device_dict = {'host': a_device,
                           'device_type': 'cisco_ios',
                           'username': username,
                           'password': password,
                           'secret': password
                           }
        elif device_type[counter].lower() == 'cisco_asa':
            device_dict = {'host': a_device,
                           'device_type': 'cisco_asa',
                           'username': username,
                           'password': password,
                           'secret': password
                           }
        elif device_type[counter].lower() == 'juniper':
            device_dict = {'host': a_device,
                           'device_type': 'juniper',
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
            if device_dict['device_type'] == 'cisco_ios':
                connection.send_command('write mem')
            elif device_dict['device_type'] == 'juniper':
                connection.send_config_set('commit')
            logger.info('Saved config changes on %s', device_dict['host'])
            connection.disconnect()
            counter += 1

        except netmiko_exceptions as e:
            print('Failed to connect: %s' % e)
            logger.error('Failed to connect %s', e)
    print('Completed. See "output.log" for results.')


main()
