#!/usr/bin/env sh
set -eu
cat <<"EOF" | xvfb-run dbus-launch sh
set -eu
echo "" | gnome-keyring-daemon --unlock --components=secrets
export XDG_CURRENT_DESKTOP=GNOME
poetry run ./integration_tests/run.py
EOF
