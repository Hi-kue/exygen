# README
# *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*
# This Makefile is our global codebase Makefile that
# chains multiple workspace scripts and Nx targets
# into common commands for exygen apps (/apps).
# The concept is simple, when certain commands are
# called it will call 'scripts/*sh' on Linux and Mac,
# or 'scripts/win/*.ps1' for anyone who is using
# Windows.
#
# Current File: Makefile
# Commands: run 'make help'
# *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*

ifeq ($(OS),Windows_NT)
    SCRIPT = powershell -NoProfile -ExecutionPolicy Bypass -File scripts/win/$(1).ps1
else
    SCRIPT = bash scripts/$(1).sh
endif

CLEAN := $(call SCRIPT,clean)
BUILD := $(call SCRIPT,build)
RUN := $(call SCRIPT,run)
SET_ENV := $(call SCRIPT,set-env)
ENABLE := $(call SCRIPT,enable)
NX := pnpm nx

# NOTE: 
# These below are apps the scripts currently support and exists within
# the /apps folder.
SCRIPT_APPS := agent api web docs tui

# NOTE: Overrides for common script commands, e.g. make run APPS="api web".
APPS ?=
ARGS ?=

.DEFAULT_GOAL := help

define HELP_TEXT
Usage: make <command> [APPS="api web"] [ARGS="--dry-run"]

Project:
  setup            Unblock scripts, write missing .env files, install dependencies.
  dev              Clean everything, reinstall, build, and run agent, api, and web.
  run              Run without cleaning or building (accepts APPS and ARGS).
  build            Build agent, api, and web (accepts APPS and ARGS).
  clean            Remove build artifacts, node_modules, and .venv, after a prompt
                   (accepts APPS and ARGS, ARGS=--yes skips the prompt).
  install          Write missing .env files and install dependencies.
  env              Write missing .env files (accepts APPS and ARGS).
  upgrade          Upgrade Python and Node dependencies and their lockfiles.
  migrate          Run database migrations (none exist yet).

Per app (<app> is agent, api, web, or tui):
  dev-<app>        Clean, reinstall, build, and run one app.
  run-<app>        Run one app.
  build-<app>      Build one app.
  test-<app>       Test one app.
  clean-<app>      Clean one app, after a prompt (ARGS=--yes skips it).

Quality:
  test             Run tests across all projects.
  lint             Lint all projects.
  format           Check formatting across all projects (does not write).
  check            Run lint and format checks across all projects.
  typecheck        Typecheck all projects.

Other:
  docs             Serve the docs site on http://localhost:3001.
  docs-build       Build the docs site and verify its assets.
  graph            Open the Nx project graph.
  help             Show this message.
endef

.PHONY: help setup dev run build clean install env upgrade migrate
.PHONY: test lint format check typecheck docs docs-build graph
.PHONY: $(foreach cmd,dev run build test clean,$(addprefix $(cmd)-,$(SCRIPT_APPS) tui))
.PHONY: require-tui

help:
	$(info $(HELP_TEXT))
	@exit 0

setup:
	$(ENABLE)
	$(SET_ENV) --sync

# NOTE:
# 'clean' removes node_modules and .venv, so dependencies
# must be reinstalled before 'build' can find pnpm, nx, or
# uv's packages.
dev:
	$(CLEAN) --all --yes
	$(SET_ENV) --sync
	$(BUILD) --all
	$(RUN)

$(addprefix dev-,$(SCRIPT_APPS)): dev-%:
	$(CLEAN) $* --yes
	$(SET_ENV) --sync
	$(BUILD) $*
	$(RUN) $*

run:
	$(RUN) $(APPS) $(ARGS)

$(addprefix run-,$(SCRIPT_APPS)): run-%:
	$(RUN) $* $(ARGS)

build:
	$(BUILD) $(APPS) $(ARGS)

$(addprefix build-,$(SCRIPT_APPS)): build-%:
	$(BUILD) $* $(ARGS)

clean:
	$(CLEAN) $(APPS) $(ARGS)

$(addprefix clean-,$(SCRIPT_APPS)): clean-%:
	$(CLEAN) $* $(ARGS)

install:
	$(SET_ENV) --sync

env:
	$(SET_ENV) $(APPS) $(ARGS)

upgrade:
	uv lock --upgrade
	uv sync --all-packages
	pnpm update -r

migrate:
	$(info Nothing to migrate: Exygen has no database or migrations yet.)
	@exit 0

test:
	$(NX) run-many -t test

$(addprefix test-,$(SCRIPT_APPS)): test-%:
	$(NX) run $*:test

lint:
	$(NX) run-many -t lint

format:
	$(NX) run-many -t format

check:
	$(NX) run-many -t check

typecheck:
	$(NX) run-many -t typecheck

docs:
	$(NX) run docs:dev

docs-build:
	$(NX) run docs:build

graph:
	$(NX) graph

require-tui:
	$(if $(wildcard apps/tui/project.json),,$(error The TUI app does not exist yet: apps/tui/project.json is missing))

dev-tui: require-tui
	$(CLEAN) apps/tui --yes
	$(SET_ENV) --sync
	$(NX) run tui:build
	$(NX) run tui:dev

run-tui: require-tui
	$(NX) run tui:dev

build-tui: require-tui
	$(NX) run tui:build

test-tui: require-tui
	$(NX) run tui:test

clean-tui: require-tui
	$(CLEAN) apps/tui $(ARGS)
