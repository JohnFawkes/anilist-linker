# Plex Anilist Linker

This Python script automates the process of enriching your Plex Media Server library by finding corresponding Anilist entries for your anime TV shows and movies and then prepending the Anilist URL to their summaries. It achieves this by leveraging external ID mappings (TMDB, TVDB, IMDb) from the Kometa-Team's `anime_ids.json` data.

## Features

* **Plex Integration:** Connects directly to your Plex Media Server.

* **Flexible Library Scanning:** Targets specific TV show and/or Movie libraries in Plex, or skips them if not specified.

* **Robust ID Matching:** Extracts TMDB, TVDB, or IMDb IDs from Plex item GUIDs and uses these to find the corresponding Anilist ID from a comprehensive `anime_ids.json` dataset. Prioritizes TMDB, then TVDB, then IMDb.

* **Anilist API Interaction:** Queries the Anilist GraphQL API by ID to retrieve the official Anilist URL.

* **Summary Enrichment:** Prepends the found Anilist URL to the summary of the Plex item.

* **Duplicate Prevention:** Avoids adding duplicate Anilist links to summaries that already contain them.

* **Rate Limit Handling:** Implements proactive and reactive rate limiting for Anilist API calls (1 call every 2 seconds, plus pauses for `Retry-After` headers).

* **Configurable via `.env`:** All sensitive information (Plex URL/token) and script settings are managed securely through a `.env` file.

* **Dry Run Mode:** Allows you to preview changes without modifying your Plex library.

* **Headless Operation:** Option to bypass interactive confirmation for automated environments.

* **Detailed Logging:** Provides comprehensive console and file logging for monitoring and troubleshooting.

* **Dockerized & Scheduled:** Can be run as a Docker container with a user-defined cron schedule, including an option to force an immediate run on container start.

## Installation

To get started with the Plex Anilist Linker, follow these steps:

1.  **Clone the Repository:**

    ```bash
    git clone [https://github.com/your-username/your-repo-name.git](https://github.com/your-username/your-repo-name.git)
    cd your-repo-name
    ```

    *(Replace `your-username/your-repo-name` with your actual repository details if you create one.)*

