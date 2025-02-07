#!/bin/sh
set -e

exec python3 /app/smartzone_exporter.py -t ${VSZ_TARGET} ${EXTRA_PARAM}