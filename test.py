from pybricks.hubs import PrimeHub
from pybricks.parameters import Port
from pybricks.iodevices import PUPDevice
from pybricks.tools import wait
from uerrno import ENODEV

hub = PrimeHub()

for port in [Port.A, Port.B, Port.C, Port.D, Port.E, Port.F]:
    try:
        dev = PUPDevice(port)
        print(port, dev.info())
    except OSError as e:
        if e.args[0] == ENODEV:
            print(port, "EMPTY / NOT DETECTED")
        else:
            print(port, "ERROR", e)

wait(10000)
