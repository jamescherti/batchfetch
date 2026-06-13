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
"""Base class used to run tasks in parallel."""

from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path
from typing import Any

from schema import Optional, Or, Schema

from .helpers import run_indent_str


class BatchFetchError(Exception):
    """Exception raised by batchfetch functions."""


class DataAlreadyInitialized(Exception):
    """Data already initialized."""


class TaskBase:
    """Base class representing a general task to be executed."""

    def __init__(self, data: dict[str, Any], options: dict[str, Any]) -> None:
        """Initialize the task with specific data and options."""
        self.global_options_schema: dict[Any, Any] = {}
        self.global_options_values: dict[str, Any] = options

        self.task_schema: dict[Any, Any] = {}
        self.task_default_values: dict[str, Any] = {}

        self._item_values = data

        # Variables
        self.values: dict[str, Any] = {}
        self.options: dict[str, Any] = {}
        self._values_initialized = False

    def _initialize_data(self) -> None:
        """Initialize the options and data values for the task."""
        if self._values_initialized:
            raise DataAlreadyInitialized

        # Options
        self.options = {}
        self.options.update(deepcopy(self.global_options_values))

        schema = Schema(self.global_options_schema)
        schema.validate(self.options)

        # Data
        self.values = {}
        self.values.update(deepcopy(self.task_default_values))
        self.values.update(deepcopy(self.options))
        self.values.update(deepcopy(self._item_values))
        schema = Schema(self.task_schema)
        schema.validate(self.values)

        self.values["result"] = {
            "output": "",
            "error": False,
            "changed": False,
        }

    def validate_schema(self) -> None:
        """Validate the schema of the task data and options."""
        self._initialize_data()

    def __getitem__(self, key: str) -> Any:
        """Retrieve an item from the task values or options."""
        self._initialize_data()

        if key in self.values:
            return self.values[key]

        if key in self.options:
            return self.options[key]

        raise KeyError(f"The item '{key}' was not found in '{self.values}'")


class TaskBatchFetch(TaskBase):
    """Plugin downloader base class."""

    def __init__(self, data: dict[str, Any], options: dict[str, Any]) -> None:
        """Initialize the batchfetch task plugin."""
        new_options: dict[str, Any] = {"exec_before": [],
                                       "exec_after": [],
                                       "ignore_untracked": []}
        new_options.update(options)
        options = new_options

        super().__init__(data=data, options=options)
        self.indent = 4
        self.indent_spaces = " " * self.indent
        self.env = os.environ.copy()

        # Default
        self.global_options_schema: dict[Any, Any] = {
            Optional("exec_before"): Or([str], str),
            Optional("exec_after"): Or([str], str),
            Optional("ignore_untracked"): Or([str], str),
        }

        self.task_schema: dict[Any, Any] = {
            Optional("path"): str,
            Optional("delete"): bool,

            Optional("exec_before"): Or([str], str),
            Optional("exec_after"): Or([str], str),

            # Global options (unused locally)
            Optional("ignore_untracked"): Or([str], str),
        }

        self.task_default_values: dict[str, Any] = {
            # Optional items
            "delete": False,
        }

    def _initialize_data(self) -> None:
        """Safely initialize data for the batchfetch task."""
        try:
            super()._initialize_data()
        except DataAlreadyInitialized:
            return

        # Mark values as initialized
        self._values_initialized = True

    def _local_task_exec(self, *args: Any, **kwargs: Any) -> None:
        """Execute a local task command and capture its output."""
        stdout = run_indent_str(env=self.env, spaces=self.indent,
                                *args, **kwargs)
        if not stdout.endswith("\n"):
            stdout += "\n"
        self.add_output(stdout)

    def _exec_before(self, cwd: os.PathLike = Path(".")) -> None:
        """Execute pre-task commands defined in options and task items."""
        self._initialize_data()
        if self["delete"]:
            return

        # Global
        cmd = self.global_options_values["exec_before"] \
            if "exec_before" in self.global_options_values else None
        if cmd:
            self._local_task_exec(cmd, cwd=str(cwd))

        # Local
        cmd = self._item_values["exec_before"] if "exec_before" \
            in self._item_values else None
        if cmd:
            self._local_task_exec(cmd, cwd=str(cwd))

    def _exec_after(self, cwd: os.PathLike = Path(".")) -> None:
        """Execute post-task commands if the task was changed successfully."""
        self._initialize_data()
        if self["delete"] or self.is_error() or not self.is_changed():
            return

        # Local
        cmd = self.global_options_values["exec_after"] \
            if "exec_after" in self.global_options_values else None
        if cmd:
            self._local_task_exec(cmd, cwd=str(cwd))

        # Local
        cmd = self._item_values["exec_after"] if "exec_after" \
            in self._item_values else None
        if cmd:
            self._local_task_exec(cmd, cwd=str(cwd))

    def is_changed(self) -> bool:
        """Return True if the task execution resulted in changes."""
        self._initialize_data()
        return bool(self.values["result"]["changed"])

    def set_changed(self, changed: bool) -> None:
        """Set the changed status of the task."""
        self._initialize_data()
        self.values["result"]["changed"] = changed

    def get_changed(self) -> bool:
        """Return the changed status of the task without initializing data."""
        try:
            return bool(self.values["result"]["changed"])
        except KeyError:
            return False

    def is_error(self) -> bool:
        """Return True if the task encountered an error."""
        self._initialize_data()
        return bool(self.values["result"]["error"])

    def set_error(self, error: bool) -> None:
        """Set the error status of the task."""
        self._initialize_data()
        self.values["result"]["error"] = error

    def set_output(self, output: str) -> None:
        """Set the output string of the task."""
        self._initialize_data()
        self.values["result"]["output"] = output

    def add_output(self, output: str) -> None:
        """Append a string to the output of the task."""
        self._initialize_data()
        self.values["result"]["output"] += output

    def get_output(self) -> str:
        """Return the output."""
        self._initialize_data()
        return str(self.values["result"]["output"])

    def update(self) -> dict[str, Any]:
        """Update the task data and return the current values."""
        self._initialize_data()
        return self.values
