#!/usr/bin/env python3
import argparse
import datetime
import logging
import os
import pathlib
import re
import subprocess
import sys
import time

import playwright.sync_api
import pyotp
import requests

import slacktoken.token

_INTEGRATION_TEST_WORKSPACE = os.environ["SLACKTOKEN_INTEGRATION_TEST_WORKSPACE"]
_INTEGRATION_TEST_USER = os.environ["SLACKTOKEN_INTEGRATION_TEST_USER"]
_INTEGRATION_TEST_PASSWORD = os.environ["SLACKTOKEN_INTEGRATION_TEST_PASSWORD"]
_INTEGRATION_TEST_TOTP_SEED = os.environ["SLACKTOKEN_INTEGRATION_TEST_TOTP_SEED"]

_CI = bool(os.environ.get("CI"))

_MAGIC_LOGIN_LINK_MATCHER = re.compile("slack:\\\\/\\\\/T[A-Z0-9]+\\\\/magic-login\\\\/[0-9]+-[a-f0-9]+")
_RETRY_MESSAGES = {
	"Wait a few minutes and try again.",
}

def _parse_arguments():
	parser = argparse.ArgumentParser()
	parser.add_argument("--debug-login", action="store_true", help="Don't start Slack, just debug the login process.")
	return parser.parse_args()

def _slack_binary():
	if sys.platform == "darwin":
		return "/Applications/Slack.app/Contents/MacOS/Slack"
	elif sys.platform == "win32":
		return str(pathlib.Path(os.environ["PROGRAMFILES"]) / "Slack" / "Slack.exe")
	else:
		return "slack"

def main():
	arguments = _parse_arguments()

	logging.basicConfig()
	logger = logging.getLogger("slacktoken")
	logger.setLevel(logging.DEBUG)

	totp = pyotp.TOTP(_INTEGRATION_TEST_TOTP_SEED)

	if not arguments.debug_login:
		slack_binary = _slack_binary()
		slack_process = subprocess.Popen([slack_binary], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
	try:
		with playwright.sync_api.sync_playwright() as playwright_sync:
			browser = playwright_sync.chromium.launch(headless=False)
			page = browser.new_page()
			for attempt in range(10):
				try:
					logger.info(f"Logging in to Slack attempt {attempt+1}...")
					page.goto(f"https://{_INTEGRATION_TEST_WORKSPACE}.slack.com/sign_in_with_password")

					logger.info("Waiting for login form...")
					page.fill("input[data-qa=login_email]", _INTEGRATION_TEST_USER)
					page.fill("input[data-qa=login_password]", _INTEGRATION_TEST_PASSWORD)
					page.click("button[data-qa=signin_button]")

					logger.info("Waiting for 2FA prompt...")
					page.wait_for_selector("#enter_code_app_root")
					if any(message in page.content() for message in _RETRY_MESSAGES):
						logger.info("Rate limited...")
						time.sleep(datetime.timedelta(minutes=3).total_seconds())
						continue
					with page.expect_response("**/ssb/redirect*") as event:
						code = totp.now()
						for index, digit in enumerate(code):
							page.fill(f".two_factor_input_item input >> nth={index}", digit)

						logger.info("Waiting for login to complete...")
						content = event.value.body().decode("utf-8")
						break
				except Exception:
					logging.exception("Failed to get token.")
			else:
				raise SystemExit("Failed to log in after final attempt.")
			match = _MAGIC_LOGIN_LINK_MATCHER.search(content)
			if not match:
				raise Exception("Failed to find magic login link in page content.")
			magic_login_link = match.group(0).replace("\/", "/")
			if not arguments.debug_login:
				subprocess.check_call([slack_binary, magic_login_link])
			browser.close()

		if arguments.debug_login:
			return
		
		for attempt in range(10):
			logger.info(f"Attempting to get token, attempt {attempt+1}...")
			try:
				authentication_information = slacktoken.token.get(None)
				break
			except Exception:
				logging.exception("Failed to get token.")
			time.sleep(datetime.timedelta(seconds=10).total_seconds())
		else:
			raise SystemExit("Failed to get token after final attempt.")

		logger.info(f"Token is {authentication_information.token[:5]}***.")
		for cookie_name, cookie_value in authentication_information.cookies.items():
			logger.info(f"Cookie is {cookie_name}={cookie_value[:5]}***.")

		response = requests.get("https://slack.com/api/conversations.list", params={"token": authentication_information.token}, cookies=authentication_information.cookies)
		response.raise_for_status()
		if response.json()["ok"] != True:
			raise Exception(f"Failed to authenticate with obtained token: {response.json()}.")
	finally:
		if not arguments.debug_login and not _CI:
			slack_process.terminate()
			slack_process.wait()

if __name__ == "__main__":
	main()
