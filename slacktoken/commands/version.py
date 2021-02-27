import argparse

import slacktoken.version

def command(arguments:argparse.Namespace) -> None:
	print(slacktoken.version.version())
