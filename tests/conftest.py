"""Shared fixtures: repo root (for BANKS.yaml/RECORDS.yaml) and temp dirs."""
from __future__ import annotations
import os
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def repo_root() -> str:
    return str(REPO_ROOT)


@pytest.fixture
def tmp_path_str(tmp_path) -> str:
    return str(tmp_path)
