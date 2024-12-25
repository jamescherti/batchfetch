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
"""Command line interface."""

import argparse
import logging
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Set, Union

import colorama
import yaml  # type: ignore
from colorama import Fore
from schema import Optional, Or, Schema, SchemaError
from setproctitle import setproctitle

from .batchfetch_base import BatchFetchError, TaskBatchFetch
from .batchfetch_git import BatchFetchGit


class BatchFetchCli:
    """Command-line-interface that downloads."""

    def __init__(self, max_workers: int, verbose: bool, check_untracked: bool,
                 targets: List[str]):
        self._logger = logging.getLogger(self.__class__.__name__)
        self.targets = {Path(item).absolute() for item in targets}
        self.cfg: dict = {}
        self.check_untracked = check_untracked
        self.tracked_paths: Dict[Path, Set[str]] = {}
        self.ignore_untracked_paths: Set[Path] = set()
        self.verbose = verbose
        self.max_workers = max_workers
        self.dirs_relative_to_batchfetch: Set[str] = set()

        # Plugin
        self.batchfetch_schemas: Dict[Any, Any] = {}
        self.batchfetch_classes: Dict[str, TaskBatchFetch] = {}
        self.cfg_schema: Dict[Any, Any] = {}
        self._plugin_add("git", BatchFetchGit)

    def _plugin_add(self, keyword: str, batchfetch_class: Any):
        batchfetch_instance = batchfetch_class(data={},
                                               options={})
        batchfetch_instance.validate_schema()

        self.batchfetch_schemas[keyword] = batchfetch_instance.task_schema
        self.batchfetch_classes[keyword] = batchfetch_class
        self.cfg_schema = {
            Optional("options"):
                batchfetch_instance.global_options_schema,  # type: ignore
            Optional("tasks"): [
                Or(*list(self.batchfetch_schemas.values()))
            ]
        }

    def _plugin_get(self, raw_data: dict) -> str:
        keyword_found = None
        for keyword in self.batchfetch_classes:
            if keyword in raw_data:
                if keyword_found is not None:
                    err_str = (f"The keywords {keyword} and {keyword_found} "
                               f"are mutually exclusive. Error in: {raw_data}")
                    raise BatchFetchError(err_str)
                keyword_found = keyword

        if not keyword_found:
            err_str = "None of the keywords " + \
                ", ".join(self.batchfetch_classes.keys()) + \
                f" have been found in: {raw_data}"
            raise BatchFetchError(err_str)

        return keyword_found

    def load(self, path: Path):
        try:
            with open(path, "r", encoding="utf-8") as fhandler:
                yaml_dict = yaml.load(fhandler, Loader=yaml.FullLoader)
                if not isinstance(yaml_dict, dict):
                    print(f"Error: Invalid format: {yaml_dict}.",
                          file=sys.stderr)
                    sys.exit(1)

                self.ignore_untracked_paths.add(Path(path).absolute())
                self.ignore_untracked_paths.add(Path(path).resolve())
                untracked_paths = None
                if "options" in yaml_dict and \
                        "ignore_untracked_paths" in yaml_dict["options"]:
                    untracked_paths = \
                        yaml_dict["options"]["ignore_untracked_paths"]

                if isinstance(untracked_paths, str):
                    untracked_paths = [untracked_paths]

                if untracked_paths:
                    for ignore_untracked_path in untracked_paths:
                        self.ignore_untracked_paths.add(
                            Path(ignore_untracked_path).absolute()
                        )

                self._loads(dict(yaml_dict))
        except OSError as err:
            raise BatchFetchError(str(err)) from err

    def _loads(self, data: dict):
        schema = Schema(self.cfg_schema)
        try:
            schema.validate(data)
        except SchemaError as err:
            print(f"Schema error: {err}.", file=sys.stderr)
            sys.exit(1)

        self.cfg = {
            "options": {"git_clone_args": []},
            "tasks": [],
        }

        if "options" in data:
            self.cfg["options"].update(data["options"])

        self._loads_tasks(data)

    def _loads_tasks(self, data: dict):
        if "tasks" not in data:
            return

        dict_local_dir = {}  # type: ignore
        for task in data["tasks"]:
            keyword = self._plugin_get(task)
            batchfetch_class = self.batchfetch_classes[keyword]

            try:
                batchfetch_instance = batchfetch_class(  # type: ignore
                    data=task,
                    options=self.cfg["options"],
                )
                self.cfg["tasks"].append(batchfetch_instance)
            except SchemaError as err:
                print(f"Schema error: {err}.", file=sys.stderr)
                sys.exit(1)

            dest_path = Path(batchfetch_instance["path"]).absolute()
            dest_path2 = Path(batchfetch_instance["path"]).resolve()
            if str(dest_path) in dict_local_dir \
                    or str(dest_path2) in dict_local_dir:
                err_str = ("More than one task have the " +
                           f"destination path (" +
                           str(task[keyword]) + " and " +
                           str(dict_local_dir[(str(dest_path))]) +
                           ")")
                raise BatchFetchError(err_str)

            dict_local_dir[str(dest_path)] = batchfetch_instance[keyword]

    def run_tasks(self) -> bool:
        failed = []
        error = False
        threads = []
        num_success = 0
        self.tracked_paths = {}

        executor_update = ThreadPoolExecutor(max_workers=self.max_workers)

        try:
            self.dirs_relative_to_batchfetch = set()

            all_tasks = self.cfg["tasks"]

            # Check targets
            if self.targets:
                targets_executed = set()
                for task in all_tasks:
                    full_path = Path(task["path"]).absolute()
                    if full_path not in self.targets:
                        continue

                    targets_executed.add(full_path)

                targets_not_found = self.targets - targets_executed
                if targets_not_found:
                    err_str = \
                        f"Error: Target(s) not found: "
                    err_str += ", ".join([str(item)
                                         for item in targets_not_found])
                    print(f"Error: {err_str}", file=sys.stderr)
                    sys.exit(1)

            for task in all_tasks:
                full_path = Path(task["path"]).absolute()

                self.dirs_relative_to_batchfetch.add(str(task["path"]))
                if not task["delete"]:
                    base_path = full_path.parent
                    try:
                        self.tracked_paths[base_path]
                    except KeyError:
                        self.tracked_paths[base_path] = set()

                    self.tracked_paths[base_path].add(full_path.name)

                if self.targets and full_path not in self.targets:
                    continue
                threads.append(executor_update.submit(task.update))

            for future in as_completed(threads):
                data = future.result()
                if data["result"]["error"]:
                    error = True
                    failed.append(data)
                else:
                    num_success += 1

                if (not self.verbose and
                    not data["result"]["error"] and
                        not data["result"]["changed"]):
                    continue

                if data["result"]["error"]:
                    print(Fore.RED, end="")
                elif data["result"]["changed"]:
                    print(Fore.YELLOW, end="")
                else:
                    print(Fore.GREEN, end="")

                if data["result"]["output"]:
                    print(data["result"]["output"].rstrip("\n"))

                print(Fore.RESET, end="")
                print()
        except KeyboardInterrupt:
            error = True
            executor_update.shutdown(cancel_futures=True)  # type: ignore

        if error:
            if failed:
                print("Failed:")
                for failed_result in failed:
                    print("  -", failed_result["path"])
            else:
                print("Failed.")

            return False
        else:
            if self.check_untracked:
                self._find_untracked_paths()

            if num_success == 0:
                print("Nothing to do.")
            elif not self.verbose:
                print("Success.")

        return True

    def _find_untracked_paths(self):
        "Find the files that are untracked and should be deleted."
        untracked_paths = set()
        for tracked_dir, tracked_filenames in self.tracked_paths.items():
            actual_filenames = {file.name for file in tracked_dir.iterdir()}
            for filename in actual_filenames - tracked_filenames:
                full_path = tracked_dir / filename
                if full_path in self.ignore_untracked_paths:
                    continue

                untracked_paths.add(full_path)

        if untracked_paths:
            err_str = "The following files need to be deleted:\n"
            for path in untracked_paths:
                err_str += ("  - " +
                            str(path) +
                            ("/" if path.is_dir() else "") +
                            "\n")
            err_str += ("The paths above are not managed by batchfetch."
                        " To retain them, add them to the "
                        "options.ignore_untracked_paths list, using either "
                        "relative or absolute paths")
            raise BatchFetchError(err_str)


