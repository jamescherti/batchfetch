#!/usr/bin/env python
#
# Copyright (c) James Cherti
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

DATA_PATH = Path(".").joinpath("tests", "data").absolute()
SCRIPT_RUN_SIMPLE = DATA_PATH / "test-run_simple.sh"
TEST_MD5SUM_FILE = DATA_PATH / "test-md5sum.txt"


def test_md5sum():
    md5sum = helpers.md5sum(TEST_MD5SUM_FILE)
    assert md5sum == "f31e127edc87a6aa2eb01b7d94d2ec58"


def test_run_simple():
    # Stdout
    stdout_lines, stderr_lines = helpers.run_simple(str(SCRIPT_RUN_SIMPLE))
    assert stdout_lines == ['Test 1.',
                            'Test 2.',
                            'Test 3.']
    assert stderr_lines == ['Test 3.']


def test_indent_raw_output():
    list_str = \
        helpers.indent_raw_output(["Test 1.", "Test 2."])

    assert list_str == ["    Test 1.", "    Test 2."]


def test_run_indent():
    stdout_lines, stderr_lines = helpers.run_indent(str(SCRIPT_RUN_SIMPLE))
    assert stdout_lines == [f'    [RUN] {str(SCRIPT_RUN_SIMPLE)}',
                            '    Test 1.',
                            '    Test 2.',
                            '    Test 3.']
    assert stderr_lines == ['    Test 3.']
