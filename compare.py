# This is a sample Python script.
import argparse
import math
from collections import Counter
from urllib.parse import quote

from helpers import get_deck_source_and_id
from moxfield import process_moxfield
from archidekt import process_archidekt
from scryfall import process_scryfall
from mtggoldfish import process_mtggoldfish
from tappedout import process_tappedout
from metagame import pull_mtggoldfish_metagame


# Function dispatch map
SOURCE_FUNCTION_MAP = {
    "moxfield": process_moxfield,
    "scryfall": process_scryfall,
    "archidekt": process_archidekt,
    "mtggoldfish": process_mtggoldfish,
    "tappedout": process_tappedout,
}

ALLOWED_FORMATS = ["pauper", "pioneer", "modern", "standard", "premodern", "legacy", "vintage"]


# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.


def counter_cosine_similarity(c1, c2):
    terms = set(c1).union(c2)
    dotprod = sum(c1.get(k, 0) * c2.get(k, 0) for k in terms)
    magA = math.sqrt(sum(c1.get(k, 0) ** 2 for k in terms))
    magB = math.sqrt(sum(c2.get(k, 0) ** 2 for k in terms))
    return dotprod / (magA * magB)


def compare_deck_to_mtggoldfish_metagame(deck_dict, metagame_collection):
    comparison_list = []

    for metadeck in metagame_collection:
        if metadeck["deck"]:
            deck = counter_cosine_similarity(Counter(deck_dict['main']), Counter(metadeck['main']))
            deck_noland = counter_cosine_similarity(Counter(deck_dict['main_noland']), Counter(metadeck['main_noland']))
            comparison_list.append(
                {
                    "metadeck": metadeck["name"],
                    "url": metadeck["url"],
                    "similarity": deck,
                    "similarity_noland": deck_noland
                }
            )

    sorted_list = sorted(comparison_list, key=lambda d: d['similarity_noland'], reverse=True)
    sorted_list = sorted_list[:5]

    comparison_dict = {
        "name": deck_dict["name"],
        "url": deck_dict["url"],
        "similarity_scores": sorted_list
    }

    return comparison_dict


def generate_text_response_mtggoldfish(comparison_dict):
    similarity_scores = comparison_dict['similarity_scores']
    text_response = f"""[{comparison_dict['name']}](<{comparison_dict['url']}>)
    Similarity Scores to [{similarity_scores[0]['metadeck']}](<{similarity_scores[0]['url']}>): With Basics {round(similarity_scores[0]['similarity'] * 100, 3)}%; Without Basics {round(similarity_scores[0]['similarity_noland'] * 100, 3)}%
    Similarity Scores to [{similarity_scores[1]['metadeck']}](<{similarity_scores[1]['url']}>): With Basics {round(similarity_scores[1]['similarity'] * 100, 3)}%; Without Basics {round(similarity_scores[1]['similarity_noland'] * 100, 3)}%
    Similarity Scores to [{similarity_scores[2]['metadeck']}](<{similarity_scores[2]['url']}>): With Basics {round(similarity_scores[2]['similarity'] * 100, 3)}%; Without Basics {round(similarity_scores[2]['similarity_noland'] * 100, 3)}%
    Similarity Scores to [{similarity_scores[3]['metadeck']}](<{similarity_scores[3]['url']}>): With Basics {round(similarity_scores[3]['similarity'] * 100, 3)}%; Without Basics {round(similarity_scores[3]['similarity_noland'] * 100, 3)}%
    Similarity Scores to [{similarity_scores[4]['metadeck']}](<{similarity_scores[4]['url']}>): With Basics {round(similarity_scores[4]['similarity'] * 100, 3)}%; Without Basics {round(similarity_scores[4]['similarity_noland'] * 100, 3)}%
"""
    return text_response



def run_generator_from_url(url):
    source, deck_id = get_deck_source_and_id(url)
    if source not in SOURCE_FUNCTION_MAP:
        return "This tool only supports Moxfield, Archidekt, MtgGoldfish, Scryfall, and TappedOut deck links at this time"
    else:
        deck_dict, format = SOURCE_FUNCTION_MAP[source](url, deck_id)
        if format in ALLOWED_FORMATS:
            metagame_collection = pull_mtggoldfish_metagame(format)
            comparison_dict = compare_deck_to_mtggoldfish_metagame(deck_dict, metagame_collection)
            return generate_text_response_mtggoldfish( comparison_dict)
        else:
            return f"This tool only supports these formats: {ALLOWED_FORMATS}"


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    args = parser.parse_args()
    url = args.url
    try:
        print(run_generator_from_url(url))
    except Exception as e:
        print(e)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
