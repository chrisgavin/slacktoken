import logging
import sqlite3
import sys
import typing

import slacktoken.decryptor
import slacktoken.exceptions
import slacktoken.slack_configuration

_LOGGER = logging.getLogger(__name__)

def get_cookies() -> typing.Dict[str, str]:
	cookie_database_path = slacktoken.slack_configuration.get_slack_configuration_directory() / "Cookies"
	if sys.platform == "win32":
		cookie_database_path = slacktoken.slack_configuration.get_slack_configuration_directory() / "Network" / "Cookies"
	if not cookie_database_path.is_file():
		raise slacktoken.exceptions.MissingSlackData("cookie database")
	_LOGGER.debug("Reading cookies from %s.", cookie_database_path)
	cookie_database = sqlite3.connect(str(cookie_database_path))
	cookie_database.text_factory = bytes
	version_cursor = cookie_database.cursor()
	version_cursor.execute("SELECT value FROM meta WHERE key=\"version\"")
	version = int(version_cursor.fetchone()[0])
	cookie_cursor = cookie_database.cursor()
	cookie_cursor.execute("SELECT value, encrypted_value FROM cookies WHERE host_key=\".slack.com\" AND name=\"d\"")
	cookie = cookie_cursor.fetchone()
	if cookie is None:
		raise slacktoken.exceptions.MissingSlackData("login cookie")
	value, encrypted_value = cookie
	value = value.decode("utf-8")
	if len(value) == 0 and len(encrypted_value) > 0:
		_LOGGER.debug("Cookie is encrypted. Will attempt to decrypt...")
		decrypted_value = slacktoken.decryptor.decrypt(encrypted_value)
		if version >= 24:
			# Remove the domain hash from the encrypted value.
			decrypted_value = decrypted_value[32:]
		value = decrypted_value.decode("utf-8")
	else:
		_LOGGER.debug("Cookie is not encrypted.")
	return {"d": value}
