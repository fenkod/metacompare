import json
import re
import requests
from bs4 import BeautifulSoup
from lxml import html
from pathlib import Path


BLOCK_MARKERS = ("Attention Required", "Not Acceptable", "Cloudflare", "Request blocked")


def get_mtggoldfish_metagame():
    mtggoldfish_pauper_metagame_url = 'https://www.mtggoldfish.com/metagame/pauper/full#paper'
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


def generate_metagame_collections(metagame_list):
    for metagame_deck in metagame_list:
        try:
            deck_request = requests.get(metagame_deck.get('url'))
            deck_request.raise_for_status()
        except Exception as e:
            raise (e)
        else:
            deck_content = deck_request.content.decode()

        parsed_deck = BeautifulSoup(deck_content, "html.parser")

        deck = {}
        deck_landless = {}
        basic_lands = [
            'Plains', 'Island', 'Swamp', 'Mountain', 'Forest', 'Wastes',
            'Snow-Covered Plains', 'Snow-Covered Island', 'Snow-Covered Swamp', 'Snow-Covered Mountain',
            'Snow-Covered Forest', 'Snow-Covered Wastes',
        ]

        special_divs = parsed_deck.find_all('div', {'class': 'spoiler-card'})
        for card in special_divs:
            card_name = card.find('span', {'class': 'price-card-invisible-label'}).text
            card_quantity = float(
                card.find('p', {'class': "archetype-breakdown-featured-card-text"}).text.split(' in ')[0].strip('\n'))
            if card_name in deck.keys():
                deck[card_name] += card_quantity
                if card_name not in basic_lands:
                    deck_landless[card_name] += card_quantity
            else:
                deck[card_name] = card_quantity
                if card_name not in basic_lands:
                    deck_landless[card_name] = card_quantity

        metagame_deck['deck'] = deck
        metagame_deck['deck_noland'] = deck_landless

    with open('metagame.json', 'w') as outfile:
        json.dump(metagame_list, outfile, indent=2)

    return metagame_list


def pull_mtggoldfish_metagame():
    metagame_file = Path("metagame.json")

    try:
        load_path = metagame_file.resolve(strict=True)
    except FileNotFoundError:
        metagame_list = get_mtggoldfish_metagame()
        metagame_collection = generate_metagame_collections(metagame_list)
    else:
        with open(load_path, 'r') as infile:
            metagame_collection = json.load(infile)

    return metagame_collection


if __name__ == '__main__':
    metagame_list = get_mtggoldfish_metagame()
    metagame_collection = generate_metagame_collections(metagame_list)
    print(metagame_collection)