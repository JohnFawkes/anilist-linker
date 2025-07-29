from plexapi.server import PlexServer
import os
import re
import requests
import json
import time
import dotenv
import argparse # Import argparse for command-line arguments

# --- Load Environment Variables from .env file ---
dotenv.load_dotenv()

# --- Configuration (Now primarily via Environment Variables from .env or system) ---
PLEX_URL = os.getenv('PLEX_URL', 'YOUR_PLEX_URL')
PLEX_TOKEN = os.getenv('PLEX_TOKEN', 'YOUR_PLEX_TOKEN')


# --- Script Settings ---
MAKE_CHANGES = os.getenv('PLEX_MAKE_CHANGES', 'False').lower() == 'true'
DEBUG = os.getenv('PLEX_DEBUG', 'False').lower() == 'true' # New Debug variable

TARGET_TV_SHOW_LIBRARIES_STR = os.getenv('PLEX_TARGET_TV_SHOW_LIBRARIES', '')
TARGET_TV_SHOW_LIBRARIES_LIST = [lib.strip() for lib in TARGET_TV_SHOW_LIBRARIES_STR.split(',') if lib.strip()]

TARGET_MOVIE_LIBRARIES_STR = os.getenv('PLEX_TARGET_MOVIE_LIBRARIES', '')
TARGET_MOVIE_LIBRARIES_LIST = [lib.strip() for lib in TARGET_MOVIE_LIBRARIES_STR.split(',') if lib.strip()]

# URL for the anime_ids.json file
ANIME_IDS_JSON_URL = os.getenv('ANIME_IDS_JSON_URL', 'https://raw.githubusercontent.com/Kometa-Team/Anime-IDs/refs/heads/master/anime_ids.json')

# --- Anilist Settings ---
ANILIST_API_URL = os.getenv('ANILIST_API_URL', "https://graphql.anilist.co")
ANILIST_PREFIX_FORMAT = os.getenv('ANILIST_PREFIX_FORMAT', "[Anilist: {anilist_url}]\n")
# Updated regex: now uses \/? to make the final slash in the URL optional.
EXISTING_ANILIST_PREFIX_CHECK_PATTERN = os.getenv('ANILIST_PREFIX_CHECK_PATTERN', r"^\[Anilist: https:\/\/anilist\.co\/anime\/\d+\/?\]\s*")

# --- Rate Limit Settings ---
MAX_ANILIST_RETRIES = int(os.getenv('ANILIST_MAX_RETRIES', '5'))
DEFAULT_RETRY_AFTER_SECONDS = int(os.getenv('ANILIST_DEFAULT_RETRY_AFTER', '60'))
# Set the Anilist API call rate: 1 call every 2 seconds
ANILIST_MIN_INTERVAL_SECONDS = 2.0 

# Global variable for anime_ids data
# Now stores pre-processed lookup maps
ANIME_IDS_DATA = {
    'tmdb_to_anilist': {},
    'tvdb_to_anilist': {},
    'imdb_to_anilist': {}
}
# Global list to store titles that could not be matched
unmatched_items = []

def print_debug(message):
    """Prints a debug message only if DEBUG is True."""
    if DEBUG:
        print(f"    [DEBUG] {message}")

