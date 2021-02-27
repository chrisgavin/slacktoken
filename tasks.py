import os
import pathlib

import invoke

_GITHUB_ACTIONS = "GITHUB_ACTIONS" in os.environ

@invoke.task()
def setup(context):
	extras_flag = ""
	if _GITHUB_ACTIONS:
		extras_flag = "--extras github_actions"
	context.run(f"poetry install {extras_flag}")

@invoke.task(pre=[setup])
def lint_flake8(context):
	format_flag = ""
	if _GITHUB_ACTIONS:
		format_flag = "--format=\"::error file=%(path)s,line=%(row)d,col=%(col)d::%(text)s\""
	context.run(f"poetry run flake8 {format_flag}")

@invoke.task(pre=[setup])
def lint_mypy(context):
	context.run("poetry run mypy slacktoken tests")

@invoke.task(pre=[setup])
def lint_pyproject(context):
	context.run("poetry check")

@invoke.task(lint_pyproject, lint_flake8, lint_mypy)
def lint(context):
	pass

@invoke.task(pre=[setup])
def test_pytest(context):
	context.run("poetry run pytest")

@invoke.task(test_pytest)
def test(context):
	pass

@invoke.task(lint, test)
def ci(context):
	pass

@invoke.task()
def build(context):
	output = pathlib.Path() / "dist"
	output.mkdir(exist_ok=True)
	requirements = output / "requirements.txt"
	context.run(f"poetry export --output {requirements}")
	context.run("poetry build")

@invoke.task(pre=[build])
def publish(context):
	context.run("poetry publish --no-interaction --username __token__ --password $PYPI_TOKEN")
