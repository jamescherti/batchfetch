#!/usr/bin/env bash

cd "$(dirname "${BASH_SOURCE[0]}")"
cat ./test-md5sum.txt
cat ./test-md5sum.txt | tail -n 1 >&2
