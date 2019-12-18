#!/usr/bin/env python3
# -*- mode: python3; indent-tabs-mode: nil; tab-width: 4 -*-
"""
usbtest - test program for reading a card and changing LEDs on pcProx

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

import pcprox
from time import sleep


def main(debug=False):
    dev = pcprox.open_pcprox(debug=debug)

    # Show the device info
    print(repr(dev.get_device_info()))

    # Dump the configuration from the device.
    config = dev.get_config()
    config.print_config()

    # Disable sending keystrokes, as we want direct control
    config.bHaltKBSnd = True

    # Turn off the red LED, turn on the green LED
    config.iRedLEDState = False
    config.iGrnLEDState = True

    # Tells pcProx that the LEDs are under application control
    config.bAppCtrlsLED = True

    # Send the updated configuration to the device
    config.set_config(dev)

    # Exit configuration mode
    dev.end_config()

    # Wait half a second
    sleep(.5)

    # Turn off the green LED
    config.iGrnLEDState = False
    found_card = False
    print('Waiting for a card... (red light should pulse)')
    for x in range(40):
        # flash the red LED as "1-on 1-off 1-on 3-off"
        config.iRedLEDState = (x % 6 in (0, 2))
        # LED control is in page 2, so we can explicitly only configure this
        # page.
        config.set_config(dev, [2])
        dev.end_config()
        tag = dev.get_tag()

        if tag is not None:
            # We got a card!
            # Turn off the red LED
            config.iRedLEDState = False
            config.set_config(dev, [2])
            dev.end_config()
            found_card = True

            # Print the tag ID on screen
            print('Tag data: %s' % pcprox._format_hex(tag[0]))
            print('Bit length: %d' % tag[1])
            break

        # No card in the field, sleep
        sleep(.2)

    # We were successful, do a little light show
    if found_card:
        print('We got a card! (blinking lights)')
        for x in range(20):
            config.iGrnLEDState = x & 0x01 == 0
            config.iRedLEDState = x & 0x02 > 0
            config.set_config(dev, [2])
            dev.end_config()
            sleep(.1)
    else:
        # When wrapping up, wait 0.3sec, so we get to see the green light on
        # success.
        print('No card found.')

    # Re-enable sending keystrokes
    config.bHaltKBSnd = True

    # Place the LEDs back under pcProx control
    config.iRedLEDState = config.iGrnLEDState = config.bAppCtrlsLED = False

    # Send the updated configuration
    config.set_config(dev)
    dev.end_config()

    # Done.


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description='Test program for pcprox which reads a card in the field')

    parser.add_argument('-d', '--debug', action='store_true',
                        help='Enable debug traces')

    options = parser.parse_args()
    main(options.debug)