def fetch_and_process_anime_ids_json(url):
    """
    Fetches the anime_ids.json file from a URL and pre-processes its content
    into optimized lookup dictionaries (TMDB, TVDB, IMDb to Anilist).
    """
    try:
        print(f"Attempting to download anime IDs from: {url}")
        response = requests.get(url)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        raw_json_data = response.json()
        print("✅ Successfully downloaded anime_ids.json. Pre-processing for faster lookups...")

        tmdb_map = {}
        tvdb_map = {}
        imdb_map = {}
        
        # Iterate through the raw JSON data to build lookup maps
        for anidb_id_str, mappings in raw_json_data.items():
            anilist_id = mappings.get('anilist_id')
            if anilist_id is None: # Skip entries without an Anilist ID
                continue

            # Populate TMDB map (checking both movie and show IDs)
            tmdb_show_id = mappings.get('tmdb_show_id')
            if tmdb_show_id is not None and isinstance(tmdb_show_id, int):
                tmdb_map[tmdb_show_id] = anilist_id

            tmdb_movie_id = mappings.get('tmdb_movie_id')
            if tmdb_movie_id is not None and isinstance(tmdb_movie_id, int):
                tmdb_map[tmdb_movie_id] = anilist_id
            
            # Populate TVDB map
            tvdb_id = mappings.get('tvdb_id')
            if tvdb_id is not None and isinstance(tvdb_id, int):
                tvdb_map[tvdb_id] = anilist_id
            
            # Populate IMDb map
            imdb_id = mappings.get('imdb_id')
            if imdb_id is not None and isinstance(imdb_id, str):
                imdb_map[imdb_id] = anilist_id
        
        print(f"✅ Pre-processing complete. Loaded {len(tmdb_map)} TMDB, {len(tvdb_map)} TVDB, {len(imdb_map)} IMDb mappings.")
        return {
            'tmdb_to_anilist': tmdb_map,
            'tvdb_to_anilist': tvdb_map,
            'imdb_to_anilist': imdb_map
        }

    except requests.exceptions.RequestException as e:
        print(f"❌ Error downloading {url}: {e}")
        return None
    except json.JSONDecodeError:
        print(f"❌ Error: Could not decode JSON from {url}. Ensure it's valid JSON.")
        return None
    except Exception as e:
        print(f"❌ An unexpected error occurred while fetching/processing {url}: {e}")
        return None

def extract_all_external_ids_from_guids(item, item_title=""):
    """
    Extracts all available external IDs (TMDB, TVDB, IMDb) from Plex item's GUIDs list.
    Returns a dictionary of found IDs, e.g., {'tmdb': 123, 'tvdb': 456, 'imdb': 'tt789'}.
    """
    guids_to_check = item.guids if hasattr(item, 'guids') and item.guids else [getattr(item, 'guid', None)]

    if not guids_to_check or guids_to_check == [None]:
        print_debug(f"No GUIDs found for item '{item_title}'.")
        return {}

    found_ids = {}
    print_debug(f"Examining GUIDs for '{item_title}': {[g.id if hasattr(g, 'id') else g for g in guids_to_check]}")

    for guid_obj in guids_to_check:
        guid_id = guid_obj.id if hasattr(guid_obj, 'id') else str(guid_obj)

        if guid_id.startswith('plex://'):
            continue

        match_tmdb = re.search(r'tmdb:\/\/(\d+)', guid_id)
        if match_tmdb:
            tmdb_id = int(match_tmdb.group(1))
            found_ids['tmdb'] = tmdb_id
            print_debug(f"Found TMDB ID '{tmdb_id}' in GUID '{guid_id}'.")

        match_tvdb = re.search(r'tvdb:\/\/(\d+)', guid_id)
        if match_tvdb:
            tvdb_id = int(match_tvdb.group(1))
            found_ids['tvdb'] = tvdb_id
            print_debug(f"Found TVDB ID '{tvdb_id}' in GUID '{guid_id}'.")

        match_imdb = re.search(r'imdb:\/\/(tt\d+)', guid_id)
        if match_imdb:
            imdb_id = match_imdb.group(1)
            found_ids['imdb'] = imdb_id
            print_debug(f"Found IMDb ID '{imdb_id}' in GUID '{guid_id}'.")
    
    if not found_ids:
        print(f"    [INFO] No recognizable TMDB, TVDB, or IMDb ID formats found in GUIDs for '{item_title}'.")
    else:
        print(f"    [INFO] Found external IDs for '{item_title}': {found_ids}")
    return found_ids


def find_anilist_id_from_json(external_id_type, external_id_value):
    """
    Searches the pre-processed ANIME_IDS_DATA for an Anilist ID using the provided external ID.
    Performs a direct dictionary lookup on the appropriate map.
    """
    if not ANIME_IDS_DATA or not ANIME_IDS_DATA.get(f'{external_id_type}_to_anilist'):
        print(f"    [WARNING] Anime ID data for '{external_id_type}' not properly loaded. Cannot find Anilist ID.")
        return None
    
    print_debug(f"Performing direct lookup in pre-processed maps for {external_id_type.upper()} ID '{external_id_value}' (type: {type(external_id_value)})...")

    # Select the correct lookup map based on external_id_type
    lookup_map = ANIME_IDS_DATA.get(f'{external_id_type}_to_anilist')
    
    if lookup_map:
        anilist_found_id = lookup_map.get(external_id_value)
        if anilist_found_id:
            print_debug(f"Direct match found for {external_id_type.upper()} ID '{external_id_value}'! Anilist ID: {anilist_found_id}")
        else:
            print_debug(f"No direct match found in {external_id_type.upper()} map for ID '{external_id_value}'.")
        return anilist_found_id
    else:
        print(f"    [INFO] No lookup map available for {external_id_type.upper()}.")
        return None


