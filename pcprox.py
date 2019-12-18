# -*- mode: python3; indent-tabs-mode: nil; tab-width: 4 -*-
"""
Implements control and configuration code for pcProx readers.

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

This has been tested with the RDR-6081AKU/APU (RFIDeas pcProx 125kHz HID Prox
Desktop USB reader). It might work with other readers, but I don't have any
other readers to test.

This is an open source, cross-platform alternative to the CmdpcProx
application. The configuration options shown here are documented in the
configuration files emitted by the CmdpcProx tool.
"""

from __future__ import annotations

from math import ceil
from struct import unpack
from time import sleep
from typing import Iterable, Iterator, Optional, Sequence, Text, Tuple, Union

# https://github.com/trezor/cython-hidapi
import hid

if not hasattr(hid, 'device'):
    # https://github.com/micolous/pcprox/issues/1
    raise ImportError(
        'You have the wrong "hid" module in your Python path, please install '
        'the correct one from https://github.com/trezor/cython-hidapi')

PCPROX_VENDOR = 0x0c27
PCPROX_PRODUCT = 0x3bfa

CONFIG_READ_CMDS = (
    0x8a000000,  # firmware / device info
    0x80000000,
    0x81000000,
    0x82000000,
    # TODO: also read/handle page 83+
    0x83000000,
    # 84 is skipped
    0x85000000,
    0x8c010000,
    0x8c010100,
    0x8c010200,
)

NULL_MSG = bytes(8)

CONFIG_PARAMS = (
    ('tsIDBitCnts', (
        'iLeadParityBitCnt',
        'iTrailParityBitCnt',
        'iIDBitCnt',
        'iTotalBitCnt',
    )),
    ('tsCfgFlags', (
        'bFixLenDsp',
        'bFrcBitCntEx',
        'bStripFac',
        'bSndFac',
        'bUseDelFac2Id',
        'bNoUseELChar',
        'bSndOnRx',
        'bHaltKBSnd',
    )),
    ('tsIDDispParms', (
        'iFACIDDelim',
        'iELDelim',
        'iIDDispLen',
        'iFACDispLen',
    )),
    ('tsTimeParms', (
        'iBitStrmTO',
        'iIDHoldTO',
        'iIDLockOutTm',
        'iUSBKeyPrsTm',
        'iUSBKeyRlsTm',
    )),
    ('tsCfgFlags2', (
        'bUseLeadChrs',
        'bDspHex',
        'bWiegInvData',
        'bUseInvDataF',
        'bRevWiegBits',
        'bBeepID',
        'bRevBytes',
    )),
    ('tsCfgFlags3', (
        'bUseNumKP',
        'bSndSFON',
        'bSndSFFC',
        'bSndSFID',
        'bPrxProEm',
        'bUse64Bit',
    )),
    ('tsIDDispParms2', (
        'iLeadChrCnt',
        'iLeadChr0',
        'iLeadChr1',
        'iLeadChr2',
        'iCrdGnChr0',
        'iCrdGnChr1',
    )),
    ('tsIDDispParms3', (
        'iTrailChrCnt',
        # 'iTrailChr0',
        # 'iTrailChr1',
        # 'iTrailChr2',
    )),
    ('tsLEDCtrl', (
        'bAppCtrlsLED',
        'iRedLEDState',
        'iGrnLEDState',
    )),
    ('tsBprRlyCtrl', (
        'iBeeperState',
        'iRelayState',
    )),
)


def _format_hex(i: bytes) -> Text:
    return ' '.join(['%02x' % c for c in i])


def _int_field(page: int,
               pos: int,
               first_bit: int = 0,
               bit_len: int = 8,
               multiplier: int = 1,
               max_value: Optional[int] = None) -> property:
    """Property declaration for integer fields."""
    # NOTE: this method only supports up to 8 bits
    if max_value is None:
        max_value = ((2 ** bit_len) - 1) * multiplier

    if first_bit > 0:
        bit_len = min(bit_len, 8 - first_bit)

    def getter(self) -> int:
        v = self.pages[page][pos]

        if first_bit > 0:
            v >>= first_bit

        if bit_len < 8:
            v &= (2 ** bit_len) - 1

        if multiplier != 1:
            v *= multiplier

        return v

    def setter(self, new_val: int):
        if new_val > max_value or new_val < 0:
            raise Exception('value must be in range 0..%d' % max_value)

        old_val = 0
        mask = 0xff
        new_val //= multiplier

        if first_bit != 0 or bit_len != 8:
            old_val = self.pages[page][pos]

            # Mask out the bits
            mask = (((2 ** bit_len) - 1) << first_bit)
            old_val &= 0xff ^ mask

            new_val <<= first_bit

        new_val &= mask

        new_val |= old_val

        self.pages[page][pos] = new_val

    return property(getter, setter)


