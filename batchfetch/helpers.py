#!/usr/bin/env python
#
# Copyright (C) 2024 James Cherti
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
"Batchfetch helper functions."

import hashlib
import os
import shlex
from subprocess import PIPE, CalledProcessError, Popen, list2cmdline
from typing import List, Tuple, Union


def md5sum(filename: os.PathLike):
    """
    Calculate and return the MD5 checksum of a file.

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


def run_simple(cmd: Union[List[str], str],
               **kwargs) -> Tuple[List[str], List[str]]:
    """
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


def run_indent_str(cmd: Union[List[str], str], **kwargs) -> str:
    """
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


def indent_raw_output(raw_output: List[str], spaces: int = 4) -> List[str]:
    """
    Indents each line of the given list of strings.

    :param raw_output: List of strings to indent.
    :param spaces: Number of spaces to indent each line.
    :return: A new list of strings with each line indented as specified.
    """
    indentation = ' ' * spaces
    return [indentation + line for line in raw_output]


def run_indent(cmd: Union[List[str], str], spaces: int = 4,
               **kwargs) -> Tuple[List[str], List[str]]:
    """
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
