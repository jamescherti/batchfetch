# Batchfetch - Efficiently clone or pull multiple Git repositories.

## Introduction

Efficiently clone or pull multiple Git repositories in parallel. Ideal for developers managing multiple projects or for downloading plugins or packages in bulk.

## Installation

```
sudo pip install git+https://github.com/jamescherti/batchfetch
```

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

## License

Copyright (c) [James Cherti](https://www.jamescherti.com)

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program.

## Links

- [The batchfetch Git repository](https://github.com/jamescherti/batchfetch)
