import dataclasses
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

@dataclasses.dataclass
class EncryptionConfiguration():
	password:bytes = b"peanuts"
	iterations:int = 1

def _get_encryption_configuration() -> EncryptionConfiguration:
	if sys.platform == "linux":
		configuration = EncryptionConfiguration()
		import gi
		gi.require_version("Secret", "1")
		import gi.repository.Secret

		service = gi.repository.Secret.Service.get_sync(gi.repository.Secret.ServiceFlags.LOAD_COLLECTIONS)
		keyring_collections = service.get_collections()
		unlocked_keyrings = service.unlock_sync(keyring_collections).unlocked

		for keyring in unlocked_keyrings:
			for item in keyring.get_items():
				attributes = item.get_attributes()
				if attributes.get("application") == "Slack" and attributes.get("xdg:schema") is not None and attributes.get("xdg:schema").startswith("chrome_libsecret_os_crypt_password_"):
					item.load_secret_sync()
					secret_text = item.get_secret().get_text()
					assert isinstance(secret_text, str)
					configuration.password = secret_text.encode("utf-8")
					return configuration

		return configuration
	elif sys.platform == "darwin":
		configuration = EncryptionConfiguration(iterations=1003)
		import keyring.backends.macOS.api
		query = keyring.backends.macOS.api.create_query(
			kSecClass=keyring.backends.macOS.api.k_("kSecClassGenericPassword"),
			kSecMatchLimit=keyring.backends.macOS.api.k_("kSecMatchLimitOne"),
			kSecAttrService="Slack Safe Storage",
			kSecReturnData=keyring.backends.macOS.api.create_cfbool(True),
		)
		data = keyring.backends.macOS.api.c_void_p()
		status = keyring.backends.macOS.api.SecItemCopyMatching(query, keyring.backends.macOS.api.byref(data))
		if status != keyring.backends.macOS.api.error.item_not_found:
			keyring.backends.macOS.api.Error.raise_for_status(status)
			password = keyring.backends.macOS.api.cfstr_to_str(data)
			configuration.password = password.encode("utf-8")
		return configuration
	else:
		raise slacktoken.exceptions.InternalException(f"Cookie decryption not implemented on {sys.platform}.")

def _decrypt(encrypted_value:bytes) -> str:
	encrypted_value = encrypted_value[3:] # Encrypted cookies start with a version number. e.g. "v11"
	encryption_configuration = _get_encryption_configuration()
	
	length = 16
	salt = b"saltysalt"
	kdf = cryptography.hazmat.primitives.kdf.pbkdf2.PBKDF2HMAC(
		algorithm=cryptography.hazmat.primitives.hashes.SHA1(),
		length=length,
		iterations=encryption_configuration.iterations,
		salt=salt,
	)

	key = kdf.derive(encryption_configuration.password)
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
