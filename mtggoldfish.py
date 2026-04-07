import argparse
import json
import re
import requests
from bs4 import BeautifulSoup
from lxml import html
from pathlib import Path
import xml.etree.ElementTree as ET

from helpers import get_deck_source_and_id, normalize_names_with_scryfall, normalize_dict


def get_goldfish_deck_name_visual(url: str) -> str:
    # Extract deck ID and force the "visual" page
    m = re.search(r"/deck/(?:visual/)?(\d+)", url)
    if not m:
        raise ValueError("Could not find a deck ID in the URL.")
    deck_id = m.group(1)
    visual_url = f"https://www.mtggoldfish.com/deck/visual/{deck_id}"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.mtggoldfish.com/",
    }

    r = requests.get(visual_url, headers=headers, timeout=20)
    r.raise_for_status()
    tree = html.fromstring(r.text)

    # --- Format ---
    info_parts = tree.xpath(
        '//p[contains(@class, "deck-visual-header-title-info")]//span/text()'
    )
    format_value = None

    if info_parts:
        raw_text = " ".join(info_parts).strip()

        # Replace non-breaking spaces with normal spaces
        cleaned = raw_text.replace('\xa0', ' ')

        # Split on comma and take first element
        format_value = cleaned.split(',')[0].strip()

    # 1) Exact target: <h1 class="deck-visual-header-title-name ..."><span>NAME</span></h1>
    xp_span = '//h1[contains(@class, "deck-visual-header-title-name")]//span/text()'
    parts = [t.strip() for t in tree.xpath(xp_span) if t.strip()]
    if parts:
        return " ".join(parts), format_value

    # 2) Fallback: any text inside that H1 (handles markup changes)
    xp_h1_text = '//h1[contains(@class, "deck-visual-header-title-name")]//text()'
    parts = [t.strip() for t in tree.xpath(xp_h1_text) if t.strip()]
    if parts:
        return " ".join(parts), format_value

    # 3) Fallback: Open Graph title from HEAD
    og = tree.xpath('/html/head/meta[@property="og:title"]/@content')
    if og and og[0].strip():
        return og[0].strip(), format_value

    # 4) Last resort: <title>
    title = tree.xpath('/html/head/title/text()')
    if title and title[0].strip():
        return title[0].strip(), format_value

    raise ValueError("Deck name not found on the visual page.")


def process_mtggoldfish(url, deck_id):
    api_url = f"https://www.mtggoldfish.com/deck/download/{deck_id}?output=dek&type=online"

    try:
        r = requests.get(api_url)
        r.raise_for_status()
    except Exception as err:
        raise (err)

    basic_lands = [
        'Plains', 'Island', 'Swamp', 'Mountain', 'Forest', 'Wastes',
        'Snow-Covered Plains', 'Snow-Covered Island', 'Snow-Covered Swamp', 'Snow-Covered Mountain',
        'Snow-Covered Forest', 'Snow-Covered Wastes',
    ]

    root = ET.fromstring(r.content)

    deck_name, format = get_goldfish_deck_name_visual(url)

    if format:
        format = format.lower()

    main = {}
    main_noland = {}
    total = {}
    total_noland = {}

    for card in root.findall("Cards"):
        name = card.get("Name")
        qty = int(card.get("Quantity"))
        sideboard = card.get("Sideboard") == "true"

        # main dict — only non-sideboard
        if not sideboard:
            main[name] = main.get(name, 0) + qty
            if name not in basic_lands:
                main_noland[name] = main_noland.get(name, 0) + qty

        # total dict — all cards
        total[name] = total.get(name, 0) + qty
        if name not in basic_lands:
            total_noland[name] = total_noland.get(name, 0) + qty

    result = {
        'name': deck_name,
        'url': url,
        'main': main,
        'main_noland': main_noland,
        'deck': total,
        'deck_noland': total_noland,
    }

    all_cards = set(result["deck"].keys())
    name_map = normalize_names_with_scryfall(all_cards)

    deck_collection = {
        "name": result["name"],
        "url": result["url"],
        "main": normalize_dict(result["main"], name_map),
        "main_noland": normalize_dict(result["main_noland"], name_map),
        "deck": normalize_dict(result["deck"], name_map),
        "deck_noland": normalize_dict(result["deck_noland"], name_map),
    }

    return deck_collection, format


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    args = parser.parse_args()
    url = args.url
    try:
        source, deck_id = get_deck_source_and_id(url)
        if source == "mtggoldfish":
            deck_collection, format = process_mtggoldfish(url, deck_id)
            print({"format": format, "deck_collection": deck_collection})
        else:
            print("This is not a deck hosted by MtgGoldfish")
    except Exception as err:
        raise err