import argparse
import logging

import slacktoken.commands.get
import slacktoken.commands.version

_LOGGER = logging.getLogger("slacktoken")

def _parse_arguments() -> argparse.Namespace:
	argument_parser = argparse.ArgumentParser(description="A library for retrieving a Slack user token from an authenticated Slack application.")
	argument_parser.add_argument("--verbose", action="store_true", help="Increases the log level.")
	subparsers = argument_parser.add_subparsers(help="The command to run.", dest="command")
	subparsers.required = True
	subparsers.add_parser("version", help="Show the version of the application.")
	get_parser = subparsers.add_parser("get", help="Get a Slack token.")
	get_parser.add_argument("--workspace", nargs="?", help="The workspace to get a Slack token for.")
	return argument_parser.parse_args()

def main() -> None:
	arguments = _parse_arguments()
	logging.basicConfig()
	_LOGGER.setLevel(logging.DEBUG if arguments.verbose else logging.INFO)
	if arguments.command == "version":
		slacktoken.commands.version.command(arguments)
	if arguments.command == "get":
		slacktoken.commands.get.command(arguments)

if __name__ == "__main__":
	main()
