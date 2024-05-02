# Batchfetch - Efficiently clone or pull multiple Git repositories.

## Introduction

Efficiently clone or pull multiple Git repositories in parallel. Ideal for developers managing multiple projects or for downloading plugins or packages in bulk.

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
    branch: "1.5"

  # Clone the s.el repository to the './another-name.el' directory
  - git: https://github.com/magnars/s.el
    path: another-name.el
    branch: dda84d38fffdaf0c9b12837b504b402af910d01d

  # Delete './impatient-mode'
  - git: https://github.com/skeeto/impatient-mode
    delete: true
```

Execute the `batchfetch` command from the same directory as `batchfetch.yml` to make it clone or update the local copies of the repositories above.

## Usage

Here are the various options that `batchfetch` provides, along with descriptions of their usage:

```sh
usage: batchfetch [--option] [args]

Command line interface.

options:
  -h, --help            show this help message and exit
  -p MAX_PROCS, --max-procs MAX_PROCS
                        Run up to N Number of parallel git processes (Default: 3).
  -v, --verbose         Enable verbose mode.
  -f BATCHFETCH_FILE, --batchfetch-file BATCHFETCH_FILE
                        Specify the batchfetch YAML file (default: './batchfetch.yaml').
```
## License

Copyright (c) [James Cherti](https://www.jamescherti.com)

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program.

## Links

- [batchfetch @GitHub](https://github.com/jamescherti/batchfetch)
- [batchfetch @Pypi](https://pypi.org/project/batchfetch/)
