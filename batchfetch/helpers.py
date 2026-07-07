#!/usr/bin/env python
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
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.
#
"""Batchfetch helper functions."""

from __future__ import annotations

import hashlib
import os
import shlex
from pathlib import Path
from subprocess import PIPE, CalledProcessError, Popen, list2cmdline
from typing import Any


def md5sum(filename: os.PathLike) -> str:
    """Calculate and return the MD5 checksum of a file.

    Args:
        filename: Path to the file for which the MD5 checksum is calculated.

    Returns:
        str: The MD5 checksum of the file.
    """
    md5 = hashlib.md5()
    with open(filename, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            md5.update(chunk)
    return md5.hexdigest()


def run_simple(cmd: list[str] | str,
               **kwargs: Any) -> tuple[list[str], list[str]]:
    """Execute a command and return stdout and stderr.

    Executes a command and returns stdout and stderr as separate lists of
    strings.

    :param cmd: Command to be executed. Can be a list or a string.
    :param kwargs: Additional keyword arguments for Popen.
    :return: Tuple containing two lists: stdout lines and stderr lines.
    """
    full_cmd = shlex.split(cmd) if isinstance(cmd, str) else cmd

    with Popen(full_cmd, stdout=PIPE, stderr=PIPE, text=True,
               **kwargs) as process:
        stdout, stderr = process.communicate()

    stdout_lines = stdout.splitlines()
    stderr_lines = stderr.splitlines()

    if process.returncode != 0:
        raise CalledProcessError(returncode=process.returncode,
                                 cmd=cmd,
                                 output=stdout,
                                 stderr=stderr)

    return (stdout_lines, stderr_lines)


def run_indent_str(cmd: list[str] | str, **kwargs: Any) -> str:
    """Execute a command and return its stdout output as a single string.

    Executes a command and returns its stdout output as a single string with
    preserved line breaks.

    :param cmd: Command to be executed. Can be a list of strings or a single
    string.
    :param kwargs: Additional keyword arguments for the execution function.
    :return: A string containing the stdout of the executed command, with each
    line separated by a newline character.
    """
    stdout, _ = run_indent(cmd=cmd, **kwargs)
    return "\n".join(stdout) + "\n"


def indent_raw_output(raw_output: list[str], spaces: int = 4) -> list[str]:
    """Indent each line of the given list of strings.

    :param raw_output: List of strings to indent.
    :param spaces: Number of spaces to indent each line.
    :return: A new list of strings with each line indented as specified.
    """
    indentation = ' ' * spaces
    return [indentation + line for line in raw_output]


def run_indent(cmd: list[str] | str, spaces: int = 4,
               **kwargs: Any) -> tuple[list[str], list[str]]:
    """Execute a command and return its stdout and stderr output indented.

    Executes a command and returns its stdout and stderr output, both indented.

    :param cmd: Command to be executed, either as a list of strings or a single
    string.
    :param spaces: Number of spaces to use for indentation.
    :param kwargs: Additional keyword arguments for `run_simple`.
    :return: A tuple containing two lists: indented stdout and stderr lines.
    """
    cmd = shlex.split(cmd) if isinstance(cmd, str) else cmd
    stdout, stderr = run_simple(cmd=cmd, **kwargs)
    stdout = indent_raw_output([f"[RUN] {list2cmdline(cmd)}"], spaces) + \
        indent_raw_output(stdout, spaces + spaces)
    stderr = indent_raw_output(stderr, spaces)

    return (stdout, stderr)


def collect_parent_dirs(base_dir: Path, directory: Path) -> set[Path]:
    """Collect all parent directories of 'dir' until 'base_dir' is reached.

    If 'dir' is not inside 'base_dir', return None.
    """
    parents: set[Path] = set()

    for dir_path, base_path in ((directory.resolve(), base_dir.resolve()),
                                (directory.absolute(), base_dir.absolute())):
        try:
            # Check if dir is inside base_dir
            dir_path.relative_to(base_path)
        except ValueError:
            continue

        while dir_path != base_path:
            parents.add(dir_path)
            dir_path = dir_path.parent

    return parents
