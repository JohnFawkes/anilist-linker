# Use a slim Python base image for smaller size
FROM python:3.11-slim-bookworm

# Set the working directory inside the container
WORKDIR /app

# Install supercronic (a container-native cron that runs without root)
ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.2.44/supercronic-linux-amd64 \
    SUPERCRONIC=/usr/local/bin/supercronic \
    SUPERCRONIC_SHA1SUM=6eb0a8e1e6673675dc67668c1a9b6409f79c37bc

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL "$SUPERCRONIC_URL" -o "$SUPERCRONIC" \
    && echo "${SUPERCRONIC_SHA1SUM}  ${SUPERCRONIC}" | sha1sum -c - \
    && chmod +x "$SUPERCRONIC"

# Copy the requirements file and install Python dependencies
# Using --no-cache-dir to prevent pip from storing downloaded packages, reducing image size
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir --upgrade pip wheel "jaraco.context>=6.0.0"

# Copy your Python script and the .env.example (for reference)
# The actual .env file will be mounted or passed as environment variables at runtime
COPY anilist_linker.py .
COPY .env.example .

# Make the Python script executable
RUN chmod +x anilist_linker.py

# Copy the startup script and make it executable
COPY Docker/start.sh .
RUN chmod +x start.sh

# Create a non-root user and hand over ownership of the app directory
RUN useradd -r -u 1001 -s /bin/false appuser \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set the entrypoint for the container to run the start.sh script
CMD ["./start.sh"]