def search_anilist_by_id(anilist_id, title_for_logging, attempt=1):
    """
    Searches Anilist for an anime by its Anilist ID and returns its siteUrl if found.
    Handles rate limiting with retries and proactive pausing.
    """
    if attempt > MAX_ANILIST_RETRIES:
        print(f"    [ERROR] Max retries ({MAX_ANILIST_RETRIES}) exceeded for Anilist ID '{anilist_id}' (Plex title: '{title_for_logging}'). Giving up.")
        return None

    query = """
    query ($id: Int) {
      Media (id: $id, type: ANIME) {
        title {
          romaji
          english
          native
        }
        siteUrl
      }
    }
    """
    variables = {
        'id': anilist_id
    }
    
    try:
        response = requests.post(ANILIST_API_URL, json={'query': query, 'variables': variables})
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        data = response.json()

        # --- Always print Rate Limit Info ---
        x_ratelimit_limit = response.headers.get('x-ratelimit-limit')
        x_ratelimit_remaining = response.headers.get('x-ratelimit-remaining')

        if x_ratelimit_limit and x_ratelimit_remaining:
            try:
                remaining_requests = int(x_ratelimit_remaining)
                limit_requests = int(x_ratelimit_limit)
                print(f"    [ANILIST API] Rate Limit - Limit: {limit_requests}, Remaining: {remaining_requests} for ID '{anilist_id}'.")

                if remaining_requests <= 5: # Proactively pause when remaining requests are low
                    print(f"    [PROACTIVE RATE LIMIT] Anilist remaining requests ({remaining_requests}) low. Pausing for {DEFAULT_RETRY_AFTER_SECONDS} seconds to reset rate limit.")
                    time.sleep(DEFAULT_RETRY_AFTER_SECONDS)

            except ValueError:
                print(f"    [WARNING] Could not parse Anilist rate limit headers (Limit: '{x_ratelimit_limit}', Remaining: '{x_ratelimit_remaining}').")
        else:
            print("    [WARNING] Anilist rate limit headers (x-ratelimit-limit, x-ratelimit-remaining) not found in response.")
        # --- End Proactive Rate Limit Check ---

        # --- Enforce 1 request per 2.0 seconds limit ---
        time.sleep(ANILIST_MIN_INTERVAL_SECONDS)


        if data and data.get('data') and data['data'].get('Media') and data['data']['Media'].get('siteUrl'):
            media = data['data']['Media']
            
            # Simple check to ensure we got a valid media object back
            if not media.get('title'):
                print(f"    [INFO] Anilist result for ID '{anilist_id}' missing 'title' key or it is None. Skipping.")
                return None

            return media['siteUrl']
        else:
            print(f"    [INFO] No Anilist data or siteUrl found for ID '{anilist_id}'.")
            return None

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            retry_after = e.response.headers.get('Retry-After')
            wait_time = DEFAULT_RETRY_AFTER_SECONDS # Initialize with our fallback default

            print(f"    [RATE LIMIT] 429 Too Many Requests for ID '{anilist_id}'.")
            if retry_after:
                try:
                    parsed_retry_after = int(retry_after)
                    wait_time = parsed_retry_after # Use Anilist's explicit instruction
                    print(f"    [RATE LIMIT] Found 'Retry-After' header: '{retry_after}'. Using this value.")
                except ValueError:
                    print(f"    [WARNING] Could not parse 'Retry-After' header '{retry_after}'. Using configured default wait time ({DEFAULT_RETRY_AFTER_SECONDS}s).")
            else:
                print(f"    [WARNING] 'Retry-After' header not found. Using configured default wait time ({DEFAULT_RETRY_AFTER_SECONDS}s).")

            print(f"    [RATE LIMIT] Waiting for {wait_time} seconds before retrying ID '{anilist_id}' (Attempt {attempt}/{MAX_ANILIST_RETRIES})...")
            time.sleep(wait_time)
            return search_anilist_by_id(anilist_id, title_for_logging, attempt + 1) # Retry the request
        else:
            print(f"    [ERROR] HTTP Error {e.response.status_code} for ID '{anilist_id}': {e}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"    [ERROR] Anilist API request failed for ID '{anilist_id}': {e}")
        return None
    except json.JSONDecodeError:
        print(f"    [ERROR] Could not decode JSON response from Anilist for ID '{anilist_id}'.")
        return None
    except Exception as e:
        print(f"    [ERROR] An unexpected error occurred during Anilist search for ID '{anilist_id}': {e}")
        return None

def process_plex_item(item, item_type="Item"):
    """
    Processes a single Plex item (TV Show or Movie) to add Anilist link to its summary.
    This now involves getting all available external IDs, trying them in order (TMDB > TVDB > IMDb),
    looking up Anilist ID, then querying Anilist API.
    """
    try:
        print(f"Processing {item_type}: '{item.title}'")
        current_summary = item.summary if item.summary else ""
        
        # Check if Anilist link is already present at the beginning of the summary
        if re.match(EXISTING_ANILIST_PREFIX_CHECK_PATTERN, current_summary):
            print(f"[*] {item_type} '{item.title}': Summary already has an Anilist prefix. Skipping.")
            return

        # 1. Get all available external IDs from Plex item
        all_external_ids = extract_all_external_ids_from_guids(item, item.title)
        
        if not all_external_ids:
            print(f"    [INFO] No external IDs found in Plex GUIDs for '{item.title}'. Skipping.")
            unmatched_items.append(f"{item_type}: {item.title} (No external ID found in Plex GUIDs)")
            return

        anilist_id = None
        used_id_type = None
        used_id_value = None

        # Try TMDB first
        if 'tmdb' in all_external_ids:
            tmdb_id = all_external_ids['tmdb']
            print(f"    [LOOKUP] Attempting Anilist lookup using TMDB ID: {tmdb_id} for '{item.title}'.")
            anilist_id = find_anilist_id_from_json('tmdb', tmdb_id)
            if anilist_id:
                used_id_type = 'tmdb'
                used_id_value = tmdb_id

        # If TMDB failed, try TVDB
        if not anilist_id and 'tvdb' in all_external_ids:
            tvdb_id = all_external_ids['tvdb']
            print(f"    [LOOKUP] TMDB lookup failed or not available. Attempting Anilist lookup using TVDB ID: {tvdb_id} for '{item.title}'.")
            anilist_id = find_anilist_id_from_json('tvdb', tvdb_id)
            if anilist_id:
                used_id_type = 'tvdb'
                used_id_value = tvdb_id

        # If TVDB failed, try IMDb
        if not anilist_id and 'imdb' in all_external_ids:
            imdb_id = all_external_ids['imdb']
            print(f"    [LOOKUP] TVDB lookup failed or not available. Attempting Anilist lookup using IMDb ID: {imdb_id} for '{item.title}'.")
            anilist_id = find_anilist_id_from_json('imdb', imdb_id)
            if anilist_id:
                used_id_type = 'imdb'
                used_id_value = imdb_id

        if not anilist_id:
            print(f"    [INFO] No Anilist ID found in fetched data for any of the available external IDs ({all_external_ids}) for '{item.title}'. Skipping.")
            unmatched_items.append(f"{item_type}: {item.title} (No Anilist ID found in JSON for any external ID: {all_external_ids})")
            return

        print(f"    [Anilist ID] Found Anilist ID: {anilist_id} using {used_id_type.upper()} ID: {used_id_value} for '{item.title}'.")

        # 3. Search Anilist API using Anilist ID to get the URL
        print(f"    [Anilist] Querying Anilist API for ID '{anilist_id}'...")
        anilist_url = search_anilist_by_id(anilist_id, item.title)

        if anilist_url:
            prefix_to_add = ANILIST_PREFIX_FORMAT.format(anilist_url=anilist_url)
            new_summary = prefix_to_add + current_summary
            
            # Ensure no extra leading newlines are introduced by prefixing an empty summary
            new_summary = new_summary.lstrip('\n') 

            if MAKE_CHANGES:
                print(f"[MODIFIED] {item_type} '{item.title}': Prepending Anilist link: {anilist_url}")
                item.editSummary(new_summary)
                item.reload() # Reload to confirm change if needed
                print(f"    New Summary (Plex will show first 100 chars): {item.summary[:100]}...")
            else:
                print(f"[DRY RUN] {item_type} '{item.title}': Would prepend Anilist link: {anilist_url}")
                if not current_summary:
                    print(f"    Original Summary was EMPTY.")
                else:
                    print(f"    Original Summary: '{current_summary}'")
                print(f"    Proposed Full Summary: '{new_summary}'") # Show the full proposed new summary explicitly
        else:
            print(f"    [INFO] No Anilist URL found via API for ID '{anilist_id}' for '{item.title}' ({item_type}).")
            unmatched_items.append(f"{item_type}: {item.title} (No Anilist URL found via API for ID {anilist_id})")

    except Exception as e:
        print(f"[ERROR] {item_type} '{item.title}': Could not process item. Error: {e}")


if __name__ == "__main__":
    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(description="Plex to Anilist Linker script.")
    parser.add_argument('-y', '--yes', action='store_true', 
                        help="Bypass the confirmation prompt for live runs (MAKE_CHANGES=True).")
    args = parser.parse_args()

    # Check if Plex URL/Token are still placeholders
    if PLEX_URL == 'YOUR_PLEX_URL' or PLEX_TOKEN == 'YOUR_PLEX_TOKEN':
        print("⚠️  Please configure your PLEX_URL and PLEX_TOKEN.")
        print("   Set them in a .env file (e.g., PLEX_URL='http://localhost:32400')")
        print("   or as system environment variables.")
        exit() # Exit if essential config is missing

    # --- Print Current Configuration ---
    print("\n--- Current Script Configuration ---")
    print(f"  Plex URL: {PLEX_URL}")
    print(f"  Make Changes (Dry Run): {MAKE_CHANGES}")
    print(f"  Debug Mode: {DEBUG}") # Display Debug status
    # Updated text to reflect new behavior
    print(f"  Target TV Show Libraries: {TARGET_TV_SHOW_LIBRARIES_LIST if TARGET_TV_SHOW_LIBRARIES_LIST else 'SKIPPED (empty)'}")
    print(f"  Target Movie Libraries: {TARGET_MOVIE_LIBRARIES_LIST if TARGET_MOVIE_LIBRARIES_LIST else 'SKIPPED (empty)'}")
    print(f"  Anilist IDs JSON URL: {ANIME_IDS_JSON_URL}")
    print(f"  Anilist API URL: {ANILIST_API_URL}")
    print(f"  Anilist Prefix Format: '{ANILIST_PREFIX_FORMAT.replace('{anilist_url}', 'https://anilist.co/anime/XXXX/')}'")
    print(f"  Anilist Prefix Check Pattern: '{EXISTING_ANILIST_PREFIX_CHECK_PATTERN}'")
    print(f"  Max Anilist Retries: {MAX_ANILIST_RETRIES}")
    print(f"  Default Retry After (seconds): {DEFAULT_RETRY_AFTER_SECONDS}")
    print(f"  Anilist Minimum Interval (seconds): {ANILIST_MIN_INTERVAL_SECONDS}")
    print("------------------------------------\n")

    # Load the anime_ids.json data once at the start from the URL
    print(f"Loading anime IDs from {ANIME_IDS_JSON_URL}...")
    # Call the new fetch_and_process function
    processed_data = fetch_and_process_anime_ids_json(ANIME_IDS_JSON_URL)
    if processed_data is None:
        print("Exiting due to error loading or processing anime_ids.json from URL.")
        exit()
    # Assign the processed data to the global variable
    ANIME_IDS_DATA = processed_data
    print(f"✅ Successfully loaded {len(ANIME_IDS_DATA['tmdb_to_anilist'])} TMDB, {len(ANIME_IDS_DATA['tvdb_to_anilist'])} TVDB, {len(ANIME_IDS_DATA['imdb_to_anilist'])} IMDb mappings.")


    if not MAKE_CHANGES:
        print("🚀 --- Starting DRY RUN (no changes will be made to Plex) --- 🚀")
        print("     Set PLEX_MAKE_CHANGES=True in your .env file or environment to apply changes.")
    else:
        print("🔥 --- Starting REAL RUN (changes WILL be made to Plex) --- 🔥")
        # Bypass prompt if -y or --yes argument is provided
        if args.yes:
            print("     Bypassing confirmation prompt due to -y/--yes flag.")
        else:
            proceed = input("     Are you ABSOLUTELY SURE you want to proceed? (yes/no): ")
            if proceed.lower() != 'yes':
                print("Aborted by user.")
                exit()

    try:
        print(f"\nAttempting to connect to Plex server at {PLEX_URL}...")
        plex = PlexServer(PLEX_URL, PLEX_TOKEN)
        print("✅ Successfully connected to Plex!\n")

        # --- Process TV Show Libraries ---
        print("\n--- Processing TV Show Libraries ---")
        all_tv_show_sections = [s for s in plex.library.sections() if s.type == 'show']
        
        if TARGET_TV_SHOW_LIBRARIES_LIST:
            tv_show_sections_to_scan = [s for s in all_tv_show_sections if s.title in TARGET_TV_SHOW_LIBRARIES_LIST]
            if not tv_show_sections_to_scan:
                print(f"No TV show libraries found matching your PLEX_TARGET_TV_SHOW_LIBRARIES: {TARGET_TV_SHOW_LIBRARIES_LIST}.")
                print("Please ensure the library names are exact (case-sensitive) as listed in Plex.")
                print("\n--- Detected TV Show Libraries in Plex (Copy Exact Names) ---")
                if all_tv_show_sections:
                    for section in all_tv_show_sections:
                        print(f"- '{section.title}'")
                else:
                    print("No TV show libraries of type 'show' found in your Plex server.")
                print("----------------------------------------------------------\n")
        else:
            tv_show_sections_to_scan = [] # Changed: If no targets, process none
            print("PLEX_TARGET_TV_SHOW_LIBRARIES is empty. Skipping ALL TV Show libraries.")


        if not tv_show_sections_to_scan:
            print("No TV show libraries to process. Skipping TV Show scan.")
        else:
            for section in tv_show_sections_to_scan:
                print(f"\nScanning TV Show Library: {section.title}")
                shows = section.all()
                if not shows:
                    print(f"No TV shows found in '{section.title}'.")
                    continue
                for i, show in enumerate(shows):
                    process_plex_item(show, item_type="TV Show")


        # --- Process Movie Libraries ---
        print("\n--- Processing Movie Libraries ---")
        all_movie_sections = [s for s in plex.library.sections() if s.type == 'movie']
        
        if TARGET_MOVIE_LIBRARIES_LIST:
            movie_sections_to_scan = [s for s in all_movie_sections if s.title in TARGET_MOVIE_LIBRARIES_LIST]
            if not movie_sections_to_scan:
                print(f"No Movie libraries found matching your PLEX_TARGET_MOVIE_LIBRARIES: {TARGET_MOVIE_LIBRARIES_LIST}.")
                print("Please ensure the library names are exact (case-sensitive) as listed in Plex.")
                print("\n--- Detected Movie Libraries in Plex (Copy Exact Names) ---")
                if all_movie_sections:
                    for section in all_movie_sections:
                        print(f"- '{section.title}'")
                else:
                    print("No Movie libraries of type 'movie' found in your Plex server.")
                print("----------------------------------------------------------\n")
        else:
            movie_sections_to_scan = [] # Changed: If no targets, process none
            print("PLEX_TARGET_MOVIE_LIBRARIES is empty. Skipping ALL Movie libraries.")


        if not movie_sections_to_scan:
            print("No movie libraries to process. Skipping Movie scan.")
        else:
            for section in movie_sections_to_scan:
                print(f"\nScanning Movie Library: {section.title}")
                movies = section.all()
                if not movies:
                    print(f"No movies found in '{section.title}'.")
                    continue
                for i, movie in enumerate(movies):
                    process_plex_item(movie, item_type="Movie")


        print("\n--- Script Finished ---")
        if not MAKE_CHANGES:
            print("Remember, this was a DRY RUN. No changes were saved to Plex.")
        else:
            print("Changes have been applied to Plex (if any items met the criteria).\n")
            print("Note: If you ran a dry run previously, some items might have been skipped if their summaries already matched the proposed changes.")

        # --- START OF UNMATCHED ITEMS OUTPUT ---
        if unmatched_items:
            print("\n--- Items for which Anilist link could not be determined ---")
            for item_info in unmatched_items:
                print(f"- {item_info}")
            print("--------------------------------------------------\n")
        else:
            print("\n🎉 All processed Plex items found a matching Anilist link (or were skipped as already linked).")
        # --- END OF UNMATCHED ITEMS OUTPUT ---

    except Exception as e:
        print(f"❌ An error occurred during the script execution: {e}")
