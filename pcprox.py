# -*- mode: python3; indent-tabs-mode: nil; tab-width: 2 -*-
"""
Implements control and configuration code for pcProx readers.

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

This has been tested with the RDR-6081AKU/APU (RFIDeas pcProx 125kHz HID Prox
Desktop USB reader). It might work with other readers, but I don't have any
other readers to test.

This is an open source, cross-platform alternative to the CmdpcProx application.
The configuration options shown here are documented in configuration files
emitted the CmdpcProx tool.
"""

from math import ceil
from time import sleep
from struct import unpack

# https://github.com/trezor/cython-hidapi
import hid


PCPROX_VENDOR = 0x0c27
PCPROX_PRODUCT = 0x3bfa

CONFIG_READ_CMDS = (
  0x8a000000, # firmware / device info
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
    #'iTrailChr0',
    #'iTrailChr1',
    #'iTrailChr2',
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

def _format_hex(i):
  return ' '.join(['%02x' % c for c in i])

def open_pcprox(debug=False):
  """
  Convenience function to find a pcProx by its vendor and product ID, then
  open a connection to it.

  debug: If True, write packet traces to stdout.
  """
  dev = hid.device()
  dev.open(PCPROX_VENDOR, PCPROX_PRODUCT)
  return PcProx(dev, debug=debug)

class DeviceInfo:
  def __init__(self, msg):
    # TODO: figure this out device_type better
    minor_ver, major_ver, self.device_type = unpack('<2xBBxHx', msg)
    self.firmware_version_tuple = (major_ver, minor_ver >> 4, minor_ver & 0xf)

  @property
  def firmware_version(self):
    return '%02d.%d.%d' % self.firmware_version_tuple

  def __repr__(self):
    return '<DeviceInfo: firmware=%s, device=0x%04x>' % (
      self.firmware_version, self.device_type)


class Configuration:
  def __init__(self, pages):
    self.pages = []
    for page in pages:
      self.pages.append(list(page))

  def _int_field(page, pos, first_bit=0, bit_len=8, multiplier=1, max_value=None, character=False):
    # NOTE: this method only supports up to 8 bits
    if max_value is None:
      max_value = ((2 ** bit_len) - 1) * multiplier

    if first_bit > 0:
      bit_len = min(bit_len, 8 - first_bit)

    def getter(self):
      v = self.pages[page][pos]
      
      if character:
        return bytes([v])
    
      if first_bit > 0:
        v >>= first_bit

      if bit_len < 8:
        v &= (2 ** bit_len) - 1

      if multiplier != 1:
        v *= multiplier
      
      return v
    
    def setter(self, new_val):
      if character:
        if isinstance(new_val, str):
          raise Exception('bytestr required')
        
        if isinstance(new_val, bytes) and len(new_val) != 1:
          raise Exception('bytestr must be 1 byte')
      else:    
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

  def _bool_field(page, pos, bit):
    def getter(self):
      return ((self.pages[page][pos] >> bit) & 1) > 0
    
    def setter(self, new_val):
      if new_val:
        self.pages[page][pos] |= 1 << bit
      else:
        self.pages[page][pos] &= 0xff ^ (1 << bit)

    return property(getter, setter)

  # Page 0
  iFACDispLen        = _int_field(0, 0)
  iIDDispLen         = _int_field(0, 1)
  iLeadParityBitCnt  = _int_field(0, 2, bit_len=4)
  iTrailParityBitCnt = _int_field(0, 2, first_bit=4)
  iIDBitCnt          = _int_field(0, 3)
  iTotalBitCnt       = _int_field(0, 4)
  iFACIDDelim        = _int_field(0, 5, character=True)
  iELDelim           = _int_field(0, 6, character=True)

  bFixLenDsp    = _bool_field(0, 7, 0)
  bFrcBitCntEx  = _bool_field(0, 7, 1)
  bStripFac     = _bool_field(0, 7, 2)
  bSndFac       = _bool_field(0, 7, 3)
  bUseDelFac2Id = _bool_field(0, 7, 4)
  bNoUseELChar  = _bool_field(0, 7, 5)
  bSndOnRx      = _bool_field(0, 7, 6)
  bHaltKBSnd    = _bool_field(0, 7, 7)

  # Page 1
  # byte 0 unknown
  iBitStrmTO   = _int_field(1, 1, multiplier=4)
  iIDHoldTO    = _int_field(1, 2, multiplier=50)
  iIDLockOutTm = _int_field(1, 3, multiplier=50)
  iUSBKeyPrsTm = _int_field(1, 4, multiplier=4)
  iUSBKeyRlsTm = _int_field(1, 5, multiplier=4)

  # bit 0 unknown
  bUse64Bit = _bool_field(1, 6, 1)
  # bit 2 unknown
  bPrxProEm = _bool_field(1, 6, 3)
  bSndSFID  = _bool_field(1, 6, 4)
  bSndSFFC  = _bool_field(1, 6, 5)
  bSndSFON  = _bool_field(1, 6, 6)
  bUseNumKP = _bool_field(1, 6, 7)

  # byte 7 unknown

  # Page 2
  iRedLEDState = _bool_field(2, 0, 0)
  iGrnLEDState = _bool_field(2, 0, 1)
  iBeeperState = _bool_field(2, 0, 2)
  iRelayState  = _bool_field(2, 0, 3)
  
  bUseLeadChrs = _bool_field(2, 1, 0)
  bAppCtrlsLED = _bool_field(2, 1, 1)
  bDspHex      = _bool_field(2, 1, 2)
  bWiegInvData = _bool_field(2, 1, 3)
  bBeepID      = _bool_field(2, 1, 4)
  bRevWiegBits = _bool_field(2, 1, 5)
  bRevBytes    = _bool_field(2, 1, 6)
  bUseInvDataF = _bool_field(2, 1, 7)
  
  iCrdGnChr0   = _int_field(2, 2, character=True)
  iCrdGnChr1   = _int_field(2, 3, character=True)
  iLeadChrCnt  = _int_field(2, 4, bit_len=4, max_value=3)
  iTrailChrCnt = _int_field(2, 4, first_bit=4, max_value=3)
  iLeadChr0    = _int_field(2, 5, character=True)
  iLeadChr1    = _int_field(2, 6, character=True)
  iLeadChr2    = _int_field(2, 7, character=True)
  
  # TODO: Handle iTrailChrN

  def generate_config(self):
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
  
  def print_config(self):
    for l in self.generate_config():
      print(l)
  
  def set_config(self, dev, pages=None):
    if pages is None:
      pages = (0, 1, 2)
    
    for i in pages:
      dev.write(bytes([0x80 | i]))
      dev.write(self.pages[i])

class PcProx:
  def __init__(self, dev, debug=False):
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
  
  def write(self, msg):
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

    ret = self._dev.send_feature_report(bytes(1) + msg)

    # TODO: handle return code
    sleep(0.001)

  def read(self):
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

  def interact(self, msg):
    """
    Writes to the device, then reads a message back from it.
    """
    self.write(msg)
    return self.read()

  def get_device_info(self):
    """
    Gets device information from the pcProx.
    """
    return DeviceInfo(self.interact(b'\x8a'))
  
  def get_config(self):
    """
    Gets the running configuration from pcProx.
    """
    ret = []
    for page in (0x80, 0x81, 0x82):
      ret.append(self.interact(bytes([page])))
    
    return Configuration(ret)

  def save_config(self, pages=0x7):
    """
    Writes configuration to the EEPROM for all pages.

    pages: bitmask of pages to write to the EEPROM.
    """
    # defaults to writing all pages
    self.write(bytes([0x90, pages]))

  def end_config(self):
    """
    Finishes configuration without writing to the EEPROM.
    """
    self.save_config(0)
    
  def get_tag(self):
    """
    Reads a single tag, and immediately returns, even if no tag was in the
    field.

    Returns None if no tag was in the field.

    Returns a tuple of (data, buffer_bits) if there was a tag in the field.  See
    `protocol.md` for information about how to interpret this buffer.
    """
    # Must send 8F first, else 8E will never be set!
    card_data = self.interact(b'\x8f')
    if card_data is None:
      return None

    # This cas be skipped without issue if there is no card there
    card_info = self.interact(b'\x8e')
    if card_info is None:
      return None

    bit_length = unpack('<B7x', card_info)[0]

    # Strip off bytes that aren't needed
    buffer_byte_length = int(ceil(bit_length / 8.))
    
    return (card_data[:buffer_byte_length], bit_length)

