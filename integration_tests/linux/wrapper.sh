#!/usr/bin/env sh
set -eu
xvfb-run dbus-launch ./integration_tests/linux/run.sh
