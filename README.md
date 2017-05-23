for_this_send_that.py

This python script uses the netmiko library to connect to a list of devices
supplied in a spreadsheet in column A, with the device type in column B
(device type being either cisco_ios, cisco_ios_telnet, juniper, or cisco_asa).
The script will then enter configuration mode and execute the implementation
commands provided in column C, saving the changes before moving on to the next
row. Column D can be used to hold commands to roll back changes (assuming you
can still access the device) and will be run if executing the script with a
'-r' flag.

Optionally, you can provide verification commands in column E. If provided, they
will be executed following the implementation commands, before saving. If the
command is executed with the '-v' flag, the script will ask for confirmation
before saving the changes.

See the example.xlsx file for examples of the spreadsheet.

usage: for_this_send_that.py [-h] [-v] [-r] <import_file>

    Connect to list of devices and run a set of commands on each.
    Format the Excel file as follows:
        | Column A   | Column B |     Column C        |     Column D     |
        +------------+----------+---------------------+------------------+
    Row1| DeviceName | OS_Type  | Implementation_Cmds |   Rollback_Cmds  |
    Row2| device1    | cisco    | commands to run     | rollback commands|
    Row3| device2    | juniper  | commands to run     | rollback commands|
    RowX|   etc...   | type     | commands to run     | rollback commands|

    (OS_Type can be either "juniper", "cisco_ios", or "cisco_ios_telnet")
    Optional: Include 'show' commands in Column E for on-screen
    verification of your implmentation commands (will be logged as well).

    Note: If the '-v' switch is given, you will be prompted to save changes,
    otherwise, changes are saved silently.


optional arguments:
  -h, --help      show this help message and exit
  -v, --verify    Ask for verification before saving
  -r, --rollback  Run rollback commands

always required:
  <import_file>   Name of file containing devices and commands for each device
  
