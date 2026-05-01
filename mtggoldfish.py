import argparse
import json
import re
import requests
from bs4 import BeautifulSoup
from collections import Counter
from lxml import html
from pathlib import Path
from urllib.parse import unquote
import xml.etree.ElementTree as ET
from helpers import (
    get_deck_source_and_id,
    normalize_names_with_scryfall,
    normalize_dict,
    load_name_map,
    save_name_map,
)


BASIC_LANDS = {
    "Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes",
    "Snow-Covered Plains", "Snow-Covered Island", "Snow-Covered Swamp",
    "Snow-Covered Mountain", "Snow-Covered Forest", "Snow-Covered Wastes",
}


def card_name_from_price_href(href: str) -> str | None:
    """
    Example:
      /price/the-list/147/thermo-alchemist
      -> Thermo-Alchemist

    This is a fallback. Prefer image alt/title when available.
    """
    if not href or "/price/" not in href:
        return None

    slug = href.rstrip("/").split("/")[-1]
    slug = unquote(slug)

    return slug.replace("-", " ").title()


def extract_card_name(a) -> str | None:
    """
    MTGGoldfish visual deck cards are usually image links.
    Best sources:
      1. img alt text
      2. img title
      3. anchor title
      4. href slug fallback
    """
    img = a.find("img")

    for attr_source in (img, a):
        if not attr_source:
            continue

        for attr in ("alt", "title", "data-card-name"):
            value = attr_source.get(attr)
            if value:
                # Handles alt text like: "Thermo-Alchemist [PLIST]"
                value = re.sub(r"\s+\[[^\]]+\]$", "", value).strip()
                if value and value.lower() not in {"image", "card"}:
                    return value

    return card_name_from_price_href(a.get("href"))


def parse_visual_deck_cards(soup: BeautifulSoup) -> tuple[dict, dict]:
    """
    Counts card links before and after the Sideboard heading.
    Visual page has one anchor/image per card copy.
    """
    main = Counter()
    sideboard = Counter()
    section = "main"

    # Start near the visual content. This keeps us from counting footer/card-popup links.
    header = soup.select_one(".deck-visual-header") or soup.find("h1")
    if not header:
        raise ValueError("Could not find visual deck header.")

    for el in header.find_all_next(["a", "h3", "h2"]):
        text = el.get_text(" ", strip=True).lower()

        if el.name in {"h2", "h3"} and text == "sideboard":
            section = "sideboard"
            continue

        # Stop before footer/popup junk.
        if text in {"layout footer", "card details"}:
            break

        if el.name != "a":
            continue

        href = el.get("href", "")
        if "/price/" not in href:
            continue

        name = extract_card_name(el)
        if not name:
            continue

        if section == "sideboard":
            sideboard[name] += 1
        else:
            main[name] += 1

    return dict(main), dict(sideboard)


def get_visual_deck_name_and_format(soup: BeautifulSoup) -> tuple[str | None, str | None]:
    name_el = soup.select_one("h1.deck-visual-header-title-name")
    if not name_el:
        name_el = soup.find("h1")

    deck_name = name_el.get_text(" ", strip=True) if name_el else None

    info_el = soup.select_one("p.deck-visual-header-title-info span")
    deck_format = None

    if info_el:
        info = info_el.get_text(" ", strip=True).replace("\xa0", " ")
        deck_format = info.split(",")[0].strip().lower()

    return deck_name, deck_format


def process_mtggoldfish(url, deck_id):
    visual_url = f"https://www.mtggoldfish.com/deck/visual/{deck_id}"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:149.0) "
            "Gecko/20100101 Firefox/149.0"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.mtggoldfish.com/",
    }

    session = requests.Session()
    session.headers.update(headers)

    r = session.get(visual_url, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    deck_name, deck_format = get_visual_deck_name_and_format(soup)
    main, sideboard = parse_visual_deck_cards(soup)

    total = dict(Counter(main) + Counter(sideboard))

    main_noland = {
        name: qty for name, qty in main.items()
        if name not in BASIC_LANDS
    }

    total_noland = {
        name: qty for name, qty in total.items()
        if name not in BASIC_LANDS
    }

    result = {
        "name": deck_name,
        "url": url,
        "main": main,
        "main_noland": main_noland,
        "deck": total,
        "deck_noland": total_noland,
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

    return deck_collection, deck_format


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


def process_mtggoldfish_old(url, deck_id):
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