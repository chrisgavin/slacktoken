import pathlib
import types
import typing

class ShadowFile():
	def __init__(self, path:pathlib.Path):
		import wmi
		self.path = path
		self.wmi_client = wmi.WMI()
		self.shadow_object = None

	def __enter__(self) -> pathlib.Path:
		drive = self.path.drive[0]
		result, shadow_copy_id = self.wmi_client.Win32_ShadowCopy.Create(Context="ClientAccessible", Volume=f"{drive}:\\")

		if result != 0:
			raise Exception(f"Failed to create shadow copy ({result}).")

		self.shadow_object = self.wmi_client.Win32_ShadowCopy(ID=shadow_copy_id)[0]

		assert self.shadow_object is not None

		parts = self.path.parts[1:]
		shadow_path = pathlib.Path(self.shadow_object.DeviceObject)
		for part in parts:
			shadow_path /= part

		return shadow_path

	def __exit__(self, exc_type:typing.Optional[typing.Type[BaseException]], exc_value:typing.Optional[BaseException], traceback:typing.Optional[types.TracebackType]) -> typing.Optional[bool]:
		if self.shadow_object is not None:
			self.shadow_object.Delete_()
			self.shadow_object = None
		return None
