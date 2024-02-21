import json
import re
import typing

import requests

import slacktoken.cookies
import slacktoken.exceptions

_AUTHENTICATION_JSON_MATCHER = re.compile("JSON\\.stringify\\((.+)\\);")

class SlackAuthenticationInformation():
	def __init__(self, token:str, cookies:typing.Dict[str, str]):
		self.token = token
		self.cookies = cookies

def get(workspace:typing.Optional[str]) -> SlackAuthenticationInformation:
	cookies = slacktoken.cookies.get_cookies()

	response = requests.get("https://app.slack.com/auth", params={"app": "client"}, cookies=cookies)
	matcher = _AUTHENTICATION_JSON_MATCHER.search(response.text)
	if matcher is None:
		raise slacktoken.exceptions.InternalException("Could not extract Slack token from webpage. Maybe the Slack webpage has changed.")
	authentication_information = json.loads(matcher.group(1))

	if workspace is None:
		if len(authentication_information["teams"]) == 1:
			workspace = list(authentication_information["teams"].values())[0]["domain"]
		else:
			raise slacktoken.exceptions.AmbiguousWorkspaceException([team["domain"] for team in authentication_information["teams"].values()])
	
	workspace_informations = [team for team in authentication_information["teams"].values() if team["domain"] == workspace]
	if len(workspace_informations) == 0:
		raise slacktoken.exceptions.NotSignedInToWorkspaceException(workspace)

	return SlackAuthenticationInformation(workspace_informations[0]["token"], cookies)
