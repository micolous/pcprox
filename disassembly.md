# pcProx disassembly

This document describes the (physical) internals of the pcProx RFID readers.

This document comes from [Python pcprox library][0].  It is not an official
document, and not written or endorsed by RFIDeas.  It is written in the hope
that it can be useful.

This documentation was written for the following models:

* RDR-6081AKU / RDR-6081APU (125kHz HID Prox Desktop USB reader)

## Opening

There appear to be no screws in the case.  The rubber feet and stickers can stay
on the case when opening.

The case is held together by friction, with four poles on the "top" of the case
which go into sockets on the "base" of the case:

* Two are located on either side of the cord, approximately half way between the
  cord and the edge of the case, near the edge.
  
* Two are located on the left and right edges of the device, about half way down

Take care when opening, as the antenna coil is loose and may be pulled off when
opening the case, requiring resoldering.

Otherwise the case can be pushed open from the side opposite the cord with
either a flat-head screwdriver or a guitar pick.

## Major components

* [Microchip PIC18F2450][PIC18F2450] single-chip microcontroller
* [HID eProx MCM 4025][4025] multi-chip OEM reader module
* Antenna coil
* Red LED
* Green LED
* Piezo-electric buzzer

TODO: Look in to this more and find some interesting things. 8)

There are some unpopulated headers on the board which might be useful.


[0]: https://github.com/micolous/pcprox
[PIC18F2450]: https://www.microchip.com/wwwproducts/en/PIC18F2450
[4025]: https://www.hidglobal.com/products/embedded-modules/hid-proximity/4025

