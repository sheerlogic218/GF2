#!/usr/bin/env python3
"""Parse command line options and arguments for the Logic Simulator.

This script parses options and arguments specified on the command line, and
runs either the command line user interface or the graphical user interface.

Usage
-----
Show help: logsim.py -h
Command line user interface: logsim.py -c <file path>
Graphical user interface: logsim.py <file path>
"""

import getopt
import sys
import os
import wx

from Front_End import *
from Back_End import *



def main(arg_list):
    """Parse the command line options and arguments specified in arg_list.

    Run either the command line user interface, the graphical user interface,
    or display the usage message.
    """
    usage_message = (
        "Usage:\n"
        "Show help: logsim.py -h\n"
        "Command line user interface: logsim.py -c <file path>\n"
        "Graphical user interface: logsim.py <file path>"
    )
    try:
        options, arguments = getopt.getopt(arg_list, "hc:")
    except getopt.GetoptError:
        print("Error: invalid command line arguments\n")
        print(usage_message)
        sys.exit()

    # Initialise instances of the four inner simulator classes
    names = Names()
    devices = Devices(names)
    network = Network(names, devices)
    monitors = Monitors(names, devices, network)

    for option, path in options:
        if option == "-h":  # print the usage message
            print(usage_message)
            sys.exit()
        elif option == "-c":  # use the command line user interface
            scanner = Scanner(path, names)
            parser = Parser(names, devices, network, monitors, scanner)
            if parser.parse_network():
                # Initialise an instance of the userint.UserInterface() class
                userint = UserInterface(names, devices, network, monitors)
                userint.command_interface()

    if not options:  # no option given, use the graphical user interface

        if len(arguments) != 1:  # wrong number of arguments
            print("Error: one file path required\n")
            print(usage_message)
            sys.exit()

        [path] = arguments
        scanner = Scanner(path, names)
        parser = Parser(names, devices, network, monitors, scanner)
        try:
            if parser.parse_network():

                # for device in parser.devices.devices_dict.values():
                #     print(parser.names.inv_name_IDS[device.device_kind])
                # print(parser.names.inv_name_IDS)

                # Initialise an instance of the gui.Gui() class
                app = wx.App()
                _app_locale = _setup_locale(app)  # noqa: F841 – keep alive
                gui = Gui(
                    "Logic Simulator", path, names, devices, network, monitors
                )
                gui.Show(True)
                app.MainLoop()
            else:
                for error in parser.errors:
                    print(error)
        except SyntaxError as e:
            # easy fix for unexpected characters
            print(e)
            for error in parser.errors[:-1]:
                print(error)


def _setup_locale(app: wx.App) -> wx.Locale:
    """Initialise wx.Locale for i18n.

    Language selection (in order of priority):
      1. LANG / LANGUAGE environment variable (e.g. LANG=fr_FR)
      2. Default system language (English)

    To run in French on any platform:
        LANG=fr_FR python logsim.py <file>          # Linux/macOS
        $env:LANG="fr_FR"; python logsim.py <file>  # PowerShell
    """
    locale_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Front_End/locale")
    wx.Locale.AddCatalogLookupPathPrefix(locale_dir)

    lang_str = os.environ.get("LANG", os.environ.get("LANGUAGE", "")).lower()
    wx_lang = wx.LANGUAGE_FRENCH if lang_str.startswith("fr") else wx.LANGUAGE_DEFAULT

    locale = wx.Locale()
    locale.Init(wx_lang, wx.LOCALE_DONT_LOAD_DEFAULT)
    locale.AddCatalog("logsim")
    return locale  # caller must keep a reference to prevent GC


if __name__ == "__main__":
    main(sys.argv[1:])
