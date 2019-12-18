#!/usr/bin/env python3
# -*- mode: python3; indent-tabs-mode: nil; tab-width: 2 -*-
"""
configure.py - test tool for setting configuration parameters on pcProx

Copyright 2018-2019 Michael Farrell <micolous+git@gmail.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import argparse
import pcprox


class IntConfigAction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError('nargs not allowed')
        super(IntConfigAction, self).__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        # Parse options like 'abc=1'
        if getattr(namespace, self.dest) is None:
            setattr(namespace, self.dest, [])

        k, v = values.split('=')
        v = int(v)
        getattr(namespace, self.dest).append((k, v))


def main(set_true, set_false, set_int, write_eeprom=False, debug=False):
    dev = pcprox.open_pcprox(debug=debug)

    # Show the device info
    print(repr(dev.get_device_info()))

    # Dump the configuration from the device.
    config = dev.get_config()

    # Now apply this config
    if set_true is not None:
        for o in set_true:
            if not hasattr(config, o):
                raise TypeError(f'Unknown option {o}')
            setattr(config, o, True)
    if set_false is not None:
        for o in set_false:
            if not hasattr(config, o):
                raise TypeError(f'Unknown option {o}')
            setattr(config, o, False)
    if set_int is not None:
        for k, v in set_int:
            if not hasattr(config, o):
                raise TypeError(f'Unknown option {o}')
            setattr(config, k, v)

    # Has anything been set?
    if any(x is not None for x in (set_true, set_false, set_int)):
        print('/ New configuration:')
        config.print_config()

        # Send the updated configuration
        config.set_config(dev)

        if write_eeprom:
            print('/ Writing to EEPROM...')
            dev.save_config(0x7)
        else:
            dev.end_config()
    else:
        print('/ Current configuration:')
        config.print_config()

    print('/ Done!')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Configuration utility for pcProx')

    parser.add_argument('-d', '--debug',
                        action='store_true', help='Enable debug traces')

    parser.add_argument('-t', '--set-true', metavar='bOPTION',
                        action='append',
                        help='Set configuration flag to true / 1')

    parser.add_argument('-f', '--set-false', metavar='bOPTION',
                        action='append',
                        help='Set configuration flag to false / 0')

    parser.add_argument('-i', '--set-int', metavar='iOPTION=VALUE',
                        action=IntConfigAction,
                        help='Set integer to value, eg: [-i '
                             'iLeadParityBitCnt=1]')

    parser.add_argument('-w', '--write-eeprom',
                        action='store_true',
                        help='Writes the configuration to EEPROM')

    options = parser.parse_args()
    main(options.set_true, options.set_false, options.set_int,
         options.write_eeprom, options.debug)
