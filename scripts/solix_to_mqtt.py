#!/usr/bin/env python3
"""Anker Solix C300X (A1723): Werte per mosquitto_pub an den MQTT-Broker senden.
Publishes all values of the Anker Solix C300X (A1723) to an MQTT broker.

Aufruf / Usage:
  python3 solix_to_mqtt.py                   Testlauf, zeigt nur an / dry run, prints only
  python3 solix_to_mqtt.py --send            einmal senden (z. B. fuer cron) / send once (cron)
  python3 solix_to_mqtt.py --send --loop 60  dauerhaft alle 60 s / keep running, every 60 s

Diese Datei MUSS im Ordner der Bibliothek anker-solix-api liegen.
This file MUST live inside the cloned anker-solix-api folder.
"""
import argparse
import asyncio
import re
import subprocess

from aiohttp import ClientSession

import common
from anker_solix_api.api import AnkerSolixApi

DEVICE_SN = "DEINE_SERIENNUMMER"  # <- anpassen / change me
MQTT_BROKER = "127.0.0.1"  # <- IP des MQTT-Brokers (ioBroker mqtt-Server) / broker IP
MQTT_PORT = 1883
BASE_TOPIC = "mqtt.0.info.Anker.c300x"  # Punkte-Schreibweise wie beim ioBroker-MQTT-Server
SKIP_KEYS = {"topics"}
FIRST_WAIT = 15
NEXT_WAIT = 5


def ignore_message(session, topic, message, data, model, *args, **kwargs):
    """Callback ohne Ausgabe, die Werte holen wir aus mqtt_data."""
    return None


def clean_key(key: str) -> str:
    """Macht aus dem Namen ein gueltiges Topic-Stueck (z. B. ohne Fragezeichen)."""
    return re.sub(r"[^A-Za-z0-9_]", "", key)


def to_text(value):
    """Wandelt einfache Werte in Text, alles andere wird nicht gesendet."""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float, str)):
        return str(value)
    return None


def send_mqtt(topic: str, value: str) -> bool:
    """Sendet einen Wert per mosquitto_pub, gibt Fehler aus."""
    try:
        result = subprocess.run(
            [
                "mosquitto_pub",
                "-h", MQTT_BROKER,
                "-p", str(MQTT_PORT),
                "-t", topic,
                "-m", value,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        print("FEHLER: mosquitto_pub nicht gefunden (sudo apt install mosquitto-clients)")
        return False
    except subprocess.TimeoutExpired:
        print(f"FEHLER: Zeitueberschreitung beim Senden an {MQTT_BROKER}")
        return False
    if result.returncode != 0:
        print(f"FEHLER beim Senden von {topic}: {result.stderr.strip()}")
        return False
    return True


async def read_values(api, session, dev, wait: int) -> dict:
    session.status_request(deviceDict=dev, wait_for_publish=2)
    await asyncio.sleep(wait)
    return api.mqttsession.mqtt_data.get(DEVICE_SN) or {}


def handle(values: dict, send: bool) -> None:
    ok = 0
    failed = 0
    for key, raw in values.items():
        if key in SKIP_KEYS:
            continue
        text = to_text(raw)
        name = clean_key(key)
        if text is None or not name:
            continue
        if send:
            if send_mqtt(f"{BASE_TOPIC}.{name}", text):
                ok += 1
            else:
                failed += 1
                if failed >= 3:
                    print("Mehrere Fehler, breche das Senden fuer diesen Lauf ab")
                    break
        else:
            print(f"  {BASE_TOPIC}.{name} = {text}")
            ok += 1
    if send:
        print(f"An {MQTT_BROKER} gesendet: {ok} Werte, Fehler: {failed}")
    else:
        print(f"Testlauf, wuerde senden: {ok} Werte")


async def main(send: bool, loop_seconds: int) -> int:
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
        dev = api.devices.get(DEVICE_SN)
        if not dev:
            print("FEHLER: Geraet nicht in der Geraeteliste gefunden")
            return 1
        session = await api.startMqttSession()
        if not (session and session.is_connected()):
            print("FEHLER: MQTT-Verbindung fehlgeschlagen")
            return 1
        poller = None
        try:
            topics = set()
            if prefix := session.get_topic_prefix(deviceDict=dev):
                topics.add(f"{prefix}#")
            poller = asyncio.create_task(
                session.message_poller(
                    topics=topics,
                    trigger_devices={DEVICE_SN},
                    msg_callback=ignore_message,
                    timeout=60,
                )
            )
            await asyncio.sleep(2)
            wait = FIRST_WAIT
            while True:
                values = await read_values(api, session, dev, wait)
                if values:
                    handle(values, send)
                else:
                    print("Keine Werte empfangen")
                if not loop_seconds:
                    return 0
                if not session.is_connected():
                    print("FEHLER: Verbindung verloren, Skript beendet")
                    return 1
                wait = NEXT_WAIT
                await asyncio.sleep(max(loop_seconds - wait, 1))
        finally:
            if poller:
                poller.cancel()
            api.mqttsession.cleanup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--send", action="store_true", help="Werte wirklich senden / really send")
    parser.add_argument("--loop", type=int, default=0, help="Intervall in Sekunden / interval in seconds")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.send, args.loop)))
