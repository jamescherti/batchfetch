#!/usr/bin/env python

from setuptools import setup, find_packages
from pathlib import Path


setup(
    name="batchfetch",
    version="1.0.0",
    packages=find_packages(),
    long_description=((Path(__file__).parent.resolve().joinpath("README.md"))
                      .read_text(encoding="utf-8")),
    long_description_content_type="text/markdown",
    url="https://github.com/jamescherti/batchfetch",
    author="James Cherti",
    python_requires=">=3.6, <4",
    install_requires=[],
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
            "batchfetch=batchfetch.__init__:command_line_interface",
        ],
    },
)
