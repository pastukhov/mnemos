"""Tests for the CLI command tree after removing wiki commands."""

from __future__ import annotations

import argparse
import sys

import pytest

from cli import build_parser, main


def _subcommand_names(parser: argparse.ArgumentParser) -> set[str]:
  for action in parser._actions:
    if isinstance(action, argparse._SubParsersAction):
      return set(action.choices)
  raise AssertionError("expected subparsers on the mnemos CLI parser")


def test_cli_does_not_expose_wiki_command():
  parser = build_parser()
  subcommands = _subcommand_names(parser)

  assert subcommands == {"ingest", "extract", "reflect", "candidates", "mcp-server"}
  assert "wiki" not in subcommands
  assert "mnemos wiki build" not in parser.format_help()


def test_cli_rejects_removed_wiki_command(monkeypatch, capsys):
  monkeypatch.setattr(sys, "argv", ["mnemos", "wiki"])

  with pytest.raises(SystemExit) as excinfo:
    main()

  assert excinfo.value.code == 2
  assert "invalid choice: 'wiki'" in capsys.readouterr().err
