import re
import requests
import time
from urllib.parse import urlparse


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


def normalize_names_with_scryfall(cards):
    """Return {original: normalized} map using Scryfall's exact/fuzzy search."""
    mapping = {}
    headers = {
        "User-Agent": "metacompare_bot/1.0",
        "Accept": "application/json;q=0.9,*/*;q=0.8",
    }
    for card in cards:
        # Try exact match first
        r = requests.get("https://api.scryfall.com/cards/named", params={"exact": card}, headers=headers)
        if r.status_code != 200:
            # fallback to fuzzy match
            r = requests.get("https://api.scryfall.com/cards/named", params={"fuzzy": card}, headers=headers)
        mapping[card] = r.json().get("name", card) if r.status_code == 200 else card
        time.sleep(0.1)
    return mapping


def normalize_dict(d, mapping):
    return {mapping.get(k, k): v for k, v in d.items()}