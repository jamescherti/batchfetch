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
"Base class used to run tasks in parallel."

import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

from schema import Optional, Or, Schema

from .helpers import run_indent_str


class BatchFetchError(Exception):
    """Exception raised by Downloader()."""


class DataAlreadyInitialized(Exception):
    """Data already initialized."""


class TaskBase:
    def __init__(self, data: Dict[str, Any], options: Dict[str, Any]):
        self.global_options_schema: Dict[Any, Any] = {}
        self.global_options_values: Dict[str, Any] = {}

        self.task_schema: Dict[Any, Any] = {}
        self.task_default_values: Dict[str, Any] = {}

        self._item_values = data
        self._item_options = options

        # Variables
        self.values: Dict[str, Any] = {}
        self.options: Dict[str, Any] = {}
        self._values_initialized = False

    def _initialize_data(self):
        if self._values_initialized:
            raise DataAlreadyInitialized

        # Options
        self.options = {}
        self.options.update(deepcopy(self.global_options_values))
        self.options.update(deepcopy(self._item_options))
        schema = Schema(self.global_options_schema)
        schema.validate(self.options)

        # Data
        self.values = {}
        self.values.update(deepcopy(self.task_default_values))
        self.values.update(deepcopy(self._item_values))
        schema = Schema(self.task_schema)
        schema.validate(self.values)

        self.values["result"] = {
            "output": "",
            "error": False,
            "changed": False,
        }

    def validate_schema(self):
        self._initialize_data()

    def __getitem__(self, key):
        self._initialize_data()

        if key in self.values:
            return self.values[key]

        if key in self.options:
            return self.options[key]

        if key in self.global_options_values:
            return self.global_options_values[key]

        raise KeyError(f"The item '{key}' was not found in '{self.values}")


class TaskBatchFetch(TaskBase):
    """Plugin downloader base class."""

    def __init__(self, data: Dict[str, Any], options: Dict[str, Any]):
        super().__init__(data=data, options=options)
        self.indent = 4
        self.indent_spaces = " " * self.indent
        self.env = os.environ.copy()

        # Default
        self.global_options_schema: Dict[Any, Any] = {
            Optional("exec_before"): Or([str], str),
            Optional("exec_after"): Or([str], str),
            Optional("ignore_untracked_paths"): Or([str], str),
        }

        self.task_schema: Dict[Any, Any] = {
            Optional("path"): str,
            Optional("delete"): bool,

            Optional("exec_before"): Or([str], str),
            Optional("exec_after"): Or([str], str),
        }

        self.global_options_values: Dict[str, Any] = {
            "exec_before": [],
            "exec_after": [],
            "ignore_untracked_paths": [],
        }

        self.task_default_values: Dict[str, Any] = {
            # Optional items
            "delete": False,
        }

    def _initialize_data(self):
        try:
            super()._initialize_data()
        except DataAlreadyInitialized:
            return

        # Mark values as initialized
        self._values_initialized = True

    def _local_task_exec(self, *args, **kwargs):
        stdout = run_indent_str(env=self.env, spaces=self.indent,
                                *args, **kwargs)
        if not stdout.endswith("\n"):
            stdout += "\n"
        self.add_output(stdout)

    def _exec_before(self, cwd: os.PathLike = Path(".")):
        self._initialize_data()
        if self["delete"]:
            return

        # Global
        cmd = self.options["exec_before"] \
            if "exec_before" in self.options else None
        if cmd:
            self._local_task_exec(cmd, cwd=str(cwd))

        # Local
        cmd = self["exec_before"]
        if cmd:
            self._local_task_exec(cmd, cwd=str(cwd))

    def _exec_after(self, cwd: os.PathLike = Path(".")):
        self._initialize_data()
        if self["delete"] or not self.is_changed():
            return

        # Local
        cmd = self.options["exec_after"] \
            if "exec_after" in self.options else None
        if cmd:
            self._local_task_exec(cmd, cwd=str(cwd))

        # Local
        cmd = self["exec_after"]
        if cmd:
            self._local_task_exec(cmd, cwd=str(cwd))

    def is_changed(self) -> bool:
        self._initialize_data()
        return bool(self.values["result"]["changed"])

    def set_changed(self, changed: bool):
        self._initialize_data()
        self.values["result"]["changed"] = changed

    def get_changed(self) -> bool:
        try:
            return bool(self.values["result"]["changed"])
        except KeyError:
            return False

    def is_error(self) -> bool:
        self._initialize_data()
        return bool(self.values["result"]["error"])

    def set_error(self, error: bool):
        self._initialize_data()
        self.values["result"]["error"] = error

    def set_output(self, output: str):
        self._initialize_data()
        self.values["result"]["output"] = output

    def add_output(self, output: str):
        self._initialize_data()
        self.values["result"]["output"] += output

    def get_output(self) -> str:
        """Return the output."""
        self._initialize_data()
        return str(self.values["result"]["output"])

    def update(self):
        self._initialize_data()
        return self.values
