import argparse
import os
import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from helpers import get_deck_source_and_id

load_dotenv()


def get_moxfield_deck(deck_id):
    retry_strategy = Retry(
            total = 4,
            backoff_factor = 10,
            status_forcelist = [
                429,
                500,
                502,
                503,
                504
                ]
            )
    adapter = HTTPAdapter(max_retries = retry_strategy)
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
        #"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:127.0) Gecko/20100101 Firefox/127.0i",
        #"x-requested-by": os.getenv("MOXFIELD_HEADER"),
        "User-Agent": os.getenv("MOXFIELD_UA_HEADER"),
    }

    try:
        r = session.get(f'https://api2.moxfield.com/v3/decks/all/{deck_id}', headers=headers)
        r.raise_for_status()
    except Exception as e:
        raise (e)
    else:
        deck_output = r.json()

    return deck_output


def process_moxfield(url, deck_id):
    deck_output = get_moxfield_deck(deck_id)

    deck_name = deck_output["name"]
    format = deck_output["format"]
    maindeck = deck_output['boards'].get('mainboard')
    sideboard = deck_output['boards'].get('sideboard')

    maindeck_card_ids = list(maindeck.get('cards').keys())

    maindeck_set = {}
    maindeck_no_lands_set = {}
    total_set = {}
    total_no_lands_set = {}

    for card_id in maindeck_card_ids:
        card_name = maindeck.get('cards')[card_id].get('card').get('name')
        card_quantity = maindeck.get('cards')[card_id].get('quantity')
        maindeck_set[card_name] = card_quantity
        total_set[card_name] = card_quantity
        if not 'Basic Land' in maindeck.get('cards')[card_id].get('card').get('type_line'):
            maindeck_no_lands_set[card_name] = card_quantity
            total_no_lands_set[card_name] = card_quantity

    if sideboard:
        sideboard_card_ids = list(sideboard.get('cards').keys())
        for card_id in sideboard_card_ids:
            card_name = sideboard.get('cards')[card_id].get('card').get('name')
            card_quantity = sideboard.get('cards')[card_id].get('quantity')
            total_set[card_name] = card_quantity
            if not 'Basic Land' in sideboard.get('cards')[card_id].get('card').get('type_line'):
                total_no_lands_set[card_name] = card_quantity

    deck_collection = {
        "name": deck_name,
        "url": url,
        "main": maindeck_set,
        "main_noland": maindeck_no_lands_set,
        "deck": total_set,
        "deck_noland": total_no_lands_set
    }

    return deck_collection, format


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    args = parser.parse_args()
    url = args.url
    try:
        deck_source, deck_id = get_deck_source_and_id(url)
        if deck_source == 'moxfield':
            deck_collection, format = process_moxfield(url, deck_id)
            print({"format": format, "deck_collection": deck_collection})
        else:
            print("This is not a deck hosted by Moxfield")
    except Exception as e:
        print(e)
