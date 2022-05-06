import json
import os
import pathlib
import re
import sys
import typing

import requests

import slacktoken.cookies
import slacktoken.exceptions

_API_TOKEN_MATCHER = re.compile("\"api_token\":\"([^\"]+)\"")
_XDG_CONFIG_DIR_VARIABLE = "XDG_CONFIG_DIR"

class SlackAuthenticationInformation():
	def __init__(self, token:str, cookies:typing.Dict[str, str]):
		self.token = token
		self.cookies = cookies

def _get_slack_configuration_directory() -> pathlib.Path:
	if sys.platform == "darwin":
		possible_config_directories = [
			pathlib.Path.home() / "Library" / "Application Support" / "Slack",
			pathlib.Path.home() / "Library" / "Containers" / "com.tinyspeck.slackmacgap" / "Data" / "Library" / "Application Support" / "Slack",
		]
		for possible_config_directory in possible_config_directories:
			if possible_config_directory.is_dir():
				return possible_config_directory
		return possible_config_directories[0]
	elif _XDG_CONFIG_DIR_VARIABLE in os.environ:
		return pathlib.Path(_XDG_CONFIG_DIR_VARIABLE) / "Slack"
	else:
		return pathlib.Path.home() / ".config" / "Slack"

def _get_slack_workspaces() -> typing.List[str]:
	root_state_path = _get_slack_configuration_directory() / "storage" / "root-state.json"
	if not root_state_path.is_file():
		raise slacktoken.exceptions.MissingSlackData("workspaces file")
	with root_state_path.open() as root_state_file:
		workspaces = json.load(root_state_file)["workspaces"]
	return [workspace["domain"] for workspace in workspaces.values()]

def get(workspace:typing.Optional[str]) -> SlackAuthenticationInformation:
	configuration_directory = _get_slack_configuration_directory()
	cookies = slacktoken.cookies.get_cookies(configuration_directory)
	workspaces = _get_slack_workspaces()
	if not workspaces:
		raise slacktoken.exceptions.NotSignedInException()
	if workspace is None:
		if len(workspaces) == 1:
			workspace = workspaces[0]
		else:
			raise slacktoken.exceptions.AmbiguousWorkspaceException(workspaces)
	else:
		if workspace not in workspaces:
			raise slacktoken.exceptions.NotSignedInToWorkspaceException(workspace)
	response = requests.get(f"https://{workspace}.slack.com/ssb/redirect", cookies=cookies)
	matcher = _API_TOKEN_MATCHER.search(response.text)
	if matcher is None:
		raise slacktoken.exceptions.InternalException("Could not extract Slack token from webpage. Maybe the Slack webpage has changed.")
	return SlackAuthenticationInformation(matcher.group(1), cookies)
