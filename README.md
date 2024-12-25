# Batchfetch - Efficiently clone or pull multiple Git repositories in parallel

## Introduction

Batchfetch is a command-line tool designed to clone, fetch, and merge multiple Git repositories simultaneously. With Batchfetch, you no longer need to manually manage each repository one by one. It automates the tedious aspects of repository management, freeing you up to focus on what truly matters: your workflow.

But why use Batchfetch? Because it is extremely fast, cloning repositories quickly by running Git operations in parallel. It intelligently detects whether a `git fetch` is needed, further speeding up the process of downloading data from repositories. Additionally, it allows specifying the revision (for Git), ensuring that the cloned repository matches the exact version you require.

Batchfetch is ideal for quickly cloning or pulling multiple Git repositories. It is also useful for cloning various addons, such as Vim plugins, Emacs packages, Ansible roles, Ansible collections, and other addons available on websites like GitHub, Codeberg, and GitLab.

## Installation

Here is how to install *batchfetch* using [pip](https://pypi.org/project/pip/):
```
pip install --user batchfetch
```

The pip command above installs the *batchfetch* executable in the `~/.local/bin/` directory. Omitting the `--user` flag will install it system-wide.

## Usage

### Example of a `batchfetch.yaml` file

Here is an example of a `batchfetch.yaml` file:

```yaml
---

tasks:
  # Clone the default branch of the general.el repository to the
  # './general.el' directory
  - git: https://github.com/jamescherti/compile-angel.el

  # Clone the tag 1.5 of the consult repository to the './consult'
  # directory
  - git: https://github.com/jamescherti/outline-indent.el
    revision: "1.1.0"

  # Clone the s.el repository to the './another-name.el' directory
  - git: https://github.com/jamescherti/easysession.el
    path: easysession
    revision: b9c6d9b6134b4981760893254f804a371ffbc899

  # Delete the local copy of the following repository
  - git: https://github.com/jamescherti/dir-config.el
    delete: true
```

Execute the `batchfetch` command from the same directory as `batchfetch.yml` to make it clone or update the local copies of the repositories above.

## Command-line options

Here are the various options that `batchfetch` provides, along with descriptions of their usage:

```
usage: batchfetch [--option] [TARGET]

Efficiently clone/pull multiple Git repositories in parallel.

positional arguments:
  target                This is a target path that batchfetch is supposed to
                        handle. When no target is specified, execute the tasks
                        of all target paths defined in the batchfetch.yml list
                        of tasks.

options:
  -h, --help            show this help message and exit
  -f FILE, --file FILE  Specify the batchfetch YAML file (default:
                        './batchfetch.yaml').
  -C DIRECTORY, --directory DIRECTORY
                        Change the working directory before reading the
                        batchfetch.yaml file. If not specified, the directory
                        is set to the parent directory of the batchfetch.yaml
                        file.
  -j JOBS, --jobs JOBS  Run up to N parallel processes (default: 5).
                        Alternatively, the BATCHFETCH_JOBS environment
                        variable can be used to configure the number of jobs.
  -v, --verbose         Enable verbose mode.
  -u, --check-untracked
                        Abort if untracked files or directories exist.
                        Alternatively, set the BATCHFETCH_CHECK_UNTRACKED=1
                        environment variable to enable this check.
```

## Features
- Git Clone and Fetch/Merge: Clones the repositories and their submodules, ensuring that all the repositories are always up-to-date by fetching and merging changes.
- Parallel Operations: Utilizes threads to simultaneously Git clone or pull multiple repositories, dramatically reducing wait times.
- User-Friendly Interface: Provides simple and straightforward command-line options that make it easy to get started and effectively manage your repositories.
- Custom Configuration: Allows the use of a YAML configuration file to specify and manage the repositories you interact with, enabling repeatable setups and consistent environments.
- Detect files that should not be present in directories managed by batchfetch, known as untracked files.

## Frequently Asked Questions

### What are untracked files?

The parent directory of the "path:" value defines the managed directory, where the directory of each path is considered as the managed directory.

For example, if the "path:" value is `file/my-project`, the managed directory will be `file/`. Any file within `file/` that is not managed by batchfetch will be considered an untracked file.

When *batchfetch* encounters an untracked file, it displays an error message to inform users about paths that are not managed by the system. The message provides clear instructions on how to handle these paths by adding them to the `options.ignore_untracked_paths` list, enabling users to manage untracked files effectively.

Here is an example of a *batchfetch.yaml* file that enables *batchfetch* to accept a list of untracked files:

``` yaml
options:
  ignore_untracked_paths:
    - ./test
    - /absolute/path
    - ../relative/path

tasks:
  - git: https://github.com/user/project
```

By default, *batchfetch.yaml* is the only untracked file that is ignored. The user does not need to add it to the *ignore_untracked_paths* option.

### How is the Git local paths handled?

When "path:" is specified, that's the path that is used.

When "path:" is not specified, Batchfetch attempts to determine the path name by extracting the repository name from the URI (e.g., `https://domain.com/repo` becomes `repo`). If the URL ends with a `.git` extension, it removes the extension (e.g., `https://domain.com/repo.git` becomes `repo`).

### How does Batchfetch detect when a git fetch is necessary?

Batchfetch is fast, not only because it runs Git commands in parallel, but also because it intelligently detects whether a `git fetch` is needed, further speeding up the process of downloading data from repositories.

When the user has specifies a revision (branch or commit reference), Batchfetch only performs a `git fetch` if that revision does not exist locally. If the revision is already up to date, it simply proceeds to the next repository in the queue.

That's why it is highly recommended to always specify the revision to speed up Batchfetch, if speed is important to you. Here is an example of a `batchfetch.yaml` file where the branch (`1.1.0`) or commit reference (`b9c6d9b6134b4981760893254f804a371ffbc899`) is specified:
``` yaml
tasks:
  - git: https://github.com/jamescherti/outline-indent.el
    revision: "1.1.0"

  - git: https://github.com/jamescherti/easysession.el
    path: easysession
    revision: b9c6d9b6134b4981760893254f804a371ffbc899
```

### How to execute a command before and after a task?

To execute a command both before and after a specific task, you can define the `exec_before` and `exec_after` directives within the task configuration. These directives specify commands to be executed at the respective stages of the task lifecycle.

Here is an example:
``` yaml
---
tasks:
  - git: https://github.com/jamescherti/easysession.el
    path: easysession
    exec_before: ["sh", "-c", "echo exec_before_task"]
    exec_after: ["sh", "-c", "echo exec_after_task"]
```

### How to make batchfetch handle only one path?

To configure `batchfetch` to handle a specific path, you can define your tasks in a `batchfetch.yml` file and pass the desired path as an argument to the `batchfetch` command.

#### Example `batchfetch.yml` file:

In the following example, the `easysession` task clones two Git repositories:
```yaml
---
tasks:
  - git: https://github.com/jamescherti/easysession.el
    path: easysession

  - git: https://github.com/jamescherti/outline-indent.el
    revision: "1.1.0"
```

To make `batchfetch` clone only `easysession`, pass its path as an argument:

```bash
batchfetch easysession
```

This will execute only the task corresponding to the `easysession` path, skipping all others in the `batchfetch.yml` file.

### How can I configure batchfetch to load a file other than batchfetch.yaml?

You can specify the configuration file using the `-f` command-line option:

```yaml
batchfetch -f alternative-batchfetch.yaml
```

Alternatively, you can set the `BATCHFETCH_FILE` environment variable:

```bash
export BATCHFETCH_FILE=alternative-batchfetch.yaml
batchfetch
```

## License

Copyright (C) 2024 [James Cherti](https://www.jamescherti.com)

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program.

## Links

- [batchfetch @GitHub](https://github.com/jamescherti/batchfetch)
- [batchfetch @Pypi](https://pypi.org/project/batchfetch/)
