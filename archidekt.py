import argparse
import requests

from helpers import get_deck_source_and_id


ARCHIDEKT_FORMAT_MAP = {
    1: "standard",
    2: "modern",
    4: "legacy",
    5: "vintage",
    6: "pauper",
    15: "pioneer",
    22: "premodern",
}


def get_archidekt_deck(deck_id):
    api_base = "https://www.archidekt.com/api/decks/"

    try:
        r = requests.get(api_base + deck_id + '/')
        r.raise_for_status()
    except Exception as err:
        raise (err)
    else:
        deck_details = r.json()

    return deck_details


def process_archidekt(url, deck_id):
    deck_details = get_archidekt_deck(deck_id)

    format = ARCHIDEKT_FORMAT_MAP.get(deck_details['deckFormat'])

    main = {}
    main_noland = {}
    total = {}
    total_noland = {}

    for card in deck_details['cards']:
        if len({'Sideboard', 'Maybeboard'}.intersection(set(card.get('categories')))) == 0:
            main[card.get('card').get('oracleCard').get('name')] = int(card.get('quantity'))
            total[card.get('card').get('oracleCard').get('name')] = int(card.get('quantity'))
            if 'Basic' not in card.get('card').get('oracleCard').get('superTypes'):
                main_noland[card.get('card').get('oracleCard').get('name')] = int(card.get('quantity'))
                total_noland[card.get('card').get('oracleCard').get('name')] = int(card.get('quantity'))
        elif 'Sideboard' in card.get('categories'):
            total[card.get('card').get('oracleCard').get('name')] = int(card.get('quantity'))
            if 'Basic' not in card.get('card').get('oracleCard').get('superTypes'):
                total_noland[card.get('card').get('oracleCard').get('name')] = int(card.get('quantity'))

    deck_collection = {
        'name': deck_details['name'],
        'url': url,
        'main': main,
        'main_noland': main_noland,
        'deck': total,
        'deck_noland': total_noland,
    }

    return deck_collection, format


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    args = parser.parse_args()
    url = args.url
    try:
        deck_source, deck_id = get_deck_source_and_id(url)
        if deck_source == 'archidekt':
            deck_collection, format = process_archidekt(url, deck_id)
            print({"format": format, "deck_collection": deck_collection})
        else:
            print("This is not a deck hosted by Archidekt")
    except Exception as err:
        raise err