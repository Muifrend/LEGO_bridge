# bridge_server.py
# Laptop bridge:
#   HTTP API /robot/command -> BLE command -> LEGO SPIKE Prime hub
#
# Run mock mode first:
#   python bridge_server.py --mock
#
# Run real BLE mode:
#   python bridge_server.py --hub-name "Pybricks Hub"
#
# Then in another terminal:
#   curl -X POST http://localhost:8000/robot/command \
#     -H "Content-Type: application/json" \
#     -d '{"command":"ALIGN_AND_PUSH"}'

import argparse
import asyncio
import time
from contextlib import suppress
from typing import Optional, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

try:
    from bleak import BleakClient, BleakScanner
except Exception:
    BleakClient = None
    BleakScanner = None


# Pybricks Command/Event Characteristic.
# We use it to write stdin events to the hub and read stdout events back.
PYBRICKS_COMMAND_EVENT_CHAR_UUID = "c5f50002-8280-46da-89f4-6d8051e4aeef"

COMMAND_MAP: Dict[str, bytes] = {
    "FORWARD": b"fwd",
    "FORWARD_LONG": b"flg",
    "BACKUP": b"bak",
    "LEFT": b"lft",
    "RIGHT": b"rgt",
    "STOP": b"stp",
    "DISTANCE": b"dst",
    "ALIGN": b"aln",
    "SWEEP": b"swp",
    "SPIN_180": b"s18",
    "SPIN_360": b"s36",
    "SEARCH": b"sch",
    "SEARCH_AND_SWEEP": b"sas",
    "BYE": b"bye",
}


class RobotCommand(BaseModel):
    command: str
    mission_id: Optional[str] = None


class HubBridge:
    def __init__(self, hub_name: str, mock: bool = False):
        self.hub_name = hub_name
        self.mock = mock
        self.client: Optional[BleakClient] = None
        self.ready_event = asyncio.Event()
        self.last_message = ""
        self.connected = False
        self.lock = asyncio.Lock()

    async def connect(self):
        if self.mock:
            self.connected = True
            print("[mock] Bridge ready. No LEGO required.")
            return

        if BleakClient is None or BleakScanner is None:
            raise RuntimeError("bleak is not installed. Run: pip install bleak")

        print(f"Scanning for hub named: {self.hub_name}")
        device = await BleakScanner.find_device_by_name(self.hub_name, timeout=15.0)
        if device is None:
            raise RuntimeError(
                f"Could not find hub named '{self.hub_name}'. "
                "Make sure the hub is on, Pybricks firmware is installed, "
                "and Pybricks Code is disconnected."
            )

        def handle_disconnect(_client):
            self.connected = False
            print("Hub disconnected.")

        self.client = BleakClient(device, disconnected_callback=handle_disconnect)
        await self.client.connect()
        await self.client.start_notify(PYBRICKS_COMMAND_EVENT_CHAR_UUID, self._handle_rx)
        self.connected = True

        print("Connected to hub.")
        print("Now press the center button on the SPIKE hub to start hub_robot.py.")
        print("Waiting for hub to send 'rdy'...")

        try:
            await asyncio.wait_for(self.ready_event.wait(), timeout=45)
            print("Hub program is ready.")
        except asyncio.TimeoutError:
            print(
                "Still did not receive 'rdy'. The hub may not have started the saved program. "
                "Press the hub center button, or reload hub_robot.py in Pybricks Code."
            )

    def _handle_rx(self, _sender, data: bytearray):
        # Pybricks stdout event: first byte 0x01, payload after that.
        if not data:
            return
        if data[0] == 0x01:
            payload = bytes(data[1:])

            if b"rdy" in payload:
                before_ready, _after_ready = payload.split(b"rdy", 1)
                if before_ready:
                    self.last_message = before_ready.decode(errors="replace")
                    print(f"[hub] {self.last_message}")
                self.ready_event.set()
                return

            text = payload.decode(errors="replace")
            self.last_message = text
            print(f"[hub] {text}")

    async def send_raw(self, code: bytes) -> str:
        if self.mock:
            await asyncio.sleep(0.2)
            self.last_message = f"MOCK_OK:{code.decode()}"
            return self.last_message

        if not self.connected or self.client is None:
            raise RuntimeError("Hub is not connected.")

        async with self.lock:
            await asyncio.wait_for(self.ready_event.wait(), timeout=15)
            self.ready_event.clear()
            await self.client.write_gatt_char(
                PYBRICKS_COMMAND_EVENT_CHAR_UUID,
                b"\x06" + code,  # 0x06 = write stdin
                response=True,
            )

            # Wait briefly for status. The next 'rdy' arrives after command completes.
            try:
                await asyncio.wait_for(self.ready_event.wait(), timeout=20)
            except asyncio.TimeoutError:
                raise RuntimeError("Timed out waiting for hub to finish command.")

            return self.last_message or "OK"

    async def command(self, command_name: str) -> dict:
        command_name = command_name.upper().strip()
        if command_name not in COMMAND_MAP:
            raise ValueError(f"Unknown command: {command_name}")

        code = COMMAND_MAP[command_name]
        result = await self.send_raw(code)
        return {"ok": True, "command": command_name, "hub_response": result}


def build_app(bridge: HubBridge) -> FastAPI:
    app = FastAPI(title="Poop Patrol LEGO Bridge", version="0.1.0")

    @app.on_event("startup")
    async def startup():
        await bridge.connect()

    @app.get("/health")
    async def health():
        return {
            "ok": True,
            "connected": bridge.connected,
            "mock": bridge.mock,
            "last_hub_message": bridge.last_message,
        }

    @app.post("/robot/command")
    async def robot_command(payload: RobotCommand):
        try:
            result = await bridge.command(payload.command)
            result["mission_id"] = payload.mission_id
            return result
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hub-name", default="Pybricks Hub")
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    bridge = HubBridge(hub_name=args.hub_name, mock=args.mock)
    app = build_app(bridge)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