def parse_args():
    """Parse the command line arguments."""
    # Batchfetch file
    try:
        batchfetch_file = os.environ["BATCHFETCH_FILE"]
    except KeyError:
        batchfetch_file = None

    # Jobs
    try:
        jobs = os.environ["BATCHFETCH_JOBS"]
    except KeyError:
        jobs = 5
    else:
        if jobs:
            jobs = int(jobs)

    # Check untracked
    try:
        check_untracked = os.environ["BATCHFETCH_CHECK_UNTRACKED"]
    except KeyError:
        check_untracked = False
    else:
        check_untracked = bool(check_untracked)

    desc = "Efficiently clone/pull multiple Git repositories in parallel."
    usage = "%(prog)s [--option] [TARGET]"
    parser = argparse.ArgumentParser(description=desc, usage=usage)

    parser.add_argument(
        "targets", metavar="target", type=str, nargs="*",
        help=("This is a target path that batchfetch is supposed to handle. "
              "When no target is specified, execute the tasks of all target "
              "paths defined in the batchfetch.yml list of tasks."),
    )

    parser.add_argument(
        "-f",
        "--file",
        default=batchfetch_file,
        required=False,
        help=("Specify the batchfetch YAML file "
              "(default: './batchfetch.yaml')."
              "Alternatively, the BATCHFETCH_FILE environment variable can be "
              "used to configure the number of jobs."),
    )

    parser.add_argument(
        "-C",
        "--directory",
        default=None,
        required=False,
        help=("Change the working directory before reading the "
              "batchfetch.yaml file. If not specified, the directory is "
              "set to the parent directory of the batchfetch.yaml file.")
    )

    parser.add_argument(
        "-j",
        "--jobs",
        default=jobs,
        type=int,
        required=False,
        help=("Run up to N parallel processes (default: 5). "
              "Alternatively, the BATCHFETCH_JOBS environment variable can be "
              "used to configure the number of jobs."))

    parser.add_argument(
        "-v", "--verbose", action="store_true", default=False,
        help="Enable verbose mode.",
    )

    parser.add_argument(
        "-u",
        "--check-untracked",
        default=check_untracked,
        action="store_true",
        required=False,
        help=("Abort if untracked files or directories exist. "
              "Alternatively, set the BATCHFETCH_CHECK_UNTRACKED=1 "
              "environment variable to enable this check."))

    args = parser.parse_args()

    if not args.file:
        args.file = "./batchfetch.yaml"

    if not Path(args.file).is_file():
        print(f"Error: File not found: {args.file}",
              file=sys.stderr)
        sys.exit(1)

    return args


