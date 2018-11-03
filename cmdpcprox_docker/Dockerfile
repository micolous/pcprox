FROM i386/debian:9.5-slim
RUN apt-get -y update && apt-get install -y libusb-1.0-0 && ln -s /opt/pcprox/CmdpcProx /usr/local/bin/
ADD CmdpcProx.tar.gz /opt/pcprox/
CMD ["bash"]

