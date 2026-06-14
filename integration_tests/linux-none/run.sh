#!/usr/bin/env sh
set -eu
sudo apt-get remove --yes gnome-keyring
xvfb-run dbus-launch poetry run ./integration_tests/run.py
