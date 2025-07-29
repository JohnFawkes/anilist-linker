#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Starting Plex Anilist Linker Container..."

# Check if PLEX_LOG_PATH is set and create the directory if it doesn't exist
if [ -n "$PLEX_LOG_PATH" ]; then
    mkdir -p "$PLEX_LOG_PATH"
    echo "Log path set to: $PLEX_LOG_PATH"
else
    echo "PLEX_LOG_PATH is not set. Script output will go to Docker logs (stdout/stderr)."
fi

# Determine if a force run on start is requested
# FORCE_RUN_ON_START is expected to be 'True' or 'False' from .env
if [ "$FORCE_RUN_ON_START" = "True" ]; then
    echo "FORCE_RUN_ON_START is True. Running script once immediately..."
    # Execute the Python script with -y to bypass confirmation
    # Redirect output to Docker logs
    /usr/local/bin/python /app/anilist_linker.py -y >> /proc/1/fd/1 2>> /proc/1/fd/2
    echo "Immediate run complete. Proceeding with cron scheduling."
fi

# Create the crontab file for our scheduled job
# The cron job will execute the Python script.
# Output (stdout and stderr) of the cron job is redirected to /proc/1/fd/1 and /proc/1/fd/2
# This makes the cron job's output visible via `docker logs <container_name>`.
# The -y flag is added to bypass the confirmation prompt for live runs.
echo "${CRON_SCHEDULE} /usr/local/bin/python /app/anilist_linker.py -y >> /proc/1/fd/1 2>> /proc/1/fd/2" > /etc/cron.d/plex-anilist-cron

# Give the crontab file appropriate permissions
chmod 0644 /etc/cron.d/plex-anilist-cron

# Apply the crontab (optional, as cron -f will pick it up, but good for explicit setup)
crontab /etc/cron.d/plex-anilist-cron

echo "Cron job scheduled: '${CRON_SCHEDULE} /usr/local/bin/python /app/anilist_linker.py -y'"

# Start the cron service in the foreground.
# This keeps the container running and allows Docker to capture its logs.
echo "Starting cron service in foreground..."
cron -f
