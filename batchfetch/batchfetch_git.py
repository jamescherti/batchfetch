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
"Clone and update Git repositories."

import os
import posixpath
import shutil
import subprocess
import textwrap
from pathlib import Path
from typing import List, Tuple, Union

from schema import Optional

from .batchfetch_base import BatchFetchError, TaskBatchFetch
from .helpers import run_simple


class GitRevisionDoesNotExist(Exception):
    """The Git revision does not exist."""


class GitRemoteError(Exception):
    """The git remote does not exist."""


class BatchFetchGit(TaskBatchFetch):
    """Clone or update a Git repository."""

    def __init__(self, *args, **kwargs):
        self._git_fetch_origin_done = False

        self.branch_commit_ref = None
        self.is_branch = False

        super().__init__(*args, **kwargs)
        self.env["GIT_TERMINAL_PROMPT"] = "0"
        self.env["GIT_PAGER"] = ""
        self.main_key = "git"

        # Schema
        self.task_schema.update({
            # Local options
            self.main_key: str,
            Optional("revision"): str,

            # Same as global options
            Optional("git_clone_args"): [str],
            Optional("git_pull"): bool,
        })

        self.global_options_schema.update({
            # Global options
            Optional("git_clone_args"): [str],
            Optional("git_pull"): bool,
        })

        # Data
        self.global_options_values.update({"git_clone_args": [],
                                           "git_pull": True})

        self.task_default_values.update({
            self.main_key: "",
            "revision": "",
            "delete": False,
        })

        self.git_local_dir = Path(self["path"])
        self.current_branch = None
        self.current_commit_ref = None

    def _initialize_data(self):
        super()._initialize_data()

        self.values[self.main_key] = \
            self.values[self.main_key].rstrip("/")

        if "path" not in self.values:
            path = \
                posixpath.basename(self.values[self.main_key])  # type: ignore
            # Remove .git from the file name
            if path.endswith(".git"):
                path = path[:-4]
            self.values["path"] = path

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

        self.add_output(f"[GIT {update_type}] {self[self.main_key]}"
                        + (f" (Ref: {self['revision']})"
                           if self["revision"] else "") + "\n")

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
                self._update_current_branch_name()
                self._repo_fix_remote_origin()
                self._exec_before(cwd=self.git_local_dir)

                if not self["revision"]:
                    self.values["revision"] = self._run_get_firstline(
                        "git symbolic-ref refs/remotes/origin/HEAD"
                    ).split("/")[-1]
                    if not self["revision"]:
                        raise BatchFetchError(
                            "Unable to determine the default origin branch"
                        )

                    self.add_output(self.indent_spaces +
                                    f"[INFO] Update revision to: '" +
                                    self["revision"] + "'\n")

                git_fetch_done = self._repo_fetch()

                git_branch_changed = False
                git_branch_changed = self._repo_fix_branch()

                git_merge_done = False
                if git_fetch_done:
                    git_merge_done = self._git_merge()

                if self.get_changed():
                    self._exec_after(cwd=self.git_local_dir)
        except BatchFetchError as err:
            self.set_error(True)
            self.add_output(self.indent_spaces + "[ERROR] " + str(err) + "\n")
        except subprocess.CalledProcessError as err:
            self.set_error(True)
            self.add_output(self.indent_spaces + "[ERROR] " + str(err) + "\n")
            self.add_output(self.indent_spaces
                            + textwrap.indent(err.stdout, " " * self.indent)
                            + "\n"
                            + textwrap.indent(err.stderr, " " * self.indent))

        if not self.is_error() and not self.is_changed():
            self.add_output(self.indent_spaces + "[INFO] Nothing to do.\n")

        return self.values

    def _run_get_firstline(self, *args, **kwargs):
        stdout, _ = self._run(*args, **kwargs)
        try:
            return stdout[0]
        except IndexError:
            return ""

    def _run(self, cmd: Union[List[str], str],
             cwd: Union[None, os.PathLike] = None,
             env: Union[None, dict] = None,
             **kwargs) -> Tuple[List[str], List[str]]:
        """
        Executes a command and returns stdout and stderr as separate lists of
        strings.

        :param cmd: Command to be executed. Can be a list or a string.
        :param kwargs: Additional keyword arguments for Popen.
        :return: Tuple containing two lists: stdout lines and stderr lines.
        """
        if not cwd:
            cwd = self.git_local_dir
        if not env:
            env = self.env
        return run_simple(cmd=cmd, env=env, cwd=cwd, **kwargs)

    def _git_ref(self, cwd: Union[None, Path] = None) -> str:
        """Get the commit revision of HEAD.

        The command will fail if the branch is detached.
        """
        cmd = ["git", "show-ref", "--head", "--verify", "HEAD"]
        try:
            stdout, _ = self._run(cmd, cwd=cwd)
            output = stdout[0].split(" ")[0]
        except IndexError:
            return ""
        return output

    def _update_current_branch_name(self):
        try:
            # This returns the branch name
            stdout, _ = self._run(["git", "symbolic-ref", "--short", "HEAD"])
            self.current_branch = stdout[0]
            self.is_branch = True
        except (IndexError, subprocess.CalledProcessError):
            # Not a symbolic ref
            self.current_branch = None

        if self.current_branch:
            try:
                # If the tag is annotated, it points to a tag object, not
                # directly to a commit. You need to resolve it to the
                # commit it points to. Using `git rev-parse
                # <tagname>^{commit}` allows getting the right revision.
                commit_ref = self._git_rev_parse_verify(self["revision"]
                                                        + "^{commit}")[0]
                self.branch_commit_ref = commit_ref.strip()
            except GitRevisionDoesNotExist:
                pass

    def _repo_delete(self):
        if not self.git_local_dir.exists():
            self.add_output(self.indent_spaces + "[INFO] Already deleted\n")
        elif not self.git_local_dir.joinpath(".git").is_dir():
            self.add_output(
                self.indent_spaces
                + f"# Cannot be deleted because '{self.git_local_dir}' is "
                "not a Git repository\n"
            )
            self.set_error(True)
        elif self.git_local_dir.is_dir():
            shutil.rmtree(str(self.git_local_dir))
            self.add_output(self.indent_spaces
                            + f"[INFO] Deleted: '{self.git_local_dir}'")
            self.set_changed(True)

    def _repo_clone(self):
        git_clone_args = self["git_clone_args"]
        # git_clone_args += ["--recurse-submodules"]

        cmd = ["git", "clone"] + git_clone_args + \
            [self[self.main_key], str(self.git_local_dir)]
        self._run(cmd, cwd=".")
        self.set_changed(True)

    def _repo_fetch(self):
        # Merge
        do_git_fetch = self["git_pull"]
        do_git_fetch = False
        commit_ref = None

        try:
            # Check if the revision such as
            stdout, _ = self._run(["git", "cat-file", "-e", self["revision"]])
        except subprocess.CalledProcessError:
            do_git_fetch = True
            self.add_output(
                self.indent_spaces
                + "[INFO] Git fetch origin reason: "
                + f"The revision does not exist: {self['revision']}"
                + "\n")

        # The revision exists, but if it a branch, git pull anyway
        if not do_git_fetch:
            try:
                # Check if the branch is a tag or a branch
                cmd = ["git", "show-ref", "--verify", "--quiet",
                       f"refs/heads/{self['revision']}"]
                self._run(cmd)
                self.add_output(
                    self.indent_spaces
                    + "[INFO] Git fetch origin reason: "
                    + f"{self['revision']} is a branch, not a tag"
                    + "\n")
                do_git_fetch = True
            except subprocess.CalledProcessError:
                pass

        if not do_git_fetch:
            self.add_output(self.indent_spaces + "[INFO] git fetch ignored\n")
            return False

        # Fetch
        self._git_fetch_origin()
        return True

    def _git_merge(self):
        git_merge = False

        # Merge
        real_branch = self._git_is_local_branch("HEAD")
        if real_branch and self.current_branch:
            # TODO: only merge when difference from upstream
            commit_ref_head = self._git_ref(cwd=self.git_local_dir)
            self._run(["git", "merge", "--ff-only",
                       f"origin/{self.current_branch}"])
            git_ref_after_merge = self._git_ref(cwd=self.git_local_dir)
            if commit_ref_head != git_ref_after_merge:
                git_merge = True
                self.set_changed(True)
                self._run(["git", "log",
                           '--pretty=format:"%h %ad %s [%cn]"',
                           "--decorate", "--date=short",
                           f"{commit_ref_head}..{git_ref_after_merge}"])

        return git_merge

    def _git_get_remote_url(self, remote_name: str = "origin") -> str:
        origin_url = ""
        try:
            stdout, _ = self._run(["git", "config",
                                   f"remote.{remote_name}.url"])
            origin_url = stdout[0]
        except (subprocess.CalledProcessError, IndexError) as err:
            raise GitRemoteError(
                f"Failed to get the Git remote url: {remote_name}") from err

        return origin_url

    def _git_set_remote_url(self, url: str,
                            remote_name: str = "origin") -> str:
        origin_url = ""
        try:
            self._run(["git", "remote", "remove", remote_name])
        except subprocess.CalledProcessError:
            # Ignore when it cannot be removed when it does not exist
            pass

        try:
            stdout, _ = self._run(["git", "remote", "add", remote_name, url])
            origin_url = stdout[0]
        except (subprocess.CalledProcessError, IndexError) as err:
            raise GitRemoteError(
                f"Failed to modify the Git remote url: {remote_name}") from err

        return origin_url

    def _git_is_local_branch(self, branch: str) -> bool:
        "Return True if it is a local branch that exists."
        try:
            stdout, _ = self._run(["git", "rev-parse", "--symbolic-full-name",
                                   branch])
            if not stdout:
                return False

            full_branch_name = stdout[0].strip()

            if full_branch_name.startswith("refs/heads/"):
                return True
        except subprocess.CalledProcessError:
            pass

        return False

    def _git_rev_parse_verify(self, revision: str) -> List[str]:
        stdout: List[str] = []
        error = False
        try:
            stdout, _ = self._run(["git", "rev-parse", "--verify", revision])
            if not stdout:
                error = True
        except subprocess.CalledProcessError:
            error = True

        if error:
            raise GitRevisionDoesNotExist(
                f"The revision '{revision}' does not exist.")

        return stdout

    def _repo_fix_branch(self) -> bool:
        git_ref_after_merge = self._git_ref(cwd=self.git_local_dir)
        branch_changed = False
        if self["revision"]:
            # We also need tags because sometimes, a branch
            # returns a different commit revision
            git_tags, _ = self._run(["git", "tag", "--points-at", "HEAD"])

            # Also check the commit revision in case
            # branch is a commit revision instead of a tag
            try:
                # Check if the branch exists
                git_ref_branch = self._git_rev_parse_verify("origin/"
                                                            + self["revision"]
                                                            + "^{commit}")[0]
            except GitRevisionDoesNotExist:
                # Check if the commit ref exists
                try:
                    git_ref_branch = \
                        self._git_rev_parse_verify(self["revision"])[0]
                except GitRevisionDoesNotExist as err:
                    raise BatchFetchError(f"The branch '{self['revision']}' "
                                          "does not exist.") from err

            if git_ref_after_merge != git_ref_branch and \
                    self["revision"] not in git_tags:
                # Update the branch
                self._run(["git", "checkout"] + [self["revision"]])
                self.add_output(self.indent_spaces
                                + "[INFO] Branch changed to "
                                + self["revision"] + "\n")
                self.set_changed(True)
                branch_changed = True

                # Read branch again
                self._update_current_branch_name()

        return branch_changed

    def _git_fetch_origin(self):
        # Fetch
        if not self._git_fetch_origin_done:
            cmd = ["git", "fetch", "origin"]
            self._run(cmd)
            self._git_fetch_origin_done = True

    def _repo_fix_remote_origin(self):
        correct_origin_url = self[self.main_key]
        update_remote_origin = False

        try:
            origin_url = self._git_get_remote_url()
            if origin_url != correct_origin_url:
                update_remote_origin = True
        except GitRemoteError:
            update_remote_origin = True

        if update_remote_origin:
            # Update remote
            try:
                self._git_set_remote_url(correct_origin_url)
            except GitRemoteError:
                # TODO handle errors
                return

            # Get the current branch
            if self.current_branch:
                try:
                    self.add_output(
                        self.indent_spaces
                        + "[INFO] Git fetch origin reason: "
                        f"we need to set the upstream "
                        f"origin to {self.current_branch}"
                        "\n"
                    )
                    self._git_fetch_origin()

                    cmd = ["git", "branch",
                           f"--set-upstream-to=origin/{self.current_branch}"]
                    _, _ = self._run(cmd)
                    # TODO: handle errors
                except subprocess.CalledProcessError as err:
                    raise BatchFetchError(str(err)) from err
