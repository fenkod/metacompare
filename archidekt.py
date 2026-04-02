import argparse
import requests


def strip_archidekt_id(url):
    return url.split('/')[-2]


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


def generate_archidekt_sets(deck_details, url):

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

    return {
        'name': deck_details['name'],
        'url': url,
        'main': main,
        'main_noland': main_noland,
        'deck': total,
        'deck_noland': total_noland,
    }


def process_archidekt(url, deck_id):
    deck_details = get_archidekt_deck(deck_id)

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

    return {
        'name': deck_details['name'],
        'url': url,
        'main': main,
        'main_noland': main_noland,
        'deck': total,
        'deck_noland': total_noland,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    args = parser.parse_args()
    url = args.url
    deck_id = strip_archidekt_id(url)
    deck_details = get_archidekt_deck(deck_id)
    print(get_archidekt_deck(deck_details, url))