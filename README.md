# 🔋 Anker SOLIX C300X ↔ ioBroker


<details open>
<summary><b>🇬🇧 English</b> &nbsp;(click to expand/collapse)</summary>

## What is this?

The **Anker SOLIX C300X** (model **A1723**, the version with AC outlets) is a great power station. But ioBroker didn't want to talk to it properly at first. The adapter only showed the state of charge, and switching gave `Unsupported control`.

This project makes them talk anyway – **without an ioBroker adapter**, using Python, JavaScript, cron and a Raspberry Pi.

## What can it do?

- 📊 **All readings** (state of charge, temperature, power per port, remaining time, switch states …) pushed to ioBroker every 10 minutes, about 40 datapoints
- 🔌 **AC output** on/off from ioBroker
- 🚬 **12 V output** (car socket) on/off
- 💡 **Light**: off / low / medium / high / blinking
- ⚡ Switching takes about **2 seconds**

**Tested with:** Anker SOLIX C300X (A1723, firmware 1.2.5.7), Raspberry Pi with Raspberry Pi OS, ioBroker with the MQTT adapter in server mode, JavaScript adapter.

## How it works

```
 Reading values (every 10 minutes)
 cron ─► solix_to_mqtt.py ─► Anker cloud ─► C300X
                │
                └─► mosquitto_pub ─► ioBroker (mqtt.0.info.Anker.c300x.*)

 Switching
 ioBroker datapoint ─► JavaScript (exec) ─► sudo -u pi ─► solix_switch.py ─► Anker cloud ─► C300X
```

