# pcprox python module

This is an open-source reimplementation of the functionality available in the
`CmdpcProx` utility for the RF IDeas pcProx USB readers, as a Python 3 module.

This has been tested with the RDR-6081AKU/APU (pcProx 125kHz HID Prox Desktop
USB reader). It might work with other readers, but I don't have any other
readers to test.

This implements the vendor-specific USB HID used to control the device.  This
doesn't support USB Serial or other non-USB interfaces.

This has been developed primarily to enable use and control of the device on
non-x86 systems (eg: ARM).

## Requirements

* Python 3.something (Python 2 is not supported)
* [pyusb][0]

This software has been developed and tested on Linux platforms.  It should work
without trouble on any Linux-supported CPU architecture.

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

