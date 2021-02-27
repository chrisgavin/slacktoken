import argparse

import slacktoken.token

def command(arguments:argparse.Namespace) -> None:
	print(slacktoken.token.get(arguments.workspace))
