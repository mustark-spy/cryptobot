#!/usr/bin/env bash
set -e

pip install --no-cache-dir -r requirements.txt
mkdir -p "${DATA_DIR:-./data}"
exec python bot.py
