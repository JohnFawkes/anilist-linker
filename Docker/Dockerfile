# Use a slim Python base image for smaller size
FROM python:3.15-slim-bookworm

# Set the working directory inside the container
WORKDIR /app

# Latest releases available at https://github.com/aptible/supercronic/releases
ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.2.51/supercronic-linux-amd64 \
    SUPERCRONIC_SHA1SUM=1692066e350a88ff4d7d6474fe3c7a6c41ec5e89 \
    SUPERCRONIC=supercronic-linux-amd64

RUN apt-get update && apt-get upgrade -y --no-install-recommends && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSLO "$SUPERCRONIC_URL" \
    && echo "${SUPERCRONIC_SHA1SUM}  ${SUPERCRONIC}" | sha1sum -c - \
    && chmod +x "$SUPERCRONIC" \
    && mv "$SUPERCRONIC" "/usr/local/bin/${SUPERCRONIC}" \
    && ln -s "/usr/local/bin/${SUPERCRONIC}" /usr/local/bin/supercronic

# Copy the requirements file and install Python dependencies
# Using --no-cache-dir to prevent pip from storing downloaded packages, reducing image size.
# pip is uninstalled afterwards: it isn't needed at runtime, and its vendored
# dependency list (pip/_vendor/vendor.txt, e.g. setuptools, urllib3, msgpack)
# is flagged by Trivy as installed Python packages.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y pip

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
