# pcprox python module

This is an open-source reimplementation of the functionality available in the
`CmdpcProx` utility for the RFIDeas pcProx USB readers, as a Python 3 module.

This has been tested with the RDR-6081AKU/APU (pcProx 125kHz HID Prox Desktop
USB reader). It might work with other readers, but I don't have any other
readers to test.

This implements [the proprietary and undocumented USB HID commands][1] that
`CmdpcProx` uses to control the device.

This differs from some [other][2] [implementations][3] in that it **does not**
use `evdev` to access the device. This also **does not** require the closed
source `CmdpcProx` executable (which is only available for Linux x86 and
Windows x86).

This **does not** support USB Serial or other non-USB interfaces.

## Requirements

* Python 3.x
* [hidapi][0] (generally packaged as `python3-hidapi`)

_Python 2.x is not supported, and will not be supported._

## Platform support

Known-working platforms:

* Linux (tested on `x86_64`, but will probably work on any Linux-supported CPU
  architecture, including ARM).
* Mac OS X (tested on 10.14)

Non-working platforms:

* Windows ([would require this hidapi patch][4])

Otherwise, this should run wherever hidapi runs, as long as one can send USB HID
feature reports to keyboard devices (which pcProx simulates).

## Setting up permissions

### Linux

Copy [the udev rules](./udev/60-rfideas-permissions.rules) (as root):

```bash
install -o0 -g0 -m0644 udev/60-rfideas-permissions.rules /etc/udev/rules.d/
udevadm control --reload-rules
```

Then disconnect the pcProx (if connected), and then reconnect it.

These rules use _uaccess_, which should grant access to anyone logged in locally
via `systemd-logind` (which includes most recent Linux distros).

If you're using this with a user which is not logged in locally, or are not
using `systemd`, modify this configuration to replace `TAG+="uaccess"` with
something like `GROUP="rfidusers"`, which will instead set ACLs based on group
membership.

### Mac OS X

Mac OS X requires that all applications requesting direct access to a keyboard
device run as `root`.

## Examples

* [configure.py](./configure.py): A basic configuration utility that supports
  dumping and changing settings at the command line, and storing the running
  configuration in the EEPROM.

* [usbtest.py](./usbtest.py): An example application that runs the pcProx in
  non-keyboard mode, and flashes the LEDs on the device.

## Other resources

* [Protocol documentation][1] (also explains the behaviour of different device
  settings)

* [Physical disassembly notes](./disassembly.md)

* [Docker container for running `CmdpcProx`](./cmdpcprox_docker)

[0]: https://pypi.org/project/hidapi/
[1]: ./protocol.md
[2]: https://github.com/goliatone/rfid-poc
[3]: https://github.com/google/makerspace-auth/blob/master/software/authbox/badgereader_hid_keystroking.py
[4]: https://github.com/signal11/hidapi/pull/335
