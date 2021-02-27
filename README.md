# slacktoken
A library for retrieving a Slack user token from an authenticated Slack application.

## Installation
```console
$ python3 -m pip install slacktoken
```

## CLI Usage
```console
$ python3 -m slacktoken get --workspace my-workspace
xoxs-12345678910-...
```

## Library Usage
```pycon
>>> import slacktoken.token
>>> slacktoken.token.get("my-workspace")
'xoxs-12345678910-...'
```
