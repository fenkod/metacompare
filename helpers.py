import json
import re
import requests
import time
from pathlib import Path
from urllib.parse import urlparse


NAME_MAP_CACHE_FILE = Path(__file__).resolve().parent / "scryfall_name_map.json"


def get_deck_source_and_id(url):
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path = parsed.path

    if "moxfield.com" in domain:
        match = re.search(r"/decks/([\w\-]+)", path)
        if match:
            return "moxfield", match.group(1)

    elif "scryfall.com" in domain:
        match = re.search(r"/decks/([0-9a-fA-F\-]{36})", path)
        if match:
            return "scryfall", match.group(1)

    elif "archidekt.com" in domain:
        match = re.search(r"/decks/(\d+)", path)
        if match:
            return "archidekt", match.group(1)

    elif "mtggoldfish.com" in domain:
        match = re.search(r"/deck/(?:visual/)?(\d+)", path)
        if match:
            return "mtggoldfish", match.group(1)

    elif "tappedout.net" in domain:
        return "tappedout", None

    else:
        return None, None


def load_name_map(cache_file=NAME_MAP_CACHE_FILE):
    """Load persisted Scryfall normalization cache from disk."""
    cache_path = Path(cache_file)

    if not cache_path.exists():
        return {}

    with open(cache_path, "r", encoding="utf-8") as infile:
        data = json.load(infile)

    return data if isinstance(data, dict) else {}


def save_name_map(name_map, cache_file=NAME_MAP_CACHE_FILE):
    """Persist Scryfall normalization cache to disk."""
    cache_path = Path(cache_file)

    with open(cache_path, "w", encoding="utf-8") as outfile:
        json.dump(name_map, outfile, indent=2, sort_keys=True, ensure_ascii=False)


def normalize_names_with_scryfall(cards, existing_map=None):
    """Return {original: normalized} map using Scryfall's exact/fuzzy search.

    - Only looks up cards not already in existing_map
    - Respects the /cards/named rate limit
    - Retries with backoff on 429
    """
    mapping = existing_map if existing_map is not None else {}

    headers = {
        "User-Agent": "metacompare_bot/1.0",
        "Accept": "application/json;q=0.9,*/*;q=0.8",
    }

    min_interval = 0.55  # stay below 2 requests/sec
    last_request_time = 0.0

    def rate_limited_get(url, params):
        nonlocal last_request_time

        now = time.time()
        elapsed = now - last_request_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)

        backoff = 1.0

        while True:
            response = requests.get(url, params=params, headers=headers)

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                wait_time = float(retry_after) if retry_after else backoff
                time.sleep(wait_time)
                backoff = min(backoff * 2, 10.0)
                continue

            last_request_time = time.time()
            return response

    for card in cards:
        if card in mapping:
            continue

        r = rate_limited_get(
            "https://api.scryfall.com/cards/named",
            {"exact": card}
        )

        if r.status_code != 200:
            r = rate_limited_get(
                "https://api.scryfall.com/cards/named",
                {"fuzzy": card}
            )

        mapping[card] = r.json().get("name", card) if r.status_code == 200 else card

    return mapping


def normalize_dict(d, mapping):
    return {mapping.get(k, k): v for k, v in d.items()}