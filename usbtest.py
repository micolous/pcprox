#!/usr/bin/env python3
"""
usbtest - test program for reading a card and changing LEDs on pcProx

Copyright 2018 Michael Farrell <micolous+git@gmail.com>

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
import time

def main():
   dev = pcprox.open_pcprox()
   dev._debug = True
   
   print(repr(dev.get_device_info()))
   
   config = dev.get_config()
   config.print_config()
   
   config.bHaltKBSnd = True
   config.iRedLEDState = config.iGrnLEDState = False
   config.bAppCtrlsLED = True
   config.set_config(dev)
   dev.end_config()
   time.sleep(.5)
   
   for x in range(10):
      print('waiting for a card...')
      
      # flash the red LED when reading.
      config.iRedLEDState = True
      config.set_config(dev, [2])      
      dev.end_config()
      tag = dev.get_tag()

      if tag is not None:
         config.iRedLEDState = False
         config.iGrnLEDState = True
         config.set_config(dev, [2])      
         dev.end_config()
         print(tag)
         break

      time.sleep(.3)
      config.iRedLEDState = False
      config.set_config(dev, [2])
      dev.end_config()
      time.sleep(.6)

   print('waiting...')
   time.sleep(.3)   
   config.bHaltKBSnd = True
   config.iRedLEDState = config.iGrnLEDState = config.bAppCtrlsLED = False
   config.set_config(dev)
   dev.end_config()
   

if __name__ == "__main__":
    main()