def command_line_interface():
    """Command line interface."""
    try:
        errno = 0
        logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                            format="%(asctime)s %(name)s: %(message)s")

        colorama.init()
        setproctitle(subprocess.list2cmdline([Path(sys.argv[0]).name] +
                                             sys.argv[1:]))

        args = parse_args()
        done = []
        file = Path(args.file).absolute()
        file_resolved = file.absolute()
        if not file_resolved:
            print(f"Error: cannot resolve the path {file}",
                  file=sys.stderr)
            sys.exit(1)

        done.append(file_resolved)

        args.directory = args.directory if args.directory else file.parent
        if args.verbose and args.jobs:
            print(f"[FILE] {file}")
            print(f"[DIR] {args.directory}")
            print(f"[JOBS] {args.jobs}")
            print(f"[CHECK UNTRACKED] {args.check_untracked}")
            print()

        os.chdir(args.directory)
        batchfetch_cli = BatchFetchCli(verbose=args.verbose,
                                       max_workers=args.jobs,
                                       check_untracked=args.check_untracked,
                                       targets=args.targets)
        batchfetch_cli.load(file)

        try:
            if not batchfetch_cli.run_tasks():
                errno = 1
        except KeyboardInterrupt:
            print("Interrupted.", file=sys.stderr)
            errno = 1
        except BatchFetchError as err:
            print(f"Error: {err}.", file=sys.stderr)
            errno = 1

        sys.exit(errno)
    except BrokenPipeError:
        sys.exit(1)
