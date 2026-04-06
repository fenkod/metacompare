import argparse
import requests

from helpers import get_deck_source_and_id


def get_scryfall_deck(deck_id):
    api_url = f"https://api.scryfall.com/decks/{deck_id}/export/json"

    try:
        r = requests.get(api_url)
        r.raise_for_status()
    except Exception as err:
        raise (err)
    else:
        deck_details = r.json()

    return deck_details


def process_scryfall(url, deck_id):
    deck_details = get_scryfall_deck(deck_id)

    ### TODO: Extract Format
    format = "pauper"

    main = {}
    main_noland = {}
    total = {}
    total_noland = {}

    maindeck = deck_details.get('entries', {}).get('mainboard', [])
    sideboard = deck_details.get('entries', {}).get('sideboard', [])

    for card in maindeck:
        if card.get('card_digest'):
            main[card.get('card_digest', {}).get('name', None)] = card.get('count', None)
            total[card.get('card_digest', {}).get('name', None)] = card.get('count', None)
            if not card.get('card_digest', {}).get('type_line', None).startswith('Basic'):
                main_noland[card.get('card_digest', {}).get('name', None)] = card.get('count', None)
                total_noland[card.get('card_digest', {}).get('name', None)] = card.get('count', None)

    for card in sideboard:
        if card.get('card_digest'):
            card_name = card.get('card_digest', {}).get('name', None)
            card_type = card.get('card_digest', {}).get('type_line', None)
            card_count = card.get('count', None)
            is_basic = True if card_type.startswith('Basic') else False

            if card_name in total and not is_basic:
                total[card_name] = total.get(card_name, 0) + card_count
                total_noland[card_name] = total_noland.get(card_name, 0) + card_count
            elif card_name in total and is_basic:
                total[card_name] = total.get(card_name, 0) + card_count
            elif card_name not in total and not is_basic:
                total[card_name] = card_count
                total_noland[card_name] = card_count
            else:
                total[card_name] = card_count

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
    source, deck_id = get_deck_source_and_id(url)
    if source == ("scryfall"):
        print(process_scryfall(url, deck_id))
    else:
        print("Non Scryfall link submitted")