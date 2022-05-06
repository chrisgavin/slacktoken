#!/usr/bin/env python3
import os
import re
import subprocess
import sys
import time
import traceback

import playwright.sync_api
import requests

import slacktoken.token

_INTEGRATION_TEST_WORKSPACE = os.environ["SLACKTOKEN_INTEGRATION_TEST_WORKSPACE"]
_INTEGRATION_TEST_USER = os.environ["SLACKTOKEN_INTEGRATION_TEST_USER"]
_INTEGRATION_TEST_PASSWORD = os.environ["SLACKTOKEN_INTEGRATION_TEST_PASSWORD"]

_MAGIC_LOGIN_LINK_MATCHER = re.compile("slack:\\\\/\\\\/T[A-Z0-9]+\\\\/magic-login\\\\/[0-9]+-[a-f0-9]+")

def _slack_binary():
	if sys.platform == "darwin":
		return "/Applications/Slack.app/Contents/MacOS/Slack"
	else:
		return "slack"

def main():
	slack_binary = _slack_binary()
	slack_process = subprocess.Popen([slack_binary], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
	try:
		with playwright.sync_api.sync_playwright() as playwright_sync:
			browser = playwright_sync.chromium.launch(headless=False)
			page = browser.new_page()
			page.goto(f"https://{_INTEGRATION_TEST_WORKSPACE}.slack.com/")
			page.fill("#email", _INTEGRATION_TEST_USER)
			page.fill("#password", _INTEGRATION_TEST_PASSWORD)
			with page.expect_response("**/ssb/redirect*") as event:
				page.click("#signin_btn")
				content = event.value.body().decode("utf-8")
			match = _MAGIC_LOGIN_LINK_MATCHER.search(content)
			if not match:
				raise Exception("Failed to find magic login link in page content.")
			magic_login_link = match.group(0).replace("\/", "/")
			subprocess.check_call([slack_binary, magic_login_link])
			browser.close()
		
		for attempt in range(0, 10):
			print(f"Attempting to get token, attempt {attempt+1}...", file=sys.stderr)
			try:
				authentication_information = slacktoken.token.get(None)
				break
			except Exception:
				traceback.print_exc()
			time.sleep(10)
		else:
			raise SystemExit("Failed to get token.")

		print(f"Token: {authentication_information.token[:5]}***")
		for cookie_name, cookie_value in authentication_information.cookies.items():
			print(f"Cookie: {cookie_name}={cookie_value[:5]}***")

		response = requests.get("https://slack.com/api/conversations.list", params={"token": authentication_information.token}, cookies=authentication_information.cookies)
		response.raise_for_status()
		if response.json()["ok"] != True:
			raise Exception(f"Failed to authenticate with obtained token: {response.json()}.")
	finally:
		slack_process.terminate()
		slack_process.wait()

if __name__ == "__main__":
	main()
