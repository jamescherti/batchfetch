#!/usr/bin/env python3
#
# Copyright (C) 2024-2026 James Cherti
# URL: https://github.com/jamescherti/batchfetch
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.
#
"""Unit tests."""

from pathlib import Path

from batchfetch import helpers

DATA_PATH = Path().joinpath("tests", "data").absolute()
SCRIPT_RUN_SIMPLE = DATA_PATH / "test-run_simple.sh"


def test_indent_raw_output() -> None:
    """Test the indent_raw_output helper function."""
    list_str = helpers.indent_raw_output(["Test 1.", "Test 2."])
    assert list_str == ["    Test 1.", "    Test 2."]
