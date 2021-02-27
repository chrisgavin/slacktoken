import slacktoken.version

def test_version_returns_consistent_version_number() -> None:
	assert slacktoken.version.version() == slacktoken.version.version()
