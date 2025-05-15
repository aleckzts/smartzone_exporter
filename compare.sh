#!/bin/sh
set -e

docker compose exec smartzone_exporter python3 /app/comparewifi.py $@
