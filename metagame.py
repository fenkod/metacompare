import argparse
import json
import re
import requests
from bs4 import BeautifulSoup
from lxml import html
from pathlib import Path

from helpers import load_name_map, save_name_map, normalize_names_with_scryfall, normalize_dict


BLOCK_MARKERS = ("Attention Required", "Not Acceptable", "Cloudflare", "Request blocked")


def get_mtggoldfish_metagame(format="pauper"):
    mtggoldfish_pauper_metagame_url = 'https://www.mtggoldfish.com/metagame/{0}/full#paper'.format(format)
    mtggoldfish_base_url = 'https://www.mtggoldfish.com'

    try:
        r = requests.get(mtggoldfish_pauper_metagame_url)
        r.raise_for_status()
    except Exception as e:
        raise e
    else:
        content = r.content.decode()

    parsed_page = BeautifulSoup(content, 'html.parser')

    metagame_list = []

    special_divs = parsed_page.find_all('div', {'class': 'archetype-tile-title'})
    for text in special_divs:
        download = text.find_all('a', href=re.compile('#online$'))
        for text in download:
            hrefText = (text['href'])
            metagame_list.append(
                {
                    "name": text.text,
                    "url": mtggoldfish_base_url + hrefText
                }
            )

    return metagame_list


def generate_metagame_collections(metagame_list, format="pauper"):
    basic_lands = [
        'Plains', 'Island', 'Swamp', 'Mountain', 'Forest', 'Wastes',
        'Snow-Covered Plains', 'Snow-Covered Island', 'Snow-Covered Swamp',
        'Snow-Covered Mountain', 'Snow-Covered Forest', 'Snow-Covered Wastes',
    ]

    name_map = load_name_map()
    num_archtypes = len(metagame_list)
    count = 1

    for metagame_deck in metagame_list:
        try:
            print(f"{count} of {num_archtypes}: Downloading archetype details for {metagame_deck.get('name')}")
            deck_request = requests.get(metagame_deck.get('url'))
            deck_request.raise_for_status()
        except Exception as e:
            raise e
        else:
            deck_content = deck_request.content.decode()

        parsed_deck = BeautifulSoup(deck_content, "html.parser")

        main = {}
        main_noland = {}
        total = {}
        total_noland = {}

        current_section = None

        card_breakdown_header = parsed_deck.find(
            ['h1', 'h2', 'h3', 'h4'],
            string=re.compile(r'Card Breakdown', re.I)
        )

        node = card_breakdown_header.find_next() if card_breakdown_header else parsed_deck.find()

        while node:
            if node.name in ('h1', 'h2', 'h3', 'h4'):
                heading_text = node.get_text(" ", strip=True)

                if re.search(r'^Sideboard$', heading_text, re.I):
                    current_section = "sideboard"
                elif re.search(
                    r'^(Creatures|Spells|Planeswalkers|Artifacts|Enchantments|Battles|Lands)$',
                    heading_text,
                    re.I
                ):
                    current_section = "main"
                elif re.search(r'^(Similar Decks|Decks|More from|Footer)$', heading_text, re.I):
                    break

            if node.name == 'div' and 'spoiler-card' in (node.get('class') or []):
                name_el = node.find('span', {'class': 'price-card-invisible-label'})
                qty_el = node.find('p', {'class': 'archetype-breakdown-featured-card-text'})

                if name_el and qty_el and current_section in {"main", "sideboard"}:
                    card_name = name_el.get_text(strip=True)
                    qty_text = qty_el.get_text(" ", strip=True)

                    m = re.match(r'^\s*([0-9]+(?:\.[0-9]+)?)\s+in\s+', qty_text)
                    if m:
                        card_quantity = float(m.group(1))

                        if current_section == "main":
                            main[card_name] = main.get(card_name, 0) + card_quantity
                            if card_name not in basic_lands:
                                main_noland[card_name] = main_noland.get(card_name, 0) + card_quantity

                        total[card_name] = total.get(card_name, 0) + card_quantity
                        if card_name not in basic_lands:
                            total_noland[card_name] = total_noland.get(card_name, 0) + card_quantity

            node = node.find_next()

        # Only normalize cards not already seen in prior archetypes
        new_cards = set(total.keys()) - set(name_map.keys())
        if new_cards:
            normalize_names_with_scryfall(new_cards, existing_map=name_map)

        metagame_deck['main'] = normalize_dict(main, name_map)
        metagame_deck['main_noland'] = normalize_dict(main_noland, name_map)
        metagame_deck['total'] = normalize_dict(total, name_map)
        metagame_deck['total_noland'] = normalize_dict(total_noland, name_map)

        # backward compatibility
        metagame_deck['deck'] = metagame_deck['total']
        metagame_deck['deck_noland'] = metagame_deck['total_noland']

        count += 1

    save_name_map(name_map)

    with open(f'{format}_metagame.json', 'w') as outfile:
        json.dump(metagame_list, outfile, indent=2, ensure_ascii=False)

    return metagame_list


def pull_mtggoldfish_metagame(format="pauper"):
    metagame_file = Path("{0}_metagame.json".format(format))

    try:
        load_path = metagame_file.resolve(strict=True)
    except FileNotFoundError:
        metagame_list = get_mtggoldfish_metagame(format)
        metagame_collection = generate_metagame_collections(metagame_list, format)
    else:
        with open(load_path, 'r') as infile:
            metagame_collection = json.load(infile)

    return metagame_collection


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--format', required=True)
    args = parser.parse_args()
    format = (args.format).lower()
    try:
        metagame_list = get_mtggoldfish_metagame(format)
        metagame_collection = generate_metagame_collections(metagame_list, format)
        print(metagame_collection)
    except Exception as e:
        raise e