#!/bin/sh
set -eu
if [ ! -f "${1:-}" ]; then
  exit 1
fi
cat "$1"
