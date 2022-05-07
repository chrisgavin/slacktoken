import abc
import base64
import json
import logging
import sys
import typing

import cryptography.hazmat.primitives.ciphers
import cryptography.hazmat.primitives.ciphers.algorithms
import cryptography.hazmat.primitives.ciphers.modes
import cryptography.hazmat.primitives.hashes
import cryptography.hazmat.primitives.kdf.pbkdf2

import slacktoken.exceptions
import slacktoken.slack_configuration

_LOGGER = logging.getLogger(__name__)

class UnhandleableEncryptionConfiguration(Exception):
	pass

class Decryptor(metaclass=abc.ABCMeta):
	@abc.abstractmethod
	def decrypt(self, encrypted_value:bytes) -> bytes:
		pass

class PasswordBackedDecryptor(Decryptor):
	@abc.abstractmethod
	def get_password(self) -> bytes:
		pass

	@abc.abstractmethod
	def get_iterations(self) -> int:
		pass

	def decrypt(self, encrypted_value:bytes) -> bytes:
		encrypted_value = encrypted_value[3:] # Encrypted cookies start with a version number. e.g. "v11"
		
		length = 16
		salt = b"saltysalt"
		kdf = cryptography.hazmat.primitives.kdf.pbkdf2.PBKDF2HMAC(
			algorithm=cryptography.hazmat.primitives.hashes.SHA1(),
			length=length,
			iterations=self.get_iterations(),
			salt=salt,
		)

		key = kdf.derive(self.get_password())
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
		return cleaned_value

class LinuxPeanutsDecryptor(PasswordBackedDecryptor):
	def get_password(self) -> bytes:
		return b"peanuts"

	def get_iterations(self) -> int:
		return 1

class LibSecretDecryptor(PasswordBackedDecryptor):
	def __init__(self) -> None:
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
					self.password = secret_text.encode("utf-8")
					return
		raise UnhandleableEncryptionConfiguration()

	def get_password(self) -> bytes:
		return self.password

	def get_iterations(self) -> int:
		return 1

class MacOSDecryptor(PasswordBackedDecryptor):
	def __init__(self) -> None:
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
			self.password:bytes = password.encode("utf-8")
			return
		raise UnhandleableEncryptionConfiguration()

	def get_password(self) -> bytes:
		return self.password

	def get_iterations(self) -> int:
		return 1003

class WindowsDecryptor(Decryptor):
	def decrypt(self, encrypted_value:bytes) -> bytes:
		encrypted_value = encrypted_value[3:] # Encrypted cookies start with a version number. e.g. "v11"

		local_state_path = slacktoken.slack_configuration.get_slack_configuration_directory() / "Local State"
		if not local_state_path.is_file():
			raise slacktoken.exceptions.MissingSlackData("local state file")
		local_state = json.loads(local_state_path.read_text())
		encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
		encryption_method = encrypted_key[:5]
		if encryption_method != b"DPAPI":
			printable_encryption_method = encryption_method.decode("utf-8")
			raise slacktoken.exceptions.InternalException(f"Encryption method {printable_encryption_method} is not supported.")
		encrypted_key = encrypted_key[5:]
		import win32crypt
		decrypted_key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]

		
		iv = encrypted_value[:12]
		tag = encrypted_value[-16:]
		cipher = cryptography.hazmat.primitives.ciphers.Cipher(
			algorithm=cryptography.hazmat.primitives.ciphers.algorithms.AES(decrypted_key),
			mode=cryptography.hazmat.primitives.ciphers.modes.GCM(iv, tag),
		)

		decryptor = cipher.decryptor()
		decrypted_value = decryptor.update(encrypted_value[12:-16]) + decryptor.finalize()

		return decrypted_value

def decrypt(encrypted_value:bytes) -> str:
	decryptor_implementations:typing.List[typing.Type[Decryptor]] = []
	if sys.platform == "linux":
		decryptor_implementations.append(LibSecretDecryptor)
		decryptor_implementations.append(LinuxPeanutsDecryptor)
	elif sys.platform == "darwin":
		decryptor_implementations.append(MacOSDecryptor)
	elif sys.platform == "win32":
		decryptor_implementations.append(WindowsDecryptor)
	else:
		raise slacktoken.exceptions.InternalException(f"Cookie decryption not implemented on {sys.platform}.")

	for decryptor_implementation in decryptor_implementations:
		_LOGGER.debug("Trying to decrypt with %s...", decryptor_implementation)
		try:
			decryptor = decryptor_implementation()
			return decryptor.decrypt(encrypted_value).decode("utf-8")
		except UnhandleableEncryptionConfiguration:
			_LOGGER.debug("Decryption failed.")
			continue
	raise slacktoken.exceptions.InternalException("No usable cookie decryptor found.")
