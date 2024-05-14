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

        self.item_schema: Dict[Any, Any] = {}
        self.item_default_values: Dict[str, Any] = {}

        self._item_values = data
        self._item_global_options = options

        # Variables
        self.values: Dict[str, Any] = {}
        self.options: Dict[str, Any] = {}
        self._values_initialized = False

    def _initialize_data(self):
        if self._values_initialized:
            raise DataAlreadyInitialized

        # Options
        self.options = {}
        self.options.update(deepcopy(self._item_global_options))
        schema = Schema(self.global_options_schema)
        schema.validate(self.options)

        # Data
        self.values = {}
        self.values.update(deepcopy(self.item_default_values))
        self.values.update(deepcopy(self._item_values))
        # self.values.update(deepcopy(self._item_global_options))
        schema = Schema(self.item_schema)
        schema.validate(self.values)

        # Strip spaces
        self.values = {
            key: value.strip() if isinstance(value, str) else value
            for key, value in self.values.items()
        }

        self.values["result"] = {
            "output": "",
            "error": False,
            "changed": False,
        }

    def update(self):
        self._initialize_data()
        return self.values

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


class BatchFetchBase(TaskBase):
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
        }

        self.item_schema: Dict[Any, Any] = {
            Optional("path"): str,
            Optional("delete"): bool,

            Optional("exec_before"): Or([str], str),
            Optional("exec_after"): Or([str], str),
        }

        self.global_options_values: Dict[str, Any] = {
            "exec_before": [],
            "exec_after": [],
        }

        self.item_default_values: Dict[str, Any] = {
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

    def _run(self, *args, **kwargs):
        stdout = run_indent_str(*args, **kwargs)

        if not stdout.endswith("\n"):
            stdout += "\n"
        self.add_output(stdout)

    def _run_pre_exec(self, cwd: os.PathLike = Path(".")):
        self._initialize_data()
        for pre_exec in self["exec_before"]:
            if not pre_exec:
                continue

            self._run(pre_exec, cwd=str(cwd), env=self.env,
                      spaces=self.indent)

    def _run_post_exec(self, cwd: os.PathLike = Path(".")):
        self._initialize_data()
        if self["delete"] or not self.is_changed():
            return

        for post_exec in self["exec_after"]:
            if not post_exec:
                continue

            self._run(post_exec, cwd=str(cwd), env=self.env,
                      spaces=self.indent)

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
        self._initialize_data()
        return str(self.values["result"]["output"])
