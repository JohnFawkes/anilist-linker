# Use a slim Python base image for smaller size
FROM python:3.11-slim-bookworm

# Set the working directory inside the container
WORKDIR /app

# Install cron and other necessary tools
# apt-get update: Updates the list of available packages
# apt-get install -y cron: Installs the cron daemon
# rm -rf /var/lib/apt/lists/*: Cleans up apt cache to keep image small
RUN apt-get update && apt-get install -y cron \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install Python dependencies
# Using --no-cache-dir to prevent pip from storing downloaded packages, reducing image size
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your Python script and the .env.example (for reference)
# The actual .env file will be mounted or passed as environment variables at runtime
COPY anilist_linker.py .
COPY .env.example .

# Make the Python script executable
RUN chmod +x anilist_linker.py

# Copy the startup script and make it executable
COPY Docker/start.sh .
RUN chmod +x start.sh

# Create a log file for cron and ensure it's writable (optional, but good practice)
# Cron logs can also be redirected to stdout/stderr via start.sh
RUN touch /var/log/cron.log
RUN chmod 0644 /var/log/cron.log

# Set the entrypoint for the container to run the start.sh script
CMD ["./start.sh"]
