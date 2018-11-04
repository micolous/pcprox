# pcProx protocol

This document describes communication with the RF IDeas pcProx readers.

This document comes from [Python pcprox library][0].  It is not an official
document, and not written or endorsed by RFIDeas.  It is written in the hope
that it can be useful for writing compatible software for the pcProx readers
without their proprietary (and costly) SDK.

## Models / firmware

This documentation was written for the following models:

* RDR-6081AKU / RDR-6081APU (125kHz HID Prox Desktop USB reader)

This probably works with other _USB_ HID Prox models:

* RDR-6011AKU / RDR-6021AKU (125kHz HID Prox Vertical/Horizontal Nano reader)
* RDR-60D1AKU (125kHz HID Prox USB dongle)
* RDR-60N1AKU / RDR-60N2AKU (125kHz HID Prox non-housed USB)
* RDR-60W1AKU (125kHz HID Prox surface-mount USB)

Other models may work, but they are not tested.  There are some other models in
the "82 series", but the differences there aren't known.

This is written for devices that emulate a USB keyboard device, that show up in
`lsusb` as `0c27:3bfa RFIDeas, Inc pcProx Card Reader`.

The firmware version tested was `07.3.0` (alternatively written as `07.30` in
configuration dumps).

I haven't looked at the firmware update process, or for firmware images.

## Notation used in this document

All integers here are unsigned and little-endian unless otherwise stated.

Unknown fields are marked as _unknown_.  One should not modify this data.

Data types are as follows:

* `bool`: 1 bit, boolean field (see _sub-byte structures_ below)
* `uint4`: 4 bit, unsigned integer (see _sub-byte structures_ below)
* `uint8`: 8 bit, unsigned integer
* `char`: 8 bit, ASCII character
* `uint16`: 16 bit, unsigned little-endian integer
* `uint24`: 24 bit, unsigned little-endian integer

Additionally, some card formats may utilise lengths that do not align to bytes
-- these are handled in a similar way to _sub-byte_ structures.

### Sub-byte structures

Some data here is contained in sub-byte structures such as bitfields, nibbles
(4 bit integers).

These structures are grouped in curly braces for each byte.

These are documented such that the least significant bit is shown before the
most significant bit.  For example:

```
{
  uint4 a
  uint4 b
}
```

The resulting byte would be packed as `a | (b << 4)`.  If `a = 0xf` and
`b = 0x3`, then the byte would be `0x3f`.

A bitfield may be listed as:

```
{
   bool a
   bool b
   bool unknown
   bool c
   bool d
}
```

In this case, the bitfield should be interpreted as:

bit    | field
-------|-------
`0x01` | a
`0x02` | b
`0x04` | _unknown_
`0x08` | c
`0x10` | d

In the case of omitted bits, the remaining bits should be considered unknown.

## USB communication

The pcProx readers expose a USB HID (keyboard) device to the host.

This driver is typically bound by the operating system, which can make direct
communications more difficult.  Typically this will require some extra
permissions, or changing the permissions on the device node.

All communication happens with [USB control transfers][usb-ctrl].

There are two basic, high-level commands: `read` and `write`.  Every `read` and
every `write` is 8 bytes long.

### write

A `write` is an OUT USB control transfer that always contains 8 bytes of data.

This is used to send commands to the device.

The message contains these attributes:

```
bmRequestType = 0x21
bRequest      = 0x09
wValue        = 0x0300
wIndex        = 0x00
data          = (command to send)
wLength       = 0x08 (bytes)
```

### read

A `read` is an IN USB control transfer, that is always for 8 bytes of data.

This is used to get the response to a previous `write` command.

The message contains these attributes:

```
bmRequestType = 0xa1
bRequest      = 0x01
wValue        = 0x0300
wIndex        = 0x00
wLength       = 0x08 (bytes)
```

## Commands

There are four types of commands:

* _get_ commands: `write` commands that are followed with a `read` to get data
  from the device.

* _put_ commands: `write` commands that are followed with another `write` to
  change data on the device.

* _get+put_ commands: `write` commands that may be followed with either a `read`
  to get data, or a `write` to change data.

* _stateless_ commands: `write` commands that are never followed with another
  command.

Commands follow the structure:

```c
uint8 code
uint8 parameter0
uint8 parameter1
uint8 parameter2
uint8 parameter3
uint8 parameter4
uint8 parameter5
uint8 parameter6
```

If a command doesn't take any parameters, then these should be left as `0x0`.

### List of commands

code   | get | put | description
-------|----------|-----------|-----------------------
`0x80` | :heavy_check_mark: | :heavy_check_mark: | Configuration page 0
`0x81` | :heavy_check_mark: | :heavy_check_mark: | Configuration page 1
`0x82` | :heavy_check_mark: | :heavy_check_mark: | Configuration page 2
`0x83` | :heavy_check_mark: | | ?? Configuration page 3 ??
`0x85` | :heavy_check_mark: | | ?? Configuration page 5 ??
`0x8a` | :heavy_check_mark: | :no_entry_sign: | Device info
`0x8c` | :heavy_check_mark: | | Configuration?
`0x8e` | :heavy_check_mark: | :no_entry_sign: | Card read buffer 1
`0x8f` | :heavy_check_mark: | :no_entry_sign: | Card read buffer 0
`0x90` | :no_entry_sign: | :no_entry_sign: | Finish configuration

### Device info

* code: `0x8c`
* parameters: _none_
* get: :heavy_check_mark:
* put: _unlikely_

This gets the firmware version:

