#!/usr/bin/env python
# pylint: disable=redefined-outer-name
"""Unit tests."""

from pathlib import Path

import pytest
import batchfetch


DATA_PATH = Path(".").joinpath("tests", "data").absolute()
