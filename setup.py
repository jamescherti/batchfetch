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

from pathlib import Path

from setuptools import find_packages, setup

setup(
    name="batchfetch",
    version="1.1.0",
    packages=find_packages(),
    description="Efficiently clone and pull multiple Git repositories.",
    license="GPLv3",
    long_description=((Path(__file__).parent.resolve().joinpath("README.md"))
                      .read_text(encoding="utf-8")),
    long_description_content_type="text/markdown",
    url="https://github.com/jamescherti/batchfetch",
    author="James Cherti",
    python_requires=">=3.6, <4",
    install_requires=[
        "colorama",
        "schema",
        "setproctitle",
        "PyYAML",
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Environment :: Console",
        "Operating System :: POSIX :: Linux",
        "Operating System :: POSIX :: Other",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Version Control :: Git",
        "Topic :: Utilities",
    ],
    entry_points={
        "console_scripts": [
            "batchfetch=batchfetch.batchfetch_cli:command_line_interface",
        ],
    },
)