```c
uint8 unknown
uint8 unknown
{
   uint4 minor_version
   uint4 release_version
}
uint8 major_version
uint8 unknown
uint16 device_type
uint8 unknown
```

### Finish configuration

* code: `0x90`
* parameters: bitmask of pages to write to EEPROM in _parameter0_.
* get: :no_entry_sign:
* put: :no_entry_sign:

This instructs the device that configuration has finished and to resume normal
operation.

The configuration may be optionally saved to the device's EEPROM, using a
bitmask in _parameter0_:

```c
{
   bool page0
   bool page1
   bool page2
}
```

If the configuration is written to the EEPROM, the device uses this
configuration on next power-on.

### Configuration pages

* code: `0x80`, `0x81` `0x82`
* parameters: _none_
* get: :heavy_check_mark:
* put: :heavy_check_mark:

This instructs the device to select a configuration page for reading or writing.

If _writing_ to the configuration, this must then be followed by a _finish
configuration_ command to resume normal device operation.

#### Page 0 (0x80)

```c
uint8 iFACDispLen
uint8 iIDDispLen
{
   uint4 iLeadParityBitCnt
   uint4 iTrailParityBitCnt
}
uint8 iIDBitCnt
uint8 iTotalBitCnt
char iFACIDDelim
char iELDelim
{
  bool bFixLenDsp
  bool bFrcBitCntEx
  bool bStripFac
  bool bSndFac
  bool bUseDelFac2Id
  bool bNoUseELChar
  bool bSndOnRx
  bool bHaltKBSnd
}
```

#### Page 1 (0x81)

```c
uint8 unknown
uint8 iBitStrmTO
uint8 iIDHoldTO
uint8 iIDLockOutTm
uint8 iUSBKeyPrsTm
uint8 iUSBKeyRlsTm
{
  bool unknown
  bool bUse64Bit
  bool unknown
  bool bPrxProEm
  bool bSndSFID
  bool bSndSFFC
  bool bSndSFON
  bool bUseNumKP
}
uint8 unknown
```

#### Page 2 (0x82)

```c
{
  bool iRedLEDState
  bool iGrnLEDState
  bool iBeeperState
  bool iRelayState
}
{
  bool bUseLeadChrs
  bool bAppCtrlsLED
  bool bDspHex
  bool bWiegInvData
  bool bBeepID
  bool bRevWiegBits
  bool bRevBytes
  bool bUseInvDataF
}
char iCrdGnChr0
char iCrdGnChr1
{
  uint4 iLeadChrCnt
  uint4 iTrailChrCnt
}
char iLeadChr0
char iLeadChr1
char iLeadChr2
```

`iLeadChr*` is shared with `iTrailChr*` as follows:

* `iLeadChrCnt + iTrailChr` must be less than or equal to 3
* `iTrailChr0` is offset by `iLeadChrCnt`.  ie:

  * if `iLeadChrCnt = 0`, then `iTrailChr0` is stored in `iLeadChr0`.
  * if `iLeadChrCnt = 1`, then `iTrailChr0` is stored in `iLeadChr1`.
  * if `iLeadChrCnt = 2`, then `iTrailChr0` is stored in `iLeadChr2`.
  * if `iLeadChrCnt = 3`, then no `iTrailChr` can be stored.

### Card read buffer

* code: `0x8f`, `0x8e`
* parameters: _none_
* get: :heavy_check_mark:
* put: _unlikely_

This gets the contents of the card read buffer.

For _HID cards_, pcProx will:

* Remove parity bits according to `iLeadParityBitCnt` and `iTrailParityBitCnt`.
  _Parity bits are never checked._

* If `bFrcBitCntEx = 1`, then only cards with a length of `iTotalBitCnt` will be
  read.  Non-matching cards will get no response from the reader.

* If `bFrcBitCntEx = 0`, then any card will be read.

> **Note:** You get raw card data, so `iIDBitCnt` is not relevant for this
> method.

#### Buffer 0 (0x8f)

This buffer contains the card data. Parity bits will be stripped according to
`iLeadParityBitCnt` and `iTrailParityBitCnt`.

This is not a complete list -- but a [more complete list of general data layouts
is available here][barkweb-weigand].

> **Note:** A single bit length on a HID can have multiple meanings, depending
> on the system.

For the 26-bit HID layout (H10301), with
`iLeadParityBitCnt = 1, iTrailParityBitCnt = 1`:

```
uint16 card_number
uint8 facility_code
```

For the Corporate 1000 35-bit layout, with
`iLeadParityBitCnt = 2, iTrailParityBitCnt = 1`:


```
uint20 card_number // bytes 0-1, lower nibble of byte 2
uint12 facility_code // upper nibble of byte 2, byte 3
```

For the Corporate 1000 48-bit standard layout, with
`iLeadParityBitCnt = 2, iTrailParityBitCnt = 1`:

```
uint23 card_number // bytes 0-1, lower 7 bits of byte 2
uint24 facility_code // highest bit of byte 2, byte 3, lower 7 bits of byte 4
```

#### Buffer 1 (0x8e)

This buffer contains information about the card.

```
uint8 buffer_length
uint8 buffer_length (again)
```

`buffer_length` is the number of bits of data from the card that are in Buffer
0.

The total bit length of the card is
`buffer_length + iLeadParityBitCnt + iTrailParityBitCnt`.



[usb-ctrl]: https://www.beyondlogic.org/usbnutshell/usb4.shtml
[barkweb-wiegand]: http://cardinfo.barkweb.com.au/

