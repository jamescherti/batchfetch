# Batchfetch - Efficiently clone or pull multiple Git repositories in parallel

## Introduction

Batchfetch is a command-line tool designed to clone, fetch, and merge multiple Git repositories simultaneously.

With Batchfetch, you no longer need to manually manage each repository one by one. It automates the tedious aspects of repository management, freeing you up to focus on what truly matters: your workflow.

Batchfetch is ideal for quickly cloning or pulling multiple Git repositories. It is also useful for cloning various addons, such as Vim plugins, Emacs packages, Ansible roles, Ansible collections, and other addons available on websites like GitHub, Codeberg, and GitLab.

## Features:
- Git Clone and Fetch/Merge: Clones the repositories and their submodules, ensuring that all the repositories are always up-to-date by fetching and merging changes.
- Parallel Operations: Utilizes threads to simultaneously Git clone or pull multiple repositories, dramatically reducing wait times.
- User-Friendly Interface: Provides simple and straightforward command-line options that make it easy to get started and effectively manage your repositories.
- Custom Configuration: Allows the use of a YAML configuration file to specify and manage the repositories you interact with, enabling repeatable setups and consistent environments.

## Installation

```
pip install --user batchfetch
```

The pip command above will install the `batchfetch` executable in the directory `~/.local/bin/`.

## Example

Here is an example of a `batchfetch.yaml` file:

```yaml
---

tasks:
  # Clone the default branch of the general.el repository to the
  # './general.el' directory
  - git: https://github.com/noctuid/general.el

  # Clone the tag 1.5 of the consult repository to the './consult'
  # directory
  - git: https://github.com/minad/consult
    revision: "1.5"

  # Clone the s.el repository to the './another-name.el' directory
  - git: https://github.com/magnars/s.el
    path: another-name.el
    revision: dda84d38fffdaf0c9b12837b504b402af910d01d

  # Delete './impatient-mode'
  - git: https://github.com/skeeto/impatient-mode
    delete: true
```

Execute the `batchfetch` command from the same directory as `batchfetch.yml` to make it clone or update the local copies of the repositories above.

## Usage

Here are the various options that `batchfetch` provides, along with descriptions of their usage:

```
usage: batchfetch [--option] [args]

Command line interface.

positional arguments:
  N                     Specify the batchfetch YAML file(s) (default: './batchfetch.yaml').

options:
  -h, --help            show this help message and exit
  -j JOBS, --jobs JOBS  Run up to N Number of parallel processes (Default: 5).
  -v, --verbose         Enable verbose mode.
```

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

## License

Copyright (C) 2024 [James Cherti](https://www.jamescherti.com)

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program.

## Links

- [batchfetch @GitHub](https://github.com/jamescherti/batchfetch)
- [batchfetch @Pypi](https://pypi.org/project/batchfetch/)
