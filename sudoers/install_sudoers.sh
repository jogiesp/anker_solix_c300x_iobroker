#!/bin/bash
# Erlaubt dem ioBroker-Benutzer, GENAU diese neun Befehle als $RUNAS auszufuehren - sonst nichts.
# Allows the ioBroker user to run EXACTLY these nine commands as $RUNAS - nothing else.
# Aufruf / Usage:  bash install_sudoers.sh     (fragt nach deinem sudo-Passwort / asks for your sudo password)
set -e
P="/home/pi/anker-solix-api"   # <- Ordner der Bibliothek / library folder
RUNAS="pi"                     # <- Benutzer, dem die .env gehoert / owner of the .env
IOB="iobroker"                 # <- Benutzer, unter dem ioBroker laeuft / user ioBroker runs as

TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT
for a in "ac on" "ac off" "dc on" "dc off" "light off" "light low" "light medium" "light high" "light blinking"; do
  echo "$IOB ALL=($RUNAS) NOPASSWD: $P/.venv/bin/python $P/solix_switch.py $a"
done > "$TMP"
sudo visudo -cf "$TMP"
sudo install -m 440 -o root -g root "$TMP" /etc/sudoers.d/iobroker-solix
echo "Regel installiert / rule installed"
