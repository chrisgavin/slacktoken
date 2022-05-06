import sqlite3
import sys
import typing

import slacktoken.decryptor
import slacktoken.exceptions
import slacktoken.slack_configuration
	
def get_cookies() -> typing.Dict[str, str]:
	cookie_database_path = slacktoken.slack_configuration.get_slack_configuration_directory() / "Cookies"
	if sys.platform == "win32":
		cookie_database_path = slacktoken.slack_configuration.get_slack_configuration_directory() / "Network" / "Cookies"
	if not cookie_database_path.is_file():
		raise slacktoken.exceptions.MissingSlackData("cookie database")
	cookie_database = sqlite3.connect(str(cookie_database_path))
	cookie_cursor = cookie_database.cursor()
	cookie_cursor.execute("SELECT value, encrypted_value FROM cookies WHERE host_key=\".slack.com\" AND name=\"d\"")
	cookie = cookie_cursor.fetchone()
	if cookie is None:
		raise slacktoken.exceptions.MissingSlackData("login cookie")
	value, encrypted_value = cookie
	if value == "" and encrypted_value != "":
		value = slacktoken.decryptor.decrypt(encrypted_value)
	return {"d": value}