def _bool_field(page: int, pos: int, bit: int) -> property:
    """Property definition for boolean fields."""
    def getter(self):
        return ((self.pages[page][pos] >> bit) & 1) > 0

    def setter(self, new_val):
        if new_val:
            self.pages[page][pos] |= 1 << bit
        else:
            self.pages[page][pos] &= 0xff ^ (1 << bit)

    return property(getter, setter)


def _char_field(page: int, pos: int) -> property:
    int_prop = _int_field(page, pos)

    def getter(self) -> bytes:
        return bytes([int_prop.fget(self)])

    def setter(self, new_val: Union[bytes, int]) -> None:
        if isinstance(new_val, int):
            # convert to bytes
            new_val = bytes([new_val])

        if not isinstance(new_val, bytes):
            raise TypeError('bytes required')

        if len(new_val) != 1:
            raise TypeError('bytes must be 1 byte')

        int_prop.fset(self, new_val[0])

    return property(getter, setter)


def open_pcprox(debug: bool = False) -> PcProx:
    """
  Convenience function to find a pcProx by its vendor and product ID, then
  open a connection to it.

  debug: If True, write packet traces to stdout.
  """
    dev = hid.device()
    dev.open(PCPROX_VENDOR, PCPROX_PRODUCT)
    return PcProx(dev, debug=debug)


class DeviceInfo:
    def __init__(self, msg: bytes):
        # TODO: figure this out device_type better
        minor_ver, major_ver, self.device_type = unpack('<2xBBxHx', msg)
        self.firmware_version_tuple = (
            major_ver, minor_ver >> 4, minor_ver & 0xf)

    @property
    def firmware_version(self) -> Text:
        return '%02d.%d.%d' % self.firmware_version_tuple

    def __repr__(self) -> Text:
        return '<DeviceInfo: firmware=%s, device=0x%04x>' % (
            self.firmware_version, self.device_type)


class Configuration:
    def __init__(self, pages: Iterable[Optional[bytes]]):
        self.pages = []
        for page in pages:
            self.pages.append(bytearray(page))

    # Page 0
    iFACDispLen = _int_field(0, 0)
    iIDDispLen = _int_field(0, 1)
    iLeadParityBitCnt = _int_field(0, 2, bit_len=4)
    iTrailParityBitCnt = _int_field(0, 2, first_bit=4)
    iIDBitCnt = _int_field(0, 3)
    iTotalBitCnt = _int_field(0, 4)
    iFACIDDelim = _char_field(0, 5)
    iELDelim = _char_field(0, 6)

    bFixLenDsp = _bool_field(0, 7, 0)
    bFrcBitCntEx = _bool_field(0, 7, 1)
    bStripFac = _bool_field(0, 7, 2)
    bSndFac = _bool_field(0, 7, 3)
    bUseDelFac2Id = _bool_field(0, 7, 4)
    bNoUseELChar = _bool_field(0, 7, 5)
    bSndOnRx = _bool_field(0, 7, 6)
    bHaltKBSnd = _bool_field(0, 7, 7)

    # Page 1
    # byte 0 unknown
    iBitStrmTO = _int_field(1, 1, multiplier=4)
    iIDHoldTO = _int_field(1, 2, multiplier=50)
    iIDLockOutTm = _int_field(1, 3, multiplier=50)
    iUSBKeyPrsTm = _int_field(1, 4, multiplier=4)
    iUSBKeyRlsTm = _int_field(1, 5, multiplier=4)

    # bit 0 unknown
    bUse64Bit = _bool_field(1, 6, 1)
    # bit 2 unknown
    bPrxProEm = _bool_field(1, 6, 3)
    bSndSFID = _bool_field(1, 6, 4)
    bSndSFFC = _bool_field(1, 6, 5)
    bSndSFON = _bool_field(1, 6, 6)
    bUseNumKP = _bool_field(1, 6, 7)

    # byte 7 unknown

    # Page 2
    iRedLEDState = _bool_field(2, 0, 0)
    iGrnLEDState = _bool_field(2, 0, 1)
    iBeeperState = _bool_field(2, 0, 2)
    iRelayState = _bool_field(2, 0, 3)

    bUseLeadChrs = _bool_field(2, 1, 0)
    bAppCtrlsLED = _bool_field(2, 1, 1)
    bDspHex = _bool_field(2, 1, 2)
    bWiegInvData = _bool_field(2, 1, 3)
    bBeepID = _bool_field(2, 1, 4)
    bRevWiegBits = _bool_field(2, 1, 5)
    bRevBytes = _bool_field(2, 1, 6)
    bUseInvDataF = _bool_field(2, 1, 7)

    iCrdGnChr0 = _char_field(2, 2)
    iCrdGnChr1 = _char_field(2, 3)
    iLeadChrCnt = _int_field(2, 4, bit_len=4, max_value=3)
    iTrailChrCnt = _int_field(2, 4, first_bit=4, max_value=3)
    iLeadChr0 = _char_field(2, 5)
    iLeadChr1 = _char_field(2, 6)
    iLeadChr2 = _char_field(2, 7)

    # TODO: Handle iTrailChrN

    def generate_config(self) -> Iterator[Text]:
        for section, keys in CONFIG_PARAMS:
            yield '/ %s' % section
            for key in keys:
                v = getattr(self, key)
                if isinstance(v, bytes):
                    v = v[0]
                if isinstance(v, bool):
                    v = int(v)

                yield '%s = %d' % (key, v)
            yield ''

    def print_config(self) -> None:
        for l in self.generate_config():
            print(l)

    def set_config(self, dev: PcProx, pages: Optional[Sequence[int]] = None):
        if pages is None:
            pages = (0, 1, 2)

        for i in pages:
            dev.write(bytes([0x80 | i]))
            dev.write(bytes(self.pages[i]))


