# Use a slim Python base image for smaller size
FROM python:3.14-slim-bookworm

# Set the working directory inside the container
WORKDIR /app

# Latest releases available at https://github.com/aptible/supercronic/releases
ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.2.46/supercronic-linux-amd64 \
    SUPERCRONIC_SHA1SUM=5bcefed628e32adc08e32634db2d10e9230dbca0 \
    SUPERCRONIC=supercronic-linux-amd64

RUN apt-get update && apt-get upgrade -y --no-install-recommends && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSLO "$SUPERCRONIC_URL" \
    && echo "${SUPERCRONIC_SHA1SUM}  ${SUPERCRONIC}" | sha1sum -c - \
    && chmod +x "$SUPERCRONIC" \
    && mv "$SUPERCRONIC" "/usr/local/bin/${SUPERCRONIC}" \
    && ln -s "/usr/local/bin/${SUPERCRONIC}" /usr/local/bin/supercronic

# Upgrade vulnerable packages from base image before installing requirements
RUN pip install --no-cache-dir --upgrade pip "wheel>=0.46.2" "jaraco.context>=6.1.0"

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

# Create a non-root user and hand over ownership of the app directory
RUN useradd -r -u 1001 -s /bin/false appuser \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set the entrypoint for the container to run the start.sh script
CMD ["./start.sh"]
