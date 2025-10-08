import os
import pathlib
import sys

_XDG_CONFIG_DIR_VARIABLE = "XDG_CONFIG_DIR"

def get_slack_configuration_directory() -> pathlib.Path:
	if sys.platform == "darwin":
		possible_config_directories = [
			pathlib.Path.home() / "Library" / "Application Support" / "Slack",
			pathlib.Path.home() / "Library" / "Containers" / "com.tinyspeck.slackmacgap" / "Data" / "Library" / "Application Support" / "Slack",
		]
		for possible_config_directory in possible_config_directories:
			if possible_config_directory.is_dir():
				return possible_config_directory
		return possible_config_directories[0]
	elif sys.platform == "win32":
		return pathlib.Path(os.environ["APPDATA"]) / "Slack"
	elif _XDG_CONFIG_DIR_VARIABLE in os.environ:
		return pathlib.Path(_XDG_CONFIG_DIR_VARIABLE) / "Slack"
	else:
		return pathlib.Path.home() / ".config" / "Slack"
