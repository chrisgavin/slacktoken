import importlib_metadata
import versio.version
import versio.version_scheme

def version() -> versio.version.Version:
	version_string = importlib_metadata.version("slacktoken")
	return versio.version.Version(version_string, versio.version_scheme.Pep440VersionScheme)
