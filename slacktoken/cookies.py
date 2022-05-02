import pathlib
import sqlite3
import sys
import typing

import cryptography.hazmat.primitives.ciphers
import cryptography.hazmat.primitives.ciphers.algorithms
import cryptography.hazmat.primitives.ciphers.modes
import cryptography.hazmat.primitives.hashes
import cryptography.hazmat.primitives.kdf.pbkdf2

import slacktoken.exceptions

def _get_encryption_password() -> bytes:
	if sys.platform == "linux":
		import gi
		gi.require_version("Secret", "1")
		import gi.repository.Secret

		service = gi.repository.Secret.Service.get_sync(gi.repository.Secret.ServiceFlags.LOAD_COLLECTIONS)
		keyring_collections = service.get_collections()
		unlocked_keyrings = service.unlock_sync(keyring_collections).unlocked

		for keyring in unlocked_keyrings:
			for item in keyring.get_items():
				if item.get_label() == "Chromium Safe Storage":
					item.load_secret_sync()
					secret_text = item.get_secret().get_text()
					assert isinstance(secret_text, str)
					return secret_text.encode("utf-8")

		return b"peanuts"
	else:
		raise slacktoken.exceptions.InternalException(f"Cookie decryption not implemented on {sys.platform}.")

def _decrypt(encrypted_value:bytes) -> str:
	encrypted_value = encrypted_value[3:] # Encrypted cookies start with a version number. e.g. "v11"
	password = _get_encryption_password()
	
	length = 16
	salt = b"saltysalt"
	iterations = 1
	kdf = cryptography.hazmat.primitives.kdf.pbkdf2.PBKDF2HMAC(
		algorithm=cryptography.hazmat.primitives.hashes.SHA1(),
		length=length,
		iterations=iterations,
		salt=salt,
	)

	key = kdf.derive(password)
	iv = b" " * length
	cipher = cryptography.hazmat.primitives.ciphers.Cipher(
		algorithm=cryptography.hazmat.primitives.ciphers.algorithms.AES(key),
		mode=cryptography.hazmat.primitives.ciphers.modes.CBC(iv),
	)

	decryptor = cipher.decryptor()
	decrypted_value = decryptor.update(encrypted_value) + decryptor.finalize()

	length_byte = decrypted_value[-1]
	cleaned_value = decrypted_value[:-length_byte]

	assert isinstance(cleaned_value, bytes)
	return cleaned_value.decode("utf-8")
	
def get_cookies(configuration_directory:pathlib.Path) -> typing.Dict[str, str]:
	cookie_database_path = configuration_directory / "Cookies"
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
		value = _decrypt(encrypted_value)
	return {"d": value}
