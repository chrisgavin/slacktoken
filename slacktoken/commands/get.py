import argparse
import urllib.parse

import slacktoken.token

def command(arguments:argparse.Namespace) -> None:
	authentication_information = slacktoken.token.get(arguments.workspace)
	print(authentication_information.token)
	print("; ".join([f"{urllib.parse.quote(key)}={urllib.parse.quote(value)}" for key, value in authentication_information.cookies.items()]))
