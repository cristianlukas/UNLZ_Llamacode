#!/bin/bash
export AGENT_DESKTOP_HOME=$PWD/adhome
/usr/libexec/at-spi-bus-launcher --launch-immediately >/dev/null 2>&1 &
openbox >/dev/null 2>&1 &
sleep 1; gnome-calculator >/dev/null 2>&1 & sleep 3
python3 e2e.py $1
