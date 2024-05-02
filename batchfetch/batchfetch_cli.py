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
"""Command line interface."""

import argparse
import logging
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Set

import colorama
import yaml  # type: ignore
from colorama import Fore
from schema import Optional, Or, Schema, SchemaError
from setproctitle import setproctitle

from .batchfetch_base import BatchFetchError
from .batchfetch_git import BatchFetchGit


class BatchFetchCli:
    """Command-line-interface that downloads."""

    main_key = "git"

    # TODO: Make this automatic
    empty_downloader_git = BatchFetchGit(
        data={main_key: "http://www.domain.com"},
        options={},
    )
    empty_downloader_git.validate_schema()  # Gen structure

    cfg_schema = {
        Optional("options"):
            empty_downloader_git.global_options_schema,  # type: ignore
        # TODO: Make this added automatically
        Optional("tasks"): [
            Or(str, empty_downloader_git.item_schema)
        ]
    }

    def __init__(self, max_workers: int, verbose: bool = False):
        self.cfg: dict = {}
        self.folder = Path(".")
        self.managed_filenames: Set[str] = set()
        self.verbose = verbose
        self.max_workers = max_workers
        self._logger = logging.getLogger(self.__class__.__name__)
        self.dirs_relative_to_batchfetch: Set[str] = set()

    def load(self, path: Path):
        try:
            with open(path, "r", encoding="utf-8") as fhandler:
                yaml_dict = yaml.load(fhandler, Loader=yaml.FullLoader)
                self.loads(dict(yaml_dict))
        except OSError as err:
            raise BatchFetchError(str(err)) from err

    def loads(self, data: dict):
        schema = Schema(BatchFetchCli.cfg_schema)
        try:
            schema.validate(data)
        except SchemaError as err:
            print(f"Schema error: {err}.", file=sys.stderr)
            sys.exit(1)

        self.cfg = {
            "options": {"clone_args": []},
            # TODO: Make this added automatically
            "tasks": [],
        }

        if "options" in data:
            self.cfg["options"].update(data["options"])

        # TODO: Make this automatic
        self._loads_git(data)

    def _loads_git(self, data: dict):
        if "tasks" not in data:
            return

        dict_local_dir = {}  # type: ignore
        for git_repo_raw in data["tasks"]:
            if isinstance(git_repo_raw, str):
                git_repo_raw = {BatchFetchCli.main_key: git_repo_raw}

            try:
                plugin_downloader_git = BatchFetchGit(
                    data=git_repo_raw,
                    options=self.cfg["options"],
                )
                self.cfg["tasks"].append(plugin_downloader_git)
            except SchemaError as err:
                print(f"Schema error: {err}.", file=sys.stderr)
                sys.exit(1)

            if plugin_downloader_git["path"] in dict_local_dir:
                err_str = ("more than one repository will be cloned " +
                           "to the directory '" +
                           str(plugin_downloader_git["path"]) + "' (" +
                           str(git_repo_raw[BatchFetchCli.main_key]) + " and " +
                           str(dict_local_dir[plugin_downloader_git["path"]]) +
                           ")")
                raise BatchFetchError(err_str)
            dict_local_dir[plugin_downloader_git["path"]] = \
                plugin_downloader_git[BatchFetchCli.main_key]

    def download(self) -> bool:
        failed = []
        error = False
        threads = []
        num_success = 0
        self.managed_filenames = set()

        executor_update = ThreadPoolExecutor(max_workers=self.max_workers)

        try:
            self.dirs_relative_to_batchfetch = set()

            # TODO: Make adding to all downloads automatic
            all_downloads = self.cfg["tasks"]
            for download_item in all_downloads:
                self.dirs_relative_to_batchfetch.add(str(download_item["path"]))
                if not download_item["delete"]:
                    self.managed_filenames.add(download_item["path"])
                threads.append(executor_update.submit(download_item.update))

            for future in as_completed(threads):
                data = future.result()
                if data["result"]["error"]:
                    print(Fore.RED, end="")
                elif data["result"]["changed"]:
                    print(Fore.YELLOW, end="")
                else:
                    if not self.verbose:
                        continue

                    print(Fore.GREEN, end="")

                if data["result"]["error"]:
                    error = True
                    failed.append(data)
                else:
                    num_success += 1

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
                for git_update_result in failed:
                    print("  - url:", git_update_result[BatchFetchCli.main_key])
                    print("    dir:", git_update_result["path"])
            else:
                print("Failed.")

            return False
        else:
            if num_success == 0:
                print("Already up to date.")
            else:
                print("Success.")

        return True

    # def check_managed_directories(self):
    #     # managed_downloads = {Path(item).resolve()
    #     #                      for item in self.managed_filenames}
    #     # managed_directories = {item.parent
    #     #                        for item in managed_downloads}
    #     # TODO Implement checker
    #     pass


def parse_args():
    """Parse the command line arguments."""
    desc = __doc__
    usage = "%(prog)s [--option] [args]"
    parser = argparse.ArgumentParser(description=desc,
                                     usage=usage)
    parser.add_argument(
        "-p", "--max-procs", default="3", required=False,
        help="Run up to N Number of parallel git fetch processes.",
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", default=False,
        help="Verbose mode.",
    )

    args = parser.parse_args()
    return args


def command_line_interface():
    """Command line interface."""
    errno = 0
    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                        format="%(asctime)s %(name)s: %(message)s")

    colorama.init()
    setproctitle(subprocess.list2cmdline(
        [Path(sys.argv[0]).name] + sys.argv[1:]
    ))

    args = parse_args()

    path_batchfetch_yaml = "batchfetch.yaml"
    downloader_cli = BatchFetchCli(verbose=args.verbose,
                                   max_workers=int(args.max_procs))
    downloader_cli.load(path_batchfetch_yaml)
    try:
        if not downloader_cli.download():
            errno = 1
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        errno = 1
    except BatchFetchError as err:
        print(f"Error: {err}.", file=sys.stderr)
        errno = 1
    # else:
    #     downloader_cli.check_managed_directories()

    sys.exit(errno)
