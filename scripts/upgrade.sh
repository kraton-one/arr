#!/bin/bash

# Media Stack Directory Setup Script
# This creates the necessary directory structure for your arr stack

set -e
docker compose pull
docker compose up -d --force-recreate --build