#!/bin/bash
set -e

# Fix permissions for mounted volumes (if running as root initially)
if [ "$(id -u)" = "0" ]; then
    echo "Running as root, fixing permissions for mounted volumes..."
    
    # Fix ownership of directories
    chown -R appuser:appuser /app/uploads /app/signed /app/temp_keys /app/logs 2>/dev/null || true
    
    # Switch to appuser and execute command
    echo "Switching to appuser..."
    exec gosu appuser "$@"
else
    # Already running as appuser
    echo "Running as appuser (UID: $(id -u))"
    exec "$@"
fi
