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
"Clone and update Git repositories."


import posixpath
import shutil
import subprocess
import textwrap
from pathlib import Path
from typing import List, Union

from schema import Optional

from .batchfetch_base import (BatchFetchBase, BatchFetchError,
                              GitBranchDoesNotExist)
from .helpers import run_simple


class BatchFetchGit(BatchFetchBase):
    """Clone or update a Git repository."""

    indent_spaces = " " * BatchFetchBase.indent
    main_key = "git"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Schema
        self.item_schema.update({
            # Local options
            BatchFetchGit.main_key: str,
            Optional("branch"): str,

            # Same as global options
            Optional("clone_args"): [str],
            Optional("git_pull"): bool,
        })

        self.global_options_schema.update({
            # Global options
            Optional("clone_args"): [str],
            Optional("git_pull"): bool,
        })

        # Data
        self.global_options_values.update({"clone_args": [],
                                           "git_pull": True})

        self.item_default_values.update({
            BatchFetchGit.main_key: "",
            "branch": "",
            "delete": False,
        })

        self.git_local_dir = Path(self["path"])
        self.current_branch = None
        self.current_commit_ref = None

    def _initialize_data(self):
        super()._initialize_data()

        self.values[BatchFetchGit.main_key] = \
            self.values[BatchFetchGit.main_key].rstrip("/")

        if "path" not in self.values:
            self.values["path"] = \
                posixpath.basename(
                    self.values[BatchFetchGit.main_key])  # type: ignore

    def _git_ref(self, cwd: Union[None, Path] = None) -> str:
        """Get the commit reference of HEAD."""
        cmd = "git show-ref --head --verify HEAD"
        try:
            stdout, _ = run_simple(cmd, cwd=cwd, env=self.env)
            output = stdout[0].split(" ")[0]
        except IndexError:
            return ""
        return output

    def update(self):
        """Clone or update a Git repository."""
        super().update()

        is_clone = False

        if not self.git_local_dir.exists():
            is_clone = True

        # Result (string)
        if self["delete"]:
            update_type = "DELETE"
        elif is_clone:
            update_type = "CLONE"
        else:
            update_type = "UPDATE"

        self.add_output(
            f"[GIT {update_type}] {self[self.main_key]}" +
            (f" (branch: {self['branch']})"
             if self["branch"] else "") + "\n"
        )

        try:
            # Delete
            if self["delete"]:
                self._repo_delete()
            # Clone
            elif is_clone:
                self._repo_clone()

            # Update
            if self.git_local_dir.is_dir():
                # Pre exec
                self._run_pre_exec(cwd=self.git_local_dir)

                self._repo_check_remote_origin()
                self._update_current_branch()
                self._repo_reset()

                git_merge_done = self._repo_pull()
                git_branch_changed = self._repo_fix_branch()
                if git_merge_done or git_branch_changed:
                    self._repo_update_submodules()

                if self.get_changed():
                    self._run_post_exec(cwd=self.git_local_dir)
        except BatchFetchError as err:
            self.set_error(True)
            self.add_output(self.indent_spaces + "[ERROR] " + str(err) + "\n")
        except subprocess.CalledProcessError as err:
            self.set_error(True)
            self.add_output(self.indent_spaces + "[ERROR] " + str(err) + "\n")
            self.add_output(self.indent_spaces +
                            textwrap.indent(err.stdout, " " * self.indent) +
                            "\n" +
                            textwrap.indent(err.stderr, " " * self.indent))

        if not self.is_error() and not self.is_changed():
            self.add_output(self.indent_spaces + "# Already up to date\n")

        return self.values

    def _update_current_branch(self):
        try:
            self.current_branch, _ = run_simple(
                ["git", "symbolic-ref", "--short", "HEAD"],
                env=self.env,
                cwd=self.git_local_dir,
            )
        except subprocess.CalledProcessError:
            # Not a symbolic ref
            self.current_branch = None

    def _repo_delete(self):
        if not self.git_local_dir.exists():
            self.add_output(self.indent_spaces + "# Already deleted\n")
        elif not self.git_local_dir.joinpath(".git").is_dir():
            self.add_output(
                self.indent_spaces +
                f"# Cannot be deleted because '{self.git_local_dir}' is "
                "not a Git repository\n"
            )
            self.set_error(True)
        elif self.git_local_dir.is_dir():
            shutil.rmtree(str(self.git_local_dir))
            self.add_output(self.indent_spaces +
                            f"# Deleted: '{self.git_local_dir}'")
            self.set_changed(True)

    def _repo_clone(self):
        git_clone_args = self["clone_args"]
        git_clone_args += ["--recurse-submodules"]

        cmd = ["git", "clone"] + git_clone_args + \
            [self[BatchFetchGit.main_key], str(self.git_local_dir)]
        self._run(cmd, env=self.env)
        self.set_changed(True)

    def _repo_reset(self):
        # Remove local changes
        cmd = ["git", "reset", "--hard", "HEAD"]
        self._run(cmd, cwd=str(self.git_local_dir), env=self.env)

    def _repo_pull(self):
        git_merge = False

        # Merge
        ignore_git_pull = False
        if not self["git_pull"]:
            ignore_git_pull = True
        elif self["branch"]:
            # Check if the new branch exists
            try:
                self._git_tags(self["branch"])
            except GitBranchDoesNotExist:
                ignore_git_pull = False
            else:
                # The branch exists
                ignore_git_pull = True

            # Check if the new branch is different from the current one
            commit_ref = self._git_ref(cwd=self.git_local_dir)
            if self.current_branch and (commit_ref == self["branch"] or
                                        self.current_branch == self["branch"]):
                ignore_git_pull = True

        if ignore_git_pull:
            self.add_output(self.indent_spaces +
                            "# git pull ignored\n")
        else:
            cmd = ["git", "fetch", "origin"]
            self._run(cmd, cwd=str(self.git_local_dir), env=self.env)

            # TODO: only merge when difference from upstream
            commit_ref = self._git_ref(cwd=self.git_local_dir)
            self._run(["git", "merge", "--ff-only"],
                      cwd=str(self.git_local_dir), env=self.env)
            git_ref_after_merge = self._git_ref(cwd=self.git_local_dir)
            if commit_ref != git_ref_after_merge:
                git_merge = True
                self.set_changed(True)
                self._run(["git", "log",
                           '--pretty=format:"%h %ad %s [%cn]"',
                           "--decorate", "--date=short",
                           f"{commit_ref}..{git_ref_after_merge}"],
                          cwd=str(self.git_local_dir),
                          env=self.env)

        return git_merge

    def _git_tags(self, branch: str) -> List[str]:
        stdout: List[str] = []
        try:
            stdout, _ = run_simple(
                ["git", "rev-parse", "--verify", branch],
                env=self.env,
                cwd=self.git_local_dir)
        except subprocess.CalledProcessError as err:
            raise GitBranchDoesNotExist(
                f"The branch '{branch}' does not exist.") from err

        return stdout

    def _repo_fix_branch(self) -> bool:
        git_ref_after_merge = self._git_ref(cwd=self.git_local_dir)
        branch_changed = False
        if self["branch"]:
            # We also need tags because sometimes, a branch
            # returns a different commit reference
            git_tags, _ = run_simple(
                ["git", "tag", "--points-at", "HEAD"],
                env=self.env,
                cwd=self.git_local_dir,
            )

            # Also check the commit reference in case
            # branch is a commit reference instead of a tag
            try:
                git_ref_branch = self._git_tags(self["branch"])[0]
            except GitBranchDoesNotExist as err:
                raise BatchFetchError(f"The branch '{self['branch']}' "
                                      "does not exist.") from err

            if git_ref_after_merge != git_ref_branch and \
                    self["branch"] not in git_tags:
                # Update the branch
                self._run(["git", "checkout"] + [self["branch"]],
                          cwd=str(self.git_local_dir), env=self.env)
                self.add_output(self.indent_spaces + "# Branch changed to " +
                                self["branch"] + "\n")
                self.set_changed(True)
                branch_changed = True

                # Read branch again
                self._update_current_branch()

        return branch_changed

    def _repo_update_submodules(self):
        # This parameter instructs Git to initiate the update
        # process for submodules:
        # 1. Git fetches the commits specified in the parent
        # repository's configuration for each submodule.
        # 2. Updates are based solely on the commit pointers stored
        # within the parent repository's submodule configuration.
        # 3. It does not directly consult the upstream repositories
        # of the submodules.
        # 4. Submodules are updated to reflect the exact commits
        # referenced in the parent repository's configuration,
        # potentially lagging behind the latest changes made in the
        # upstream repositories.
        if self.git_local_dir.joinpath(".gitmodules").is_file():
            cmd = ["git", "submodule", "update", "--recursive"]
            self._run(cmd, cwd=str(self.git_local_dir), env=self.env)

    def _repo_check_remote_origin(self):
        cmd = ["git", "config", "remote.origin.url"]
        try:
            stdout, _ = run_simple(cmd,
                                   env=self.env,
                                   cwd=self.git_local_dir)
            origin_url = stdout[0]
        except IndexError:
            origin_url = ""

        if origin_url != self[BatchFetchGit.main_key]:
            self.set_error(True)
            self.add_output(
                self.indent_spaces +
                "[ERROR] The Git remote origin URL is incorrect: "
                f"'{origin_url}' (It is supposed to "
                f"be '{self[self.main_key]}')\n")
            raise BatchFetchError
