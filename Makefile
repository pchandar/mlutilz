.PHONY = help test clean release dev-release
.DEFAULT_GOAL = help

VER:=$(shell cat src/mlutilz/__init__.py| head -1 | sed 's/__version__ = \"\(.*\)\"/\1/')
TAG:=dev$(shell echo `date '+%Y%m%d%H%m%s'`)

# The @ makes sure that the command itself isn't echoed in the terminal
help:
	@echo "---------------HELP-----------------"
	@echo "To setup the project type make setup"
	@echo "To test the project type make test"
	@echo "To run the project type make run"
	@echo "------------------------------------"

release:
	bumpversion --tag release --dry-run --verbose
	@echo -n "Ready for release. Are you sure? [y/N] " && read ans && [ $${ans:-N} = y ]
	bumpversion --tag release
	cat src/mlutilz/version.py| head -1 | sed 's/__version__ = \"\(.*\)\"/\1/'
	git push --tags
	bumpversion patch
	git push origin master

dev-release:
	@echo -n "Ready to release version $(VER). Are you sure? [y/N] " && read ans && [ $${ans:-N} = y ]
	git tag "v$(VER)"
	git push origin "v$(VER)"
	@bumpversion build --allow-dirty
	git push
	
test:
	pytest tests

clean:
	rm -rf .pytest_cache
	rm -f coverage.xml junit.xml
	rm -rf dist build
	rm -rf .coverage*
	rm -rf __pycache__
	rm -rf .mypy_cache/