# slacktoken
A library for retrieving a Slack user token and cookies from an authenticated Slack application.

## Installation
```console
$ python3 -m pip install slacktoken
```

## CLI Usage
```console
$ python3 -m slacktoken get --workspace my-workspace
xoxs-12345678910-...
d=...
```

## Library Usage
```pycon
>>> import slacktoken.token
>>> authentication_information = slacktoken.token.get("my-workspace")
>>> authentication_information.token
'xoxs-12345678910-...'
>>> authentication_information.cookies
{'d': '...'}
```
