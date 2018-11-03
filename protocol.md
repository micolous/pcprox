# pcProx protocol

This document describes communication with the RF IDeas pcProx readers.

This is not an official document, and was written to aid in writing compatible
software for the pcProx readers.

This documentation was written for the following models:

* RDR-6081AKU / RDR-6081APU (125kHz HID Prox Desktop USB reader)

Other models may work, but they are not tested.

## USB communication

The pcProx readers expose a USB HID (keyboard) device to the host.

This driver is typically bound by the operating system, which can make direct
communications more difficult.  Typically this will require some extra
permissions, or changing the permissions on the device node.

There are two basic, high-level commands: `read` and `write`.  Every `read` and
every `write` is 8 bytes long.

### write

A write consists of:

```
   bmRequestType = 0x21
   bRequest      = 0x09
   wValue        = 0x0300
   wIndex        = 0x00
   data          = 8 bytes
```

This sends a command to the device.

### read

A read consists of:

```
   bmRequestType = 0xa1
   bRequest      = 0x01
   wValue        = 0x0300
   wIndex        = 0x00
   length        = 8 bytes
```

These reads don't contain any command information, and is given in response to
a previous `write`.

## Commands

### Device info / firmware version

Write: `8a 00 00 00  00 00 00 00`

Then peform a read.

This gets the firmware version:

```c
   char[2] unknown,
   {
      uint4 minor_version,
      uint4 release_version,
   }
   uint8 major_version
   char[1] unknown,
   uint16 device_type,
   char[1] unknown,
```

### Reading/writing configuration options

1. Do a get
2. Then write the data
3. Then "finish"

