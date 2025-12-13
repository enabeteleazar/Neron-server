#!/usr/bin/env bash
set -e
./scripts/stop_all.sh
sleep 2
./scripts/start_all.sh
