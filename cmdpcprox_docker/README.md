# Docker container for `CmdpcProx`

This directory contains a [Docker container][0] for running [`CmdpcProx`][1].
It is based on [the Debian 9.5-slim Docker base image][2].

This is a very bare-bones image, only intended to offer some isolation around
the `CmdpcProx` utility (such as disabling host network and filesystem access).

> **Note:** This will only work on native Docker for Linux. It will not run in a
> virtualised or cloud Docker environment, nor non-Linux platforms, nor
> architectures other than amd64 and i686.

## Building the image

1. [Install Docker on your system][0].
2. [Download CmdpcProx for Linux][1] into this directory.
3. Build the image: `docker build -t cmdpcprox .`

> **Note:** Building the image requires an internet connection to fetch the
> Docker images, and to also fetch a dependency from Debian's apt repository.

## Running the image

Connect the pcProx to your PC, and find it's USB device node using `lsusb`:

```
$ lsusb
Bus 001 Device 002: ID 0c27:3bfa RFIDeas, Inc pcProx Card Reader
```

> The _bus_ and _device_ numbers shown here _will be different for your
> computer_.  They will also change if the pcProx is reconnected.

Then, run the container using the absolute path to the USB device node
(`/dev/bus/usb/$BUS/$DEVICE`):

```
$ docker run --network none --device /dev/bus/usb/001/002 -it pcprox
```

You'll then get a (root) shell from which you can interact with `CmdpcProx`:

```
root@1a2b3c4d:/# CmdpcProx 
------------------------------------------------------------------------------
CmdpcProx for USB devices Version 0.9.0a (Beta) Copyright 2010 RFIDeas. For Linux

Usage: switch=value ...
       CmdpcProx -version
```

When you're done, exit that shell.

> **Note:** Docker will automatically delete any modified files after you exit
> the shell. If you want to back up your configuration, you should copy it out
> of the container first.
> 
> All pcProx configuration files are plain text, and can be displayed in `cat`.

## Sniffing communications

You can sniff communications between `CmdpcProx` and the pcProx using the
[usbmon kernel module][3]. [Wireshark offers a good GUI front-end to this][4].

[0]: https://www.docker.com/
[1]: https://www.rfideas.com/files/downloads/software/CmdpcProx.tar.gz
[2]: https://hub.docker.com/r/i386/debian/
[3]: https://www.kernel.org/doc/Documentation/usb/usbmon.txt
[4]: https://wiki.wireshark.org/CaptureSetup/USB

