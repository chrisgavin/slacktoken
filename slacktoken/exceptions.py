import typing

class MissingSlackData(Exception):
	def __init__(self, data:str) -> None:
		super().__init__(f"Slack {data} is missing. Have you installed Slack and logged in?")

class NotSignedInException(Exception):
	def __init__(self) -> None:
		super().__init__("You are not signed in to any Slack workspaces.")

class NotSignedInToWorkspaceException(Exception):
	def __init__(self, workspace:str) -> None:
		super().__init__(f"You are not signed in to the {workspace} Slack workspace.")

class AmbiguousWorkspaceException(Exception):
	def __init__(self, workspaces:typing.List[str]) -> None:
		self.workspaces = workspaces
		workspaces_list = ", ".join(workspaces)
		super().__init__(f"You are signed in to multiple Slack workspaces ({workspaces_list}). An explicit workspace to get a token for must be provided.")

class InternalException(Exception):
	pass