The real magic is done by **[anker-solix-api](https://github.com/thomluther/anker-solix-api)** by thomluther. It talks to the Anker cloud and knows the A1723 commands. We just wrap some everyday Pi plumbing around it.

## Requirements

- Raspberry Pi (or another Linux machine) with Python 3, `git`, `mosquitto-clients` (`sudo apt install mosquitto-clients`)
- ioBroker with the **MQTT adapter (server mode)** and the **JavaScript adapter**
- An Anker account in which the C300X is set up
- The serial number of your C300X (shown in the Anker app under device info)

## Installation – step by step

### 1. Get the library

```bash
cd ~
git clone https://github.com/thomluther/anker-solix-api.git
cd anker-solix-api
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

> 💡 There is **no** `requirements.txt` – the library is a proper package, `pip install .` pulls in everything it needs.

### 2. Store your credentials (`.env`)

```bash
cp /path/to/this/project/scripts/.env.example .env
nano .env          # enter e-mail, password, country
chmod 600 .env     # only you may read it
```

The file must live in the `anker-solix-api` folder (that's where `common.py` is, which loads it). **Never put the `.env` on GitHub.** Really. Please. 🙏

### 3. Check that the library knows your device

```bash
python3 mqtt_monitor.py -dev YOUR_SERIAL_NUMBER -rt -sr -r 5
```

After a few seconds values appear. Press **`c`** to see the list of commands your device supports (e.g. `ac_output_switch`, `dc_output_switch`, `light_mode_select`). If they are missing, the library is too old: `git pull` and `pip install .` again.

> Handy: with this monitor tool you can safely try out commands for other devices first.

### 4. Copy the scripts into the library folder

```bash
cp /path/to/this/project/scripts/solix_switch.py .
cp /path/to/this/project/scripts/solix_to_mqtt.py .
nano solix_switch.py solix_to_mqtt.py     # adjust DEVICE_SN (and MQTT_BROKER)
```

The scripts must live **in the same folder** as `common.py`, because they use its credential helpers. In `solix_to_mqtt.py`, `MQTT_BROKER` is the IP of the ioBroker MQTT server (port 1883, no username/password).

### 5. Test and send the values

```bash
python3 solix_to_mqtt.py            # dry run: prints only, sends nothing
python3 solix_to_mqtt.py --send     # really send to ioBroker
```

Datapoints should then appear under `mqtt.0.info.Anker.c300x` (`temperature`, `battery_soc`, …). For us it took a little while after the first send until they showed up – be patient.

### 6. Set up cron (every 10 minutes)

`crontab -e` and add this line (adjust the path):

```
*/10 * * * * cd /home/pi/anker-solix-api && .venv/bin/python solix_to_mqtt.py --send > /tmp/solix_cron.log 2>&1
```

Why the long path? Cron doesn't know your Python environment. Calling `.venv/bin/python` directly runs the right Python – no "activate" needed. The log goes to `/tmp` (RAM), which spares the SD card.

### 7. Test switching

```bash
python3 solix_switch.py dc off      # 12 V output off
python3 solix_switch.py dc on       # 12 V output on
python3 solix_switch.py ac on|off   # AC output
python3 solix_switch.py light off|low|medium|high|blinking
```

`OK: …` means it worked. ⚠️ The AC output cuts power to everything plugged into it.

### 8. Let ioBroker switch (sudo rule)

ioBroker usually runs as user `iobroker`, but your `.env` belongs to you (`pi`). So that the script can find it, ioBroker starts it via `sudo -u pi`. The rule allows **only these nine fixed commands**, nothing else:

```bash
bash sudoers/install_sudoers.sh     # adjust paths/users at the top of the script
```

### 9. ioBroker scripts

Create two scripts in the JavaScript adapter:

1. `iobroker/01_create_datapoints.js` – run **once**, then stop it. Creates `0_userdata.0.Anker.c300x_12V_Ausgang`, `…_AC_Ausgang` and `…_Licht`.
2. `iobroker/02_switch_handler.js` – keep it **running** (adjust the paths at the top).

Done: toggle a datapoint → about 2 seconds later the power station switches. You can use the datapoints in Blockly, VIS or Grafana as well.

## Pitfalls (so you don't fall into the same holes)

- **`pip install -r requirements.txt` doesn't work** – there is none. → `pip install .`
- **The scripts belong in the library folder**, otherwise Python can't find `common`.
- **Cron + venv:** always use the full path `.venv/bin/python`.
- **`.env` with special characters:** put passwords containing `#` or spaces in single quotes.
- **ioBroker runs as a different user.** Without the sudo rule the script asks for e-mail and password – and ioBroker can't answer that.
- **`createState` in the object notation** (as in `01_create_datapoints.js`) worked for us. A variant with an extra initial-value parameter failed already while the script was being prepared (cause not clearly identified).
- **The detour "ioBroker → MQTT → listener on the Pi" did not work for us:** the commands never reached the listener (cause unknown, probably ioBroker's MQTT server behaves differently from a plain broker). Hence `exec` + `sudo`.
- **`battery_soh` always showed the same value as `battery_soc` for us.** Don't rely on it as battery health.
- **The Anker app apparently switches via a path the monitor tool doesn't see.** So test commands with the menu (`c`) rather than trying to sniff them.
- **Cron readings are only as fresh as the interval** (10 minutes here). Switching, however, takes only about 2 seconds.

## Security

- 🔐 Never commit `.env` (a `.gitignore` is included) and protect it with `chmod 600`.
- 🔐 The sudo rule allows only the nine fixed calls. Review it before installing.
- ⚠️ Don't hang anything vital (fridge, medical equipment) on an output that scripts can switch without a fallback.
- ⚠️ This uses the **unofficial** Anker cloud interface. Anker can change it at any time. Use at your own risk.

## Credits & disclaimer

- All the cloud/MQTT heavy lifting is done by **[anker-solix-api](https://github.com/thomluther/anker-solix-api)** by thomluther (which also powers the Home Assistant integration). This project wouldn't exist without it. Please respect its license.
- The ioBroker adapter [`ioBroker.anker-solix`](https://github.com/MatthiasUlrich1/ioBroker.anker-solix) by Matthias Ulrich is a separate project. At the time of our test it could only read the state of charge on the A1723; we filed a feature request there.
- This project is not affiliated with Anker. No warranty, no liability (see `LICENSE`).

Have fun – and may your battery always have enough juice! ⚡

</details>

<details>
<summary><b>🇩🇪 Deutsch</b> &nbsp;(zum Auf- und Zuklappen anklicken)</summary>

## Worum geht's?

Die **Anker SOLIX C300X** (Modell **A1723**, die Variante mit Steckdosen) ist eine feine Powerstation. Nur: ioBroker wollte anfangs nicht so recht mit ihr reden. Der Adapter zeigte nur den Ladestand, und beim Schalten kam `Unsupported control`.

Dieses Projekt bringt die beiden trotzdem zusammen – **ohne ioBroker-Adapter**, nur mit Python, JavaScript, Cron und einem Raspberry Pi.

## Was kann das?

- 📊 **Alle Messwerte** (Ladestand, Temperatur, Leistung je Anschluss, Restlaufzeit, Schalterstände …) alle 10 Minuten nach ioBroker, rund 40 Datenpunkte
- 🔌 **AC-Ausgang** ein/aus aus ioBroker
- 🚬 **12-V-Ausgang** (Zigarettenanzünder) ein/aus
- 💡 **Licht**: Aus / Niedrig / Mittel / Hoch / Blinken
- ⚡ Reaktionszeit beim Schalten: etwa **2 Sekunden**

**Getestet mit:** Anker SOLIX C300X (A1723, Firmware 1.2.5.7), Raspberry Pi mit Raspberry Pi OS, ioBroker mit MQTT-Adapter im Server-Modus, JavaScript-Adapter.

## So funktioniert's

```
 Messwerte lesen (alle 10 Minuten)
 cron ─► solix_to_mqtt.py ─► Anker-Cloud ─► C300X
                │
                └─► mosquitto_pub ─► ioBroker (mqtt.0.info.Anker.c300x.*)

 Schalten
 ioBroker-Datenpunkt ─► JavaScript (exec) ─► sudo -u pi ─► solix_switch.py ─► Anker-Cloud ─► C300X
```

Die eigentliche Kunst steckt in der Bibliothek **[anker-solix-api](https://github.com/thomluther/anker-solix-api)** von thomluther. Sie spricht mit der Anker-Cloud und kennt die Befehle des A1723. Wir kleben nur ein bisschen Pi-Alltag drumherum.

## Voraussetzungen

- Raspberry Pi (oder anderer Linux-Rechner) mit Python 3, `git`, `mosquitto-clients` (`sudo apt install mosquitto-clients`)
- ioBroker mit **MQTT-Adapter (Server-Modus)** und **JavaScript-Adapter**
- Ein Anker-Konto, in dem die C300X eingerichtet ist
- Die Seriennummer deiner C300X (steht in der Anker-App unter den Geräteinfos)

## Installation – Schritt für Schritt

### 1. Bibliothek holen

```bash
cd ~
git clone https://github.com/thomluther/anker-solix-api.git
cd anker-solix-api
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

> 💡 Es gibt **keine** `requirements.txt` – die Bibliothek ist ein richtiges Paket, `pip install .` zieht alles Nötige mit.

### 2. Zugangsdaten hinterlegen (`.env`)

```bash
cp /pfad/zu/diesem/projekt/scripts/.env.example .env
nano .env          # E-Mail, Passwort, Land eintragen
chmod 600 .env     # nur du darfst sie lesen
```

Die Datei muss im Ordner `anker-solix-api` liegen (dort liegt auch `common.py`, das sie lädt). **Die `.env` kommt niemals auf GitHub.** Wirklich nicht. Bitte. 🙏

### 3. Prüfen, ob die Bibliothek dein Gerät kennt

```bash
python3 mqtt_monitor.py -dev DEINE_SERIENNUMMER -rt -sr -r 5
```

Nach ein paar Sekunden erscheinen Werte. Drückst du **`c`**, siehst du eine Liste der Befehle, die dein Gerät kennt (z. B. `ac_output_switch`, `dc_output_switch`, `light_mode_select`). Fehlen sie, ist die Bibliothek zu alt: `git pull` und noch einmal `pip install .`.

> Praktisch: Mit diesem Monitor-Tool kannst du Befehle für andere Geräte erst einmal gefahrlos ausprobieren.

### 4. Skripte in den Bibliotheks-Ordner kopieren

```bash
cp /pfad/zu/diesem/projekt/scripts/solix_switch.py .
cp /pfad/zu/diesem/projekt/scripts/solix_to_mqtt.py .
nano solix_switch.py solix_to_mqtt.py     # DEVICE_SN (und MQTT_BROKER) anpassen
```

Die Skripte müssen **im selben Ordner** wie `common.py` liegen, weil sie dessen Zugangsdaten-Funktionen nutzen. In `solix_to_mqtt.py` ist `MQTT_BROKER` die IP des ioBroker-MQTT-Servers (Port 1883, ohne Benutzer/Passwort).

### 5. Werte testen und senden

```bash
python3 solix_to_mqtt.py            # Testlauf: zeigt nur an, sendet nichts
python3 solix_to_mqtt.py --send     # wirklich an ioBroker senden
```

Danach sollten unter `mqtt.0.info.Anker.c300x` Datenpunkte erscheinen (`temperature`, `battery_soc`, …). Bei uns hat es nach dem ersten Senden etwas gedauert, bis sie auftauchten – kurz Geduld.

### 6. Cron einrichten (alle 10 Minuten)

`crontab -e` und diese Zeile einfügen (Pfad anpassen):

```
*/10 * * * * cd /home/pi/anker-solix-api && .venv/bin/python solix_to_mqtt.py --send > /tmp/solix_cron.log 2>&1
```

Warum der lange Pfad? Cron kennt deine Python-Umgebung nicht. Mit `.venv/bin/python` rufst du direkt das richtige Python auf – ein „Aktivieren" ist nicht nötig. Das Log liegt in `/tmp` (im RAM) und schont die SD-Karte.

### 7. Schalten testen

```bash
python3 solix_switch.py dc off      # 12-V-Ausgang aus
python3 solix_switch.py dc on       # 12-V-Ausgang an
python3 solix_switch.py ac on|off   # AC-Ausgang
python3 solix_switch.py light off|low|medium|high|blinking
```

Bei `OK: …` hat es geklappt. ⚠️ Der AC-Ausgang schaltet alles ab, was daran hängt.

### 8. ioBroker darf schalten (sudo-Regel)

ioBroker läuft meist unter dem Benutzer `iobroker`, deine `.env` gehört aber dir (`pi`). Damit das Skript sie findet, startet ioBroker es per `sudo -u pi`. Die Regel erlaubt **nur diese neun festen Befehle**, sonst nichts:

```bash
bash sudoers/install_sudoers.sh     # Pfade/Benutzer oben im Skript anpassen
```

### 9. ioBroker-Skripte

Im JavaScript-Adapter zwei Skripte anlegen:

1. `iobroker/01_create_datapoints.js` – **einmal** starten, dann stoppen. Legt `0_userdata.0.Anker.c300x_12V_Ausgang`, `…_AC_Ausgang` und `…_Licht` an.
2. `iobroker/02_switch_handler.js` – **dauerhaft** laufen lassen (Pfade oben anpassen).

Fertig: Ein Datenpunkt umschalten → nach ca. 2 Sekunden schaltet die Powerstation. Die Datenpunkte lassen sich auch in Blockly, VIS oder Grafana verwenden.

## Stolpersteine (damit du nicht in dieselben tappst)

- **`pip install -r requirements.txt` geht nicht** – gibt es nicht. → `pip install .`
- **Skripte gehören in den Ordner der Bibliothek**, sonst findet Python `common` nicht.
- **Cron + venv:** Immer den vollen Pfad `.venv/bin/python` benutzen.
- **`.env` mit Sonderzeichen:** Passwörter mit `#` oder Leerzeichen in einfache Anführungszeichen setzen.
- **ioBroker läuft als anderer Benutzer.** Ohne die sudo-Regel fragt das Skript nach E-Mail und Passwort – und das kann ioBroker nicht beantworten.
- **`createState` in der Objekt-Schreibweise** (wie in `01_create_datapoints.js`) hat bei uns funktioniert. Eine Variante mit zusätzlichem Startwert-Parameter brach schon beim Vorbereiten des Skripts ab (Ursache nicht sicher geklärt).
- **Der Umweg „ioBroker → MQTT → Listener auf dem Pi" hat bei uns nicht funktioniert:** Die Befehle kamen im Listener nie an (Ursache nicht geklärt, vermutlich verhält sich der MQTT-Server von ioBroker anders als ein normaler Broker). Deshalb `exec` + `sudo`.
- **`battery_soh` zeigt bei uns immer denselben Wert wie `battery_soc`.** Als Akkugesundheit nicht verlassen.
- **Die Anker-App schaltet offenbar auf einem Weg, den das Monitor-Tool nicht mithört.** Befehle also lieber mit dem Menü (`c`) testen, statt sie mitzuschneiden.
- **Messwerte sind bei Cron nur so frisch wie das Intervall** (hier 10 Minuten). Schalten dauert dagegen nur ca. 2 Sekunden.

## Sicherheit

- 🔐 `.env` nie committen (`.gitignore` ist dabei) und mit `chmod 600` schützen.
- 🔐 Die sudo-Regel erlaubt nur die neun festen Aufrufe. Prüfe sie, bevor du sie installierst.
- ⚠️ Hänge nichts Lebenswichtiges (Kühlschrank, medizinische Geräte) ohne Rückfallebene an einen per Skript schaltbaren Ausgang.
- ⚠️ Das alles nutzt die **inoffizielle** Anker-Cloud-Schnittstelle. Anker kann sie jederzeit ändern. Nutzung auf eigene Gefahr.

## Credits & Haftung

- Die gesamte Cloud-/MQTT-Arbeit erledigt **[anker-solix-api](https://github.com/thomluther/anker-solix-api)** von thomluther (dazu gehört auch die Home-Assistant-Integration). Ohne diese Bibliothek gäbe es dieses Projekt nicht. Bitte beachte deren Lizenz.
- Der ioBroker-Adapter [`ioBroker.anker-solix`](https://github.com/MatthiasUlrich1/ioBroker.anker-solix) von Matthias Ulrich ist ein eigenes Projekt. Er konnte beim A1723 zum Zeitpunkt unseres Tests nur den Ladestand; wir haben dort einen Feature-Request gestellt.
- Dieses Projekt steht in keiner Verbindung zu Anker. Keine Gewähr, keine Haftung (siehe `LICENSE`).

Viel Spaß – und möge dein Akku immer genug Saft haben! ⚡

</details>
