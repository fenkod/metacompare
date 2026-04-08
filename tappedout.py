import argparse
import re
import requests
from collections import Counter

from helpers import (
    get_deck_source_and_id,
    normalize_names_with_scryfall,
    normalize_dict,
    load_name_map,
    save_name_map,
)


def process_tappedout(url, deck_id=None):
    try:
        r = requests.get(url)
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise e

    html = r.content.decode("utf-8")

    # --- Deck name + MTGA deck text ---
    mtga = re.search(r'<textarea[^>]+id="mtga-textarea"[^>]*>(.*?)</textarea>', html, flags=re.S)
    mtga_text = mtga.group(1) if mtga else ""
    name_match = re.search(r'^\s*Name\s+(.+)$', mtga_text, flags=re.M)
    name = name_match.group(1).strip() if name_match else "Unknown"

    # Try the format badge first: /mtg-deck-builder/pauper/
    format_match = re.search(
        r'href="/mtg-deck-builder/([^"/]+)/"[^>]*>\s*([A-Za-z0-9 _-]+)\s*</a>',
        html,
        flags=re.I,
    )

    if format_match:
        format = format_match.group(1).strip().lower()
    else:
        # Fallback to the <title>, e.g. "Tandem Solfatara (Pauper MTG Deck)"
        title_match = re.search(r"<title>.*?\((.*?)\s+MTG Deck\)</title>", html, flags=re.I | re.S)
        format = title_match.group(1).strip().lower() if title_match else None

    # Split MTGA block into main vs sideboard lines
    lines = [ln.rstrip() for ln in mtga_text.strip().splitlines()]
    deck_start = lines.index("Deck") if "Deck" in lines else None
    side_start = lines.index("Sideboard") if "Sideboard" in lines else None
    maybe_start = lines.index("Maybeboard") if "Maybeboard" in lines else None

    if deck_start is None:
        main_lines = []
        side_lines = []
    else:
        # Main deck runs from "Deck" to the first later section marker, if any
        section_ends = [i for i in [side_start, maybe_start] if i is not None and i > deck_start]
        main_end = min(section_ends) if section_ends else len(lines)
        main_lines = lines[deck_start + 1:main_end]

        # Sideboard runs from "Sideboard" to "Maybeboard" or EOF
        if side_start is not None:
            side_end = maybe_start if maybe_start is not None and maybe_start > side_start else len(lines)
            side_lines = lines[side_start + 1:side_end]
        else:
            side_lines = []

    # Parse "Nx Card Name (...) ..." lines
    def parse_section(lines):
        counts = Counter()
        for line in lines:
            line = line.strip()
            if not re.match(r'^\d+x?\s', line):
                continue
            m = re.match(r'^(\d+)x?\s+(.+?)(?:\s*\(.*)?$', line)
            if m:
                qty = int(m.group(1))
                card = m.group(2).strip()
                counts[card] += qty
        return counts

    main = parse_section(main_lines)
    side = parse_section(side_lines)

    # Basic lands filter
    basic_lands = [
        'Plains', 'Island', 'Swamp', 'Mountain', 'Forest', 'Wastes',
        'Snow-Covered Plains', 'Snow-Covered Island', 'Snow-Covered Swamp', 'Snow-Covered Mountain',
        'Snow-Covered Forest', 'Snow-Covered Wastes',
    ]

    def drop_basics(counter: Counter):
        c = Counter(counter)
        for b in basic_lands:
            c.pop(b, None)
        return c

    # Totals
    deck = main + side

    result = {
        "name": name,
        "url": url,
        "main": dict(sorted(main.items())),
        "main_noland": dict(sorted(drop_basics(main).items())),
        "deck": dict(sorted(deck.items())),
        "deck_noland": dict(sorted(drop_basics(deck).items())),
    }

    all_cards = set(result["deck"].keys())
    name_map = load_name_map()
    name_map = normalize_names_with_scryfall(all_cards, name_map)
    save_name_map(name_map)

    deck_collection = {
        "name": result["name"],
        "url": result["url"],
        "main": normalize_dict(result["main"], name_map),
        "main_noland": normalize_dict(result["main_noland"], name_map),
        "deck": normalize_dict(result["deck"], name_map),
        "deck_noland": normalize_dict(result["deck_noland"], name_map),
    }

    return deck_collection, format


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    args = parser.parse_args()
    url = args.url
    try:
        source, deck_id = get_deck_source_and_id(url)
        if source == "tappedout":
            deck_collection, format = process_tappedout(url, deck_id)
            print({"format": format, "deck_collection": deck_collection})
        else:
            print("This is not a deck hosted by TappedOut")
    except Exception as err:
        raise err