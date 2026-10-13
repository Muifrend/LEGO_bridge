# Trash Patrol — LEGO Robot Bridge

**HTTP-to-Bluetooth control for a LEGO SPIKE Prime cleanup robot.**

Part of **[Trash Patrol — World Cup Edition](https://github.com/Muifrend/Trash_Patrol)**, the first-place Google I/O Kickoff: Pre-World Cup Hack project. [Project overview and developer contribution](https://github.com/Muifrend/Trash_Patrol#my-contribution-and-team) · [Recorded demo](https://www.youtube.com/shorts/33VFazESk8A) · [Published results](https://www.gmicloud.ai/en/blog/what-32-teams-built-for-the-world-cup-in-one-day)

A FastAPI service on the laptop receives robot commands and sends three-byte messages over Bluetooth Low Energy to a SPIKE Prime hub running Pybricks. The hub controls the drive motors, ultrasonic sensing, and sweeper.

## Components

| Component | Repository |
| --- | --- |
| Project overview and Android app | [Trash_Patrol](https://github.com/Muifrend/Trash_Patrol) |
| Mission backend and RocketRide dispatch | [rocketride](https://github.com/Muifrend/rocketride) |
| Laptop bridge and robot program | **This repository** |

## Files

| File | Purpose |
| --- | --- |
| [bridge_server.py](bridge_server.py) | Laptop HTTP server and Bluetooth connection |
| [hub_robot.py](hub_robot.py) | Pybricks program loaded onto the SPIKE Prime hub |
| [test.py](test.py) | Hub-side port discovery script; not a laptop test suite |
| [requirements.txt](requirements.txt) | Laptop Python dependencies |

## Hardware and wiring

The current [hub program](hub_robot.py) uses:

| Device | Port |
| --- | --- |
| Left drive motor | C |
| Right drive motor | D |
| Ultrasonic distance sensor | E |
| Sweeper motor | F |

Change the hub program if your build uses different ports. Wheel diameter, axle track, speed, and sensing thresholds are also configured in `hub_robot.py`.

## Setup

### 1. Prepare the hub

1. Open [Pybricks Code](https://code.pybricks.com/).
2. Use **Tools → Install Pybricks firmware** for the SPIKE Prime / Prime Hub.
3. Create a program containing [hub_robot.py](hub_robot.py), download it to the hub, then stop it.
4. Disconnect Pybricks Code from the hub before starting the laptop bridge.

The laptop bridge needs the Bluetooth connection; it cannot share it with Pybricks Code.

### 2. Check HTTP commands without hardware

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python bridge_server.py --mock
```

In another terminal:

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/robot/command \
  -H "Content-Type: application/json" \
  -d '{"command":"SEARCH_AND_SWEEP","mission_id":"demo-001"}'
```

Mock mode responds with `MOCK_OK:sas`. It checks the HTTP-to-command mapping but does not simulate sensing or a completed cleanup.

### 3. Connect the physical robot

```bash
python bridge_server.py --hub-name "Pybricks Hub"
```

After the laptop connects, press the hub's center button to start the saved program. The bridge waits for the hub's `rdy` message.

Start with a distance query:

```bash
curl -X POST http://localhost:8000/robot/command \
  -H "Content-Type: application/json" \
  -d '{"command":"DISTANCE"}'
```

Use a clear, controlled space when testing movement commands.

## HTTP interface

### `GET /health`

Reports connection state, mock mode, and the last hub message.

### `POST /robot/command`

```json
{
  "command": "SEARCH_AND_SWEEP",
  "mission_id": "cleanup-123"
}
```

The response contains `ok`, `command`, `hub_response`, and `mission_id`. The backend interprets hub messages such as `OK:SAS:COMPLETE:1:42` or `OK:SAS:FAILED:15`.

The request model accepts `command` and an optional `mission_id`. The backend's extra `max_steps` field is not forwarded to the hub; the current robot program uses `SEARCH_SWEEP_MAX_STEPS = 15`.

## Command reference

| HTTP command | Hub code | Action |
| --- | --- | --- |
| `FORWARD` | `fwd` | Move forward 120 mm |
| `FORWARD_LONG` | `flg` | Move forward 300 mm |
| `BACKUP` | `bak` | Move backward 120 mm |
| `LEFT` | `lft` | Turn left 25° |
| `RIGHT` | `rgt` | Turn right 25° |
| `STOP` | `stp` | Stop drive and sweeper |
| `DISTANCE` | `dst` | Report ultrasonic distance |
| `ALIGN` | `aln` | Scan left/center/right and face the closest detected object |
| `SWEEP` | `swp` | Run the sweeper briefly |
| `SPIN_180` | `s18` | Turn 180° |
| `SPIN_360` | `s36` | Turn 360° |
| `SEARCH` | `sch` | Scan a full rotation and face the closest detected object |
| `SEARCH_AND_SWEEP` | `sas` | Run the hub's search, approach, sweep, and return routine |
| `BYE` | `bye` | Stop and exit the hub program |

## Backend integration

Set the backend's `ROCKETRIDE_BRIDGE_COMMAND_URL` to this laptop's reachable `/robot/command` URL. If RocketRide runs elsewhere, provide a route to the laptop, such as an active tunnel.

## Prototype limits

- The robot uses ultrasonic sensing and relative movements rather than mapping or GPS navigation. The return routine is approximate.
- The bridge waits up to 20 seconds for command completion. A longer robot routine can exceed that wait.
- The bridge returns results synchronously; this implementation does not send a later `/bridge/callback`.
- The service has no application-level authentication and was built for a local hackathon demonstration.
