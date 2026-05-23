# Poop Patrol LEGO Bridge Starter

This is the minimal bridge for the hackathon demo.

## What this does

Android / RocketRide / GMI can call:

```http
POST http://<laptop-ip>:8000/robot/command
Content-Type: application/json

{"command":"ALIGN_AND_PUSH","mission_id":"demo-001"}
```

The laptop bridge sends a 3-byte command to the LEGO SPIKE Prime hub running Pybricks.

## Files

- `hub_robot.py` — load this onto the SPIKE Prime hub with Pybricks Code.
- `bridge_server.py` — run this on the laptop.
- `requirements.txt` — Python dependencies.

## Assumed LEGO ports

- Left motor: C
- Right motor: D
- Distance sensor: A

Change the ports in `hub_robot.py` if your build differs.

## Step 1 — Install Pybricks firmware

1. Open https://code.pybricks.com in Chrome/Edge.
2. Tools menu → Install Pybricks firmware.
3. Select SPIKE Prime / Prime Hub.
4. Follow the instructions.

You can restore official LEGO firmware later from the same Tools menu.

## Step 2 — Load hub program

1. In Pybricks Code, create a new program.
2. Paste `hub_robot.py`.
3. Connect to hub.
4. Download/run it once.
5. Stop it.
6. Disconnect Pybricks Code from the hub.

Important: the laptop bridge cannot find the hub while Pybricks Code is still connected.

## Step 3 — Start laptop bridge in mock mode first

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python bridge_server.py --mock
```

Test:

```bash
curl -X POST http://localhost:8000/robot/command \
  -H "Content-Type: application/json" \
  -d '{"command":"ALIGN_AND_PUSH","mission_id":"demo-001"}'
```

## Step 4 — Start laptop bridge with real LEGO

```bash
python bridge_server.py --hub-name "Pybricks Hub"
```

When the terminal says it is connected, press the center button on the SPIKE hub to start the saved program.

Test commands:

```bash
curl -X POST http://localhost:8000/robot/command \
  -H "Content-Type: application/json" \
  -d '{"command":"DISTANCE"}'

curl -X POST http://localhost:8000/robot/command \
  -H "Content-Type: application/json" \
  -d '{"command":"FORWARD"}'

curl -X POST http://localhost:8000/robot/command \
  -H "Content-Type: application/json" \
  -d '{"command":"ALIGN_AND_PUSH"}'
```

## Commands

- `FORWARD`
- `BACKUP`
- `LEFT`
- `RIGHT`
- `STOP`
- `DISTANCE`
- `ALIGN`
- `PUSH`
- `ALIGN_AND_PUSH`
- `BYE`

## RocketRide integration

Have RocketRide call:

```http
POST http://<laptop-ip>:8000/robot/command
```

with:

```json
{
  "mission_id": "cleanup-123",
  "command": "ALIGN_AND_PUSH"
}
```

For a cloud-hosted RocketRide workflow, the easiest demo option is to run a tunnel to your laptop bridge, or have the laptop poll RocketRide for the next command.
