# pcProx protocol

This document describes communication with the RFIDeas pcProx readers.

This document comes from [Python pcprox library][0].  It is not an official
document, and not written or endorsed by RFIDeas.

This document is written in the hope that it can be useful for writing
compatible software for the pcProx readers without needing their proprietary
SDK.

## Models / firmware

This documentation was written for the following models:

* RDR-6081AKU / RDR-6081APU (125kHz HID Prox Desktop USB reader)

This probably works with other _USB_ HID Prox models (`RDR-60_1A_U`):

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

## Notation used in this document

All integers here are unsigned and little-endian unless otherwise stated.

Unknown fields are marked as _unknown_.  One should not modify this data.

Data types are as follows:

* `bool`: 1 bit, boolean field (see _sub-byte structures_ below)
* `uint4`: 4 bit, unsigned integer (see _sub-byte structures_ below)
* `uint8`: 8 bit, unsigned integer
* `char`: 8 bit, [keyboard scancode][scancodes]. Bit 0x80 indicates SHIFT state (eg: 0x04 = a, 0x84 = A)
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

The pcProx readers expose a USB HID (keyboard) device to the host, using
USB device ID `0c27:3bfa`.

This driver is typically bound by the operating system, which can make direct
communications more difficult. There are some [udev rules
included](./udev/60-rfideas-permissions.rules) which make this easier.

All communication happens with [USB control transfers][usb-ctrl].

There are two basic, high-level commands: `read` and `write`.  Every `read` and
every `write` is 8 bytes long.

### read

A `read` is a [USB HID][usb-hid] Get Feature Report. Report IDs are not used.
Reports are always 8 bytes long.

This is used to get the response to a previous `write` command.

The message contains these attributes:

```
bmRequestType = 0xa1
bRequest      = 0x01    (GET_REPORT)
wValue        = 0x0300  (FEATURE, report ID 0)
wIndex        = 0x00    (Interface)
wLength       = 0x08    (bytes)
```

hidapi: `hid_get_feature_report(device, "\0" + 8 byte buffer, 9)`

**Note:** Due to [a bug in hidapi on OSX][hidapi-osx], you need to send a
slightly different command which includes a report ID:

```c
char* buf = "\1\0\0\0\0\0\0";
hid_get_feature_report(device, &buf, 8);
```

This results in a different `wValue`, but the device seems to still accept it.

### write

A `write` is a [USB HID][usb-hid] Set Feature Report. Report IDs are not used.
Reports are always 8 bytes long.

This is used to send commands to the device.

The message contains these attributes:

```
bmRequestType = 0x21
bRequest      = 0x09    (SET_REPORT)
wValue        = 0x0300  (FEATURE, report ID 0)
wIndex        = 0x00    (Interface)
data          = (command to send)
wLength       = 0x08    (bytes)
```

hidapi: `hid_send_feature_report(device, "\0" + msg, 9)`

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

Configuration options are also described in [the configuration utility
manual][config-manual], and in exported "HWG" files.

#### Page 0 (0x80)

```c
uint8 iFACDispLen           // If bFixLenDsp = 1, facility codes will be padded
                            // to this many digits (with zeros).

uint8 iIDDispLen            // If bFixLenDsp = 1, card IDs will be padded to
                            // this many digits (with zeros).

{
   uint4 iLeadParityBitCnt  // Number of leading bits to strip from the card
                            // data.

   uint4 iTrailParityBitCnt // Number of trailing bits to strip from the card
                            // data.
}
uint8 iIDBitCnt             // If bStripFac = 1, only the first iIDBitCnt bits
                            // will be returned.

uint8 iTotalBitCnt          // If bFrcBitCntEx = 1, only cards with this many
                            // bits will be read (including parity).

char iFACIDDelim            // If bUseDelFac2Id = 1, this character is sent
                            // between the facility code and card ID.

char iELDelim               // If bNoUseELChar = 0, this character is sent after
                            // the card ID. Default = 40 (ENTER)

{
  bool bFixLenDsp           // If 1, IDs are padded to iIDDispLen digits, and
                            // facility codes are padded to iFACDispLen digits.

  bool bFrcBitCntEx         // If 1, only cards with iTotalBitCnt bits will be
                            // read.

  bool bStripFac            // If 1, only the first iIDBitCnt bits will be
                            // returned for the card ID.

  bool bSndFac              // If 1, and if bStripFac = 1, the facility code
                            // will be sent.

  bool bUseDelFac2Id        // If 1, and if bStripFac = 1 and bSndFac = 1,
                            // iFACIDDelim will be sent between the facility
                            // code and the card ID.

  bool bNoUseELChar         // If 0, sends iELDelim after the card ID. If 1,
                            // doesn't send anything.

  bool bSndOnRx             // TODO

  bool bHaltKBSnd           // If 0, the card number will be sent as keystrokes.
                            // If 1, then the card data can only be read with
                            // the 'card read buffer' commands.
}
```

#### Page 1 (0x81)

```c
uint8 unknown
uint8 iBitStrmTO            // in 4ms increments
uint8 iIDHoldTO             // in 50ms increments
uint8 iIDLockOutTm          // in 50ms increments
uint8 iUSBKeyPrsTm          // in 4ms increments
uint8 iUSBKeyRlsTm          // in 4ms increments
{
  bool unknown
  bool bUse64Bit
  bool unknown
  bool bPrxProEm
  bool bSndSFID
  bool bSndSFFC
  bool bSndSFON
  bool bUseNumKP            // Send numbers using numeric keypad scancodes. This
                            // requires NumLock be turned on. This is useful for
                            // keyboards where the numbers are not on the top
                            // row of the keyboard in the unshifted state (eg:
                            // French AZERTY, 1-handed Dvorak layouts)
}
uint8 unknown
```

#### Page 2 (0x82)

```c
{
  bool iRedLEDState         // If bAppCtrlsLED = 1, the state of the red LED.
  bool iGrnLEDState         // If bAppCtrlsLED = 1, the state of the green LED.
  bool iBeeperState         // Appears to do nothing?
  bool iRelayState          // Appears to do nothing?
}
{
  bool bUseLeadChrs
  bool bAppCtrlsLED         // If 1, then iRedLEDState and iGrnLEDState will be
                            // used. If 0, the reader controls the LEDs.

  bool bDspHex              // If 1, emits card ID and facility code as
                            // hexadecimal (only works on QWERTY-like
                            // keyboards). If 0, emits them as decimal.
                            // TODO: check bSndSFFC/bSndSFID

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

This works best when `bHaltKBSnd = 1`, which will prevent pcProx from sending
keystrokes for the card ID. [The configuration manual][config-manual] describes
this as _Software Developer Kit (SDK) Mode_.

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
is available here][barkweb-wiegand].

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


[0]: https://github.com/micolous/pcprox
[usb-ctrl]: https://www.beyondlogic.org/usbnutshell/usb4.shtml
[usb-hid]: https://www.usb.org/sites/default/files/documents/hid1_11.pdf
[barkweb-wiegand]: http://cardinfo.barkweb.com.au/
[scancodes]: https://www.win.tue.nl/~aeb/linux/kbd/scancodes-14.html
[hidapi-osx]: https://github.com/signal11/hidapi/pull/219
[config-manual]: https://www.rfideas.com/files/rfideas/files/support/doc/manuals/pcProx_Manual.pdf
