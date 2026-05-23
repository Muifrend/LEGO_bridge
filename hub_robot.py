# hub_robot.py
# LEGO SPIKE Prime / Pybricks robot program
#
# Current wiring from your port scan:
#   Left drive motor:      Port C
#   Right drive motor:     Port D
#   Distance sensor:       Port E
#   Sweeper motor:         Port F
#
# Commands from laptop bridge are 3 bytes:
#   fwd = short forward
#   flg = longer forward
#   bak = short backward
#   lft = short left turn
#   rgt = short right turn
#   stp = stop
#   dst = report distance
#   aln = scan left/center/right and turn toward nearest object
#   swp = run sweeper briefly
#   s18 = spin 180 degrees
#   s36 = spin 360 degrees
#   sch = search one full spin and face nearest object
#   sas = search, approach, sweep, and dead-reckon home
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
# Port F = Technic Large Angular Motor for sweeper
left_motor = Motor(Port.C, Direction.COUNTERCLOCKWISE)
right_motor = Motor(Port.D)
eyes = UltrasonicSensor(Port.E)
sweep_motor = Motor(Port.F)

SWEEP_SPEED = -350
SWEEP_MS = 500
ALIGN_ANGLE = 20
ALIGN_NO_OBJECT_MM = 1900
SEARCH_STEP_DEGREES = 30
SEARCH_SWEEP_MAX_STEPS = 15
SEARCH_SWEEP_DETECT_MM = 300
SEARCH_SWEEP_SWEEP_MM = 80
SEARCH_SWEEP_ALIGN_STOP_MM = 200

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


def stable_dist_mm():
    best = 2000
    for _ in range(3):
        d = dist_mm()
        if d < best:
            best = d
        wait(40)
    return best


def stop():
    robot.stop()
    sweep_motor.stop()


def start_sweeper():
    sweep_motor.run(SWEEP_SPEED)


def stop_sweeper():
    sweep_motor.stop()


def sweep(report=True):
    start_sweeper()
    wait(SWEEP_MS)
    stop_sweeper()
    if report:
        send("OK:SWP")


def scan_and_align(report=True):
    """
    Simple alignment:
    1. Read distance straight ahead.
    2. Turn left and read.
    3. Turn right and read.
    4. Face the direction with the closest object.
    """

    center = stable_dist_mm()

    robot.turn(-ALIGN_ANGLE)
    wait(100)
    left = stable_dist_mm()

    robot.turn(ALIGN_ANGLE * 2)
    wait(100)
    right = stable_dist_mm()

    # Robot is now facing +ALIGN_ANGLE degrees from original center.
    readings = [
        ("left", left),
        ("center", center),
        ("right", right),
    ]

    best_name, best_val = min(readings, key=lambda x: x[1])
    scan_report = "L%s:C%s:R%s" % (left, center, right)

    # If nothing was seen, return to center and report no object.
    if best_val >= ALIGN_NO_OBJECT_MM:
        robot.turn(-ALIGN_ANGLE)
        if report:
            send("OK:ALN:NO_OBJECT:%s" % scan_report)
        return False, best_name, best_val

    if best_name == "left":
        # Current heading is +ALIGN_ANGLE. Left target was -ALIGN_ANGLE.
        robot.turn(-(ALIGN_ANGLE * 2))

    elif best_name == "center":
        # Current heading is +ALIGN_ANGLE. Center target was 0.
        robot.turn(-ALIGN_ANGLE)

    else:
        # Already facing the right target.
        pass

    if report:
        send("OK:ALN:%s:%s:%s" % (best_name, best_val, scan_report))
    return True, best_name, best_val


def search(report=True):
    steps = 360 // SEARCH_STEP_DEGREES
    best_step = 0
    best_dist = 2000

    for step in range(steps):
        d = stable_dist_mm()
        if d < best_dist:
            best_dist = d
            best_step = step

        robot.turn(SEARCH_STEP_DEGREES)

    if best_dist >= ALIGN_NO_OBJECT_MM:
        if report:
            send("OK:SCH:NO_OBJECT:%s" % best_dist)
        return False, 0, best_dist

    best_angle = best_step * SEARCH_STEP_DEGREES
    robot.turn(best_angle)
    if report:
        send("OK:SCH:%s:%s" % (best_angle, best_dist))
    return True, best_angle, best_dist


def search_and_sweep(max_steps=SEARCH_SWEEP_MAX_STEPS):
    steps_taken = 0

    while steps_taken < max_steps:
        robot.straight(300)
        steps_taken += 1

        found, _direction, distance = scan_and_align(report=False)

        if found and distance <= SEARCH_SWEEP_DETECT_MM:
            approach_steps = 0
            while distance > SEARCH_SWEEP_ALIGN_STOP_MM and approach_steps < max_steps:
                robot.straight(120)
                approach_steps += 1
                found, _direction, distance = scan_and_align(report=False)
                if not found:
                    break

            robot.straight(300)
            sweep(report=False)

            robot.turn(180)
            for _ in range(steps_taken):
                robot.straight(300)

            robot.turn(360)
            send("OK:SAS:COMPLETE:%s:%s" % (steps_taken, distance))
            return

    send("OK:SAS:FAILED:%s" % steps_taken)


def run_command(cmd):
    if cmd == b"fwd":
        robot.straight(120)
        send("OK:FWD")

    elif cmd == b"flg":
        robot.straight(300)
        send("OK:FLG")

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

    elif cmd == b"swp":
        sweep()

    elif cmd == b"s18":
        robot.turn(180)
        send("OK:S18")

    elif cmd == b"s36":
        robot.turn(360)
        send("OK:S36")

    elif cmd == b"sch":
        search()

    elif cmd == b"sas":
        search_and_sweep()

    else:
        stop()
        send("ERR:UNKNOWN:%s" % cmd.decode(errors="replace"))


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
