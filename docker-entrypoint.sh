#!/bin/bash
set -e

# Fix permissions for mounted volumes (if running as root initially)
if [ "$(id -u)" = "0" ]; then
    echo "Running as root, fixing permissions for mounted volumes..."
    
    # Fix ownership of directories
    chown -R appuser:appuser /app/uploads /app/signed /app/temp_keys /app/logs 2>/dev/null || true
    
    # Ensure GPG home directory exists and has correct permissions
    if [ ! -d /home/appuser/.gnupg ]; then
        mkdir -p /home/appuser/.gnupg
        chown -R appuser:appuser /home/appuser/.gnupg
        chmod 700 /home/appuser/.gnupg
    fi
    
    # Switch to appuser and execute command
    echo "Switching to appuser..."
    exec gosu appuser "$@"
else
    # Already running as appuser
    echo "Running as appuser (UID: $(id -u))"
    exec "$@"
fi
