#!/usr/bin/env bash
cd "$(dirname "${BASH_SOURCE[0]}")"
export PYTHONPATH="$(pwd)"
exec pytest -v -v --cov=batchfetch --cov=tests \
  --cov-report=term \
  --cov-report=html:htmlcov \
  tests/*
