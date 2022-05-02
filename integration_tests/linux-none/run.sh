#!/usr/bin/env sh
set -eu
xvfb-run dbus-launch poetry run ./integration_tests/run.py