2.  **Install Python (if running directly):**
    Ensure you have Python 3.8 or newer installed. You can download it from [python.org](https://www.python.org/downloads/). *(If you plan to use Docker, Python will be installed within the container.)*

3.  **Create a Virtual Environment (Recommended for direct Python execution):**
    If you're running the script directly (not via Docker), it's good practice to create a virtual environment:

    ```bash
    python3 -m venv venv
    # On Windows:
    # .\venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```

4.  **Install Dependencies:**
    The script relies on a few Python libraries. Install them using `pip`:

    ```bash
    pip install -r requirements.txt
    ```

    *(The `requirements.txt` file should contain `plexapi`, `requests`, and `python-dotenv`.)*

5.  **Download `anime_ids.json` (Automated):**
    The script will automatically download the `anime_ids.json` file from `https://raw.githubusercontent.com/Kometa-Team/Anime-IDs/refs/heads/master/anime_ids.json` when it runs. Ensure your system has internet access.

## Usage

### 1. Configure Environment Variables (`.env` file)

Create a file named `.env` in the root directory of the cloned repository (the same directory as the script). Populate it with your configuration. **Ensure there are no spaces around the `=` signs.**

```ini
# .env file for Plex to Anilist Linker Script

# --- Plex Configuration ---
# Your Plex Media Server URL (e.g., 'http://localhost:32400' or '[http://192.168.1.100:32400](http://192.168.1.100:32400)')
PLEX_URL='YOUR_PLEX_URL'
# Your Plex X-Plex-Token. You can find this by inspecting network requests when using Plex Web.
PLEX_TOKEN='YOUR_PLEX_TOKEN'

# --- Script Behavior Settings ---
# Set to 'True' to make actual changes to Plex summaries.
# Set to 'False' for a dry run (recommended for testing).
PLEX_MAKE_CHANGES='False'

# Set to 'True' to enable detailed [DEBUG] messages in the console and log file.
# Set to 'False' for more concise [INFO] level messages in the console.
PLEX_DEBUG='False'

# Path to the directory where log files will be saved INSIDE the container (e.g., '/app/logs').
# If left empty, logging will only go to the container's stdout/stderr.
# If you want logs persisted outside the container, you'll need to mount a volume.
PLEX_LOG_PATH='/app/logs'

# --- Library Targeting ---
# Comma-separated list of EXACT TV show library names in Plex (e.g., "Anime,My Cartoons").
# If left empty, TV show libraries will be SKIPPED entirely.
PLEX_TARGET_TV_SHOW_LIBRARIES=''

# Comma-separated list of EXACT Movie library names in Plex (e.g., "Anime Movies,Studio Ghibli").
# If left empty, Movie libraries will be SKIPPED entirely.
PLEX_TARGET_MOVIE_LIBRARIES=''

# --- Anilist Data Source ---
# URL for the anime_ids.json file. Usually, this default is fine.
ANIME_IDS_JSON_URL='[https://raw.githubusercontent.com/Kometa-Team/Anime-IDs/refs/heads/master/anime_ids.json](https://raw.githubusercontent.com/Kometa-Team/Anime-IDs/refs/heads/master/anime_ids.json)'

# --- Anilist API Settings ---
# Anilist GraphQL API endpoint. Usually, this default is fine.
ANILIST_API_URL='[https://graphql.anilist.co](https://graphql.anilist.co)'
# The format string for the Anilist link prepended to summaries.
# '{anilist_url}' will be replaced with the actual Anilist URL.
ANILIST_PREFIX_FORMAT='[Anilist: {anilist_url}]\n'
# Regular expression used to detect if an Anilist link already exists at the start of the summary.
# This should match the format above. The \/? makes the trailing slash optional.
EXISTING_ANILIST_PREFIX_CHECK_PATTERN='^\[Anilist: https:\/\/anilist\.co\/anime\/\\d+\/?\]\s*'

# --- Anilist Rate Limit Settings ---
# Maximum number of retries for Anilist API calls if a rate limit or transient error occurs.
MAX_ANILIST_RETRIES='5'
# Default number of seconds to wait if Anilist hits a rate limit and doesn't provide a 'Retry-After' header.
# Also used for proactive pausing when 'x-ratelimit-remaining' is low.
DEFAULT_RETRY_AFTER_SECONDS='60'
# The script also enforces 1 API call every 2.0 seconds directly (ANILIST_MIN_INTERVAL_SECONDS = 2.0 in script).

# --- Scheduling ---
# Cron schedule for running the script.
# Format: "minute hour day_of_month month day_of_week"
# Examples:
#   "0 3 * * *"  - Every day at 3:00 AM
#   "0 0 * * 0"  - Every Sunday at 12:00 AM (midnight)
#   "*/30 * * * *" - Every 30 minutes
# Find more examples at crontab.guru
CRON_SCHEDULE="0 3 * * *"
# Set to 'True' to force the script to run once immediately when the container starts,
# in addition to any scheduled cron runs. Set to 'False' to only run on schedule.
FORCE_RUN_ON_START='False'
````

### 2\. Run the Script (Directly or via Docker)

#### Option A: Run Directly (for testing/development)

Once your `.env` file is configured and dependencies are installed, you can run the script from your terminal:

##### Dry Run (Recommended for first-time use)

Always start with a dry run to see what changes the script *would* make without actually modifying your Plex library.

```bash
python plex_anilist_linker.py
```

*(Ensure `PLEX_MAKE_CHANGES='False'` in your `.env` file for a dry run.)*

##### Live Run

If you're confident in the dry run output, you can set `PLEX_MAKE_CHANGES='True'` in your `.env` file and run the script. It will ask for confirmation by default.

```bash
python plex_anilist_linker.py
```

##### Headless / Bypass Confirmation

For automated environments (e.g., cron jobs on a host machine), you can bypass the confirmation prompt by adding the `-y` or `--yes` flag:

```bash
python plex_anilist_linker.py -y
# or
python plex_anilist_linker.py --yes
```

*(This will only apply changes if `PLEX_MAKE_CHANGES='True'` in your `.env` file.)*

#### Option B: Run with Docker (for production/scheduling)

1.  **Build the Docker Image:**
    Navigate to the root directory of your project (where `docker-compose.yml` is located) in your terminal and build the image:

    ```bash
    docker build -t plex-anilist-linker -f docker/Dockerfile .
    ```

2.  **Run the Docker Container with Docker Compose:**
    This is the recommended way to run the container for scheduling and persistent logging. Ensure your `.env` file is in the project root.

    ```bash
    docker compose up -d --build
    ```

      * `docker compose up`: Starts the services defined in `docker-compose.yml`.

      * `-d`: Runs the containers in detached mode (in the background).

      * `--build`: Forces Docker Compose to rebuild the image before starting the container. Use this whenever you make changes to your `Dockerfile` or source code.

      * Logs will be saved to the `./logs` directory in your project root by default (as configured in `docker-compose.yml` and `.env`).

3.  **Check Container Logs:**
    To see the output of your scheduled script runs (including errors and unmatched items), check the Docker logs:

    ```bash
    docker compose logs -f plex-anilist-linker
    ```

      * `-f`: Follows the log output in real-time.

4.  **Stop and Remove the Container:**

    ```bash
    docker compose down
    ```

## Troubleshooting & Debugging

  * **Check Console Output (for direct runs) / Docker Logs (for containerized runs):** The script provides real-time feedback on its progress.

  * **Review Log Files:** If `PLEX_LOG_PATH` is configured and mounted (for Docker), detailed logs will be saved, which are invaluable for debugging.

  * **Enable Debug Mode:** Set `PLEX_DEBUG='True'` in your `.env` file to get very verbose output in both the console/Docker logs and log file, showing internal workings like GUID parsing and JSON lookups.

  * **Unmatched Items:** At the end of each run, the script will list any items for which it couldn't find an Anilist link, along with the reason (e.g., no external ID, no match in `anime_ids.json`, API error).

  * **Plex Library Agents:** If the script consistently reports "No recognizable TMDB, TVDB, or IMDb ID formats found in GUIDs," it might indicate that your Plex library's metadata agent is not configured to pull these external IDs. Consider changing your library's agent settings (e.g., to "Plex Movie" or "Plex TV Series" which often expose these, or specific agents like "TheTVDB") and refreshing metadata for your items.

  * **Cron Schedule:** Ensure your `CRON_SCHEDULE` in the `.env` file is in the correct cron format. You can use tools like [crontab.guru](https://crontab.guru/) to verify your schedule.

-----

Feel free to contribute or report issues on the GitHub repository\!
