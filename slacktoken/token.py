import json
import pathlib
import re
import sqlite3
import typing

import requests
import xdg

import slacktoken.exceptions

_API_TOKEN_MATCHER = re.compile("\"api_token\":\"([^\"]+)\"")

def _get_slack_configuration_directory() -> pathlib.Path:
	return xdg.xdg_config_home() / "Slack"

def _get_slack_cookies() -> typing.Dict[str, str]:
	cookie_database_path = _get_slack_configuration_directory() / "Cookies"
	if not cookie_database_path.is_file():
		raise slacktoken.exceptions.MissingSlackData("cookie database")
	cookie_database = sqlite3.connect(str(cookie_database_path))
	cookie_cursor = cookie_database.cursor()
	cookie_cursor.execute("SELECT value FROM cookies WHERE host_key=\".slack.com\" AND name=\"d\"")
	cookie = cookie_cursor.fetchone()
	if cookie is None:
		raise slacktoken.exceptions.MissingSlackData("login cookie")
	return {"d": cookie[0]}

def _get_slack_workspaces() -> typing.List[str]:
	workspaces_path = _get_slack_configuration_directory() / "storage" / "slack-workspaces"
	if not workspaces_path.is_file():
		raise slacktoken.exceptions.MissingSlackData("workspaces file")
	with workspaces_path.open() as workspaces_file:
		workspaces = json.load(workspaces_file)
	return [workspace["domain"] for workspace in workspaces.values()]

def get(workspace:typing.Optional[str]) -> str:
	cookies = _get_slack_cookies()
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
	response = requests.get(f"https://{workspace}.slack.com/", cookies=cookies)
	matcher = _API_TOKEN_MATCHER.search(response.text)
	if matcher is None:
		raise slacktoken.exceptions.InternalException("Could not extract Slack token from webpage. Maybe the Slack webpage has changed.")
	return matcher.group(1)
