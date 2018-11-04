# pcprox python module

This is an open-source reimplementation of the functionality available in the
`CmdpcProx` utility for the RF IDeas pcProx USB readers, as a Python 3 module.

This has been tested with the RDR-6081AKU/APU (pcProx 125kHz HID Prox Desktop
USB reader). It might work with other readers, but I don't have any other
readers to test.

This implements [the proprietary and undocumented USB HID commands][1] that
`CmdpcProx` uses to control the device.  As such, this will unbind the `usbhid`
(keyboard) driver from the device in order to allow direct control.

This differs from some [other][2] [implementations][3] in that it **does not**
use `evdev` to access the device. This also **does not** require the closed
source `CmdpcProx` executable (which is only available for Linux x86 and
Windows x86).

This **does not** support USB Serial or other non-USB interfaces.

## Requirements

* Python 3.something (Python 2 is not supported)
* [pyusb][0]

This software has been developed and tested on Linux platforms.  It should work
without trouble on any Linux-supported CPU architecture (eg: ARM).

## Configuration options

The configuration options have the same name as what `CmdpcProx` uses, with a
couple of minor exceptions where multiple configuration options are on the same
byte (eg: `iTrailChr0`).

## Protocol

Device communication is described in [protocol.md][1].

## Library documentation

TODO

## Examples

See `usbtest.py`.

[0]: https://pyusb.github.io/pyusb/
[1]: ./protocol.md
[2]: https://github.com/goliatone/rfid-poc
[3]: https://github.com/google/makerspace-auth/blob/master/software/authbox/badgereader_hid_keystroking.py

