# slacktoken
A library for retrieving a Slack user token and cookies from an authenticated Slack application.

## Installation
### Linux Prerequisites
To access the secret store which is used to decrypt cookies you will need to install some native dependencies.
```console
$ sudo apt-get install libgirepository1.0-dev
```

### Library Installation
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
