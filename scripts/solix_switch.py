#!/usr/bin/env python3
"""Schaltet Ausgaenge und Licht der Anker Solix C300X (A1723) per MQTT.
Switches outputs and light of the Anker Solix C300X (A1723) via MQTT.

Aufruf / Usage:
  python3 solix_switch.py ac on|off
  python3 solix_switch.py dc on|off
  python3 solix_switch.py light off|low|medium|high|blinking

Diese Datei MUSS im Ordner der Bibliothek anker-solix-api liegen
(sie nutzt deren common.py fuer die Zugangsdaten aus der .env).
This file MUST live inside the cloned anker-solix-api folder
(it uses the library's common.py to read the credentials from .env).
"""
import asyncio
import sys

from aiohttp import ClientSession

import common
from anker_solix_api.api import AnkerSolixApi
from anker_solix_api.mqtt_factory import SolixMqttDeviceFactory

DEVICE_SN = "DEINE_SERIENNUMMER"  # <- anpassen / change me
ONOFF = {"on": 1, "off": 0}
COMMANDS = {
    "ac": ("ac_output_switch", "set_ac_output_switch", ONOFF),
    "dc": ("dc_output_switch", "set_dc_output_switch", ONOFF),
    "light": (
        "light_mode_select",
        "set_light_mode",
        {"off": 0, "low": 1, "medium": 2, "high": 3, "blinking": 4},
    ),
}


async def main(which: str, option: str) -> int:
    cmd, param, options = COMMANDS[which]
    value = options[option]
    async with ClientSession() as websession:
        api = AnkerSolixApi(
            common.user(),
            common.password(),
            common.country(),
            websession,
            common.CONSOLE,
        )
        await api.async_authenticate()
        await api.update_sites()
        await api.get_bind_devices()
        session = await api.startMqttSession()
        if not (session and session.is_connected()):
            print("FEHLER: MQTT-Verbindung fehlgeschlagen")
            return 1
        try:
            mdev = SolixMqttDeviceFactory(api, DEVICE_SN).create_device()
            if not mdev:
                print("FEHLER: Geraet nicht gefunden")
                return 1
            response = await mdev.run_command(cmd=cmd, parm_map={param: value})
            if isinstance(response, dict):
                print(f"OK: {cmd} = {option}")
                return 0
            print(f"FEHLER: Befehl nicht gesendet ({response})")
            return 1
        finally:
            api.mqttsession.cleanup()


if __name__ == "__main__":
    ok = (
        len(sys.argv) == 3
        and sys.argv[1] in COMMANDS
        and sys.argv[2] in COMMANDS[sys.argv[1]][2]
    )
    if not ok:
        print("Aufruf: python3 solix_switch.py ac|dc on|off  oder  light off|low|medium|high|blinking")
        sys.exit(2)
    sys.exit(asyncio.run(main(sys.argv[1], sys.argv[2])))