class PcProx:
    def __init__(self, dev, debug: bool = False):
        """
        Opens a connection to a pcProx device.

        dev: hidapi device reference to which device to connect to.
        debug: if True, this library will write USB packets to stdout.
        """
        self._dev = dev
        self._debug = debug
        self._dev.set_nonblocking(1)

    def close(self):
        # TODO
        pass

    def write(self, msg: bytes) -> None:
        # Sends a message to the device.
        # This needs to be exactly 8 bytes.
        msg = bytes(msg)
        if len(msg) > 8:
            raise Exception('Can only send up to 8 byte messages.')

        # Pad short commands with NULL bytes
        if len(msg) < 8:
            msg += bytes(8 - len(msg))

        if self._debug:
            print('USB TX: >>> ' + _format_hex(msg))

        self._dev.send_feature_report(bytes(1) + msg)

        # TODO: handle return code
        sleep(0.001)

    def read(self) -> Optional[bytes]:
        """
        Reads a message from the device as a bytes object.

        All messages are 8 bytes long. ie: len(d.read) == 8.

        If a message of all NULL bytes is returned, then this method will instead
        return None.
        """
        msg = self._dev.get_feature_report(1, 8)

        # Feature reports have a report number added to them, skip that.
        msg = bytes(msg)

        if self._debug:
            print('USB RX: >>> ' + _format_hex(msg))

        if not msg or msg == NULL_MSG:
            return None

        return msg

    def interact(self, msg: bytes) -> Optional[bytes]:
        """
        Writes to the device, then reads a message back from it.
        """
        self.write(msg)
        return self.read()

    def get_device_info(self) -> DeviceInfo:
        """
        Gets device information from the pcProx.
        """
        return DeviceInfo(self.interact(b'\x8a'))

    def get_config(self) -> Configuration:
        """
        Gets the running configuration from pcProx.
        """
        ret = []
        for page in (0x80, 0x81, 0x82):
            ret.append(self.interact(bytes([page])))

        return Configuration(ret)

    def save_config(self, pages: int = 0x7) -> None:
        """
        Writes configuration to the EEPROM for all pages.

        pages: bitmask of pages to write to the EEPROM.
        """
        # defaults to writing all pages
        self.write(bytes([0x90, pages]))

    def end_config(self) -> None:
        """
        Finishes configuration without writing to the EEPROM.
        """
        self.save_config(0)

    def get_tag(self) -> Optional[Tuple[bytes, int]]:
        """
        Reads a single tag, and immediately returns, even if no tag was in the
        field.

        Returns None if no tag was in the field.

        Returns a tuple of (data, buffer_bits) if there was a tag in the field. See
        `protocol.md` for information about how to interpret this buffer.
        """
        # Must send 8F first, else 8E will never be set!
        card_data = self.interact(b'\x8f')
        if card_data is None:
            return None

        # This can be skipped without issue if there is no card there
        card_info = self.interact(b'\x8e')
        if card_info is None:
            return None

        bit_length = unpack('<B7x', card_info)[0]

        # Strip off bytes that aren't needed
        buffer_byte_length = int(ceil(bit_length / 8.))

        return card_data[:buffer_byte_length], bit_length
