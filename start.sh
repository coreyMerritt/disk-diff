#!/usr/bin/env bash

if [[ -f .venv/bin/activate ]]; then
  source .venv/bin/activate
fi

sudo python3 ./src/main.py $@

