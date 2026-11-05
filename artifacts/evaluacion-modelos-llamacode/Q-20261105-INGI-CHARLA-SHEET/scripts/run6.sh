#!/bin/bash
export AGENT_DESKTOP_HOME=$PWD/adhome
/usr/libexec/at-spi-bus-launcher --launch-immediately >/dev/null 2>&1 &
openbox >/dev/null 2>&1 &
sleep 1
LLAMACODE_AGENT_DESKTOP=$2 QT_QPA_PLATFORM=xcb timeout 60 stdbuf -oL $1 > qa6.out 2>&1; echo rc=$? >> qa6.out
