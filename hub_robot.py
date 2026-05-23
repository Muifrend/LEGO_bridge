# hub_robot.py
# LEGO SPIKE Prime / Pybricks robot program
#
# Current wiring from your port scan:
#   Left drive motor:      Port C
#   Right drive motor:     Port D
#   Distance sensor:       Port E
#
# No scoop motor is connected right now.
#
# Commands from laptop bridge are 3 bytes:
#   fwd = short forward
#   bak = short backward
#   lft = short left turn
#   rgt = short right turn
#   stp = stop
#   dst = report distance
#   aln = scan left/center/right and turn toward nearest object
#   psh = approach and push
#   bye = exit program

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port, Direction
from pybricks.robotics import DriveBase
from pybricks.tools import wait

from usys import stdin, stdout
from uselect import poll


hub = PrimeHub()

# Your actual wiring:
# Port C = motor
# Port D = motor
# Port E = distance sensor
left_motor = Motor(Port.C, Direction.COUNTERCLOCKWISE)
right_motor = Motor(Port.D)
eyes = UltrasonicSensor(Port.E)

# Tune axle_track later if turning is inaccurate.
robot = DriveBase(
    left_motor,
    right_motor,
    wheel_diameter=56,
    axle_track=116,
)

robot.settings(
    straight_speed=150,
    straight_acceleration=300,
    turn_rate=90,
    turn_acceleration=180,
)

keyboard = poll()
keyboard.register(stdin)


def send(msg):
    """Send a short status message back to the laptop bridge."""
    stdout.write(str(msg))


def dist_mm():
    """Return distance in mm. 2000 means no valid object detected."""
    try:
        return eyes.distance()
    except Exception:
        return 2000


def stop():
    robot.stop()


def scan_and_align():
    """
    Simple alignment:
    1. Read distance straight ahead.
    2. Turn left 30 degrees and read.
    3. Turn right 60 degrees and read.
    4. Face the direction with the closest object.
    """

    center = dist_mm()

    robot.turn(-30)
    wait(100)
    left = dist_mm()

    robot.turn(60)
    wait(100)
    right = dist_mm()

    # Robot is now facing +30 degrees from original center.
    readings = [
        ("left", left),
        ("center", center),
        ("right", right),
    ]

    best_name, best_val = min(readings, key=lambda x: x[1])

    # If nothing was seen, return to center and report no object.
    if best_val >= 1900:
        robot.turn(-30)
        send("OK:ALN:NO_OBJECT")
        return

    if best_name == "left":
        # Current heading is +30. Left target was -30.
        robot.turn(-60)

    elif best_name == "center":
        # Current heading is +30. Center target was 0.
        robot.turn(-30)

    else:
        # Already facing the right target.
        pass

    send("OK:ALN:%s:%s" % (best_name, best_val))


def approach_and_push():
    """
    Approach the nearest object and push it forward.
    This is the no-scoop-motor version.
    """

    # Approach in short chunks.
    for _ in range(10):
        d = dist_mm()

        if d < 100:
            break

        robot.straight(70)
        wait(50)

    # Push/corral the object.
    robot.straight(180)
    wait(100)

    # Back up so the demo looks complete.
    robot.straight(-120)
    stop()

    send("OK:PSH:%s" % dist_mm())


def run_command(cmd):
    if cmd == b"fwd":
        robot.straight(120)
        send("OK:FWD")

    elif cmd == b"bak":
        robot.straight(-120)
        send("OK:BAK")

    elif cmd == b"lft":
        robot.turn(-25)
        send("OK:LFT")

    elif cmd == b"rgt":
        robot.turn(25)
        send("OK:RGT")

    elif cmd == b"stp":
        stop()
        send("OK:STP")

    elif cmd == b"dst":
        send("OK:DST:%s" % dist_mm())

    elif cmd == b"aln":
        scan_and_align()

    elif cmd == b"psh":
        approach_and_push()

    else:
        stop()
        send("ERR:UNKNOWN")


send("BOOT")

while True:
    # Tell the laptop bridge that the hub is ready for one 3-byte command.
    stdout.write("rdy")

    while not keyboard.poll(0):
        wait(10)

    cmd = stdin.buffer.read(3)

    if cmd == b"bye":
        stop()
        send("OK:BYE")
        break

    run_command(cmd)