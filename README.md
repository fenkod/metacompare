# Metacompare

## Features
- Loads and parses decklists from Moxfield, Archidekt, MTGGoldfish, TappedOut, and Scryfall,
- Gathers metagame details from MTGGoldfish. Currently supports Pauper, Standard, Modern, Premodern, Legacy, Vintage, and Pioneer.
- Normalizes card names to comply with UFT-8 formatting and to properly include Universes Within cardnames to Universes Beyond reprints (when necessary).
- Uses cosine similarity scoring to compare a decklist against the established metagame for a given format.

## Requirements
- Python 3.12+ recommended

## Recommended Environment
Using a virtual environment is strongly recommended.

### Mac and Linux

```bash
python -m venv .venv
source .venv/bin/activate
```

### Windows (Power Shell)

```shell
python -m venv .venv
.venv\Scripts\activate
```

## Installation

```bash
git clone https://github.com/fenkod/metacompare.git
cd metacompare
```
Create your virtual environment now if you choose to follow the recommendation. Once done, install the dependencies.

```bash
pip install -r requirements.txt
```

### Updating the .env file

If you intend on using Moxfield as a source for decklists, you will need to acquire API credentials from the Moxfield team (reach out to them on Discord.) Once you have credentials, make a copy of the `template.env` file named `.env` and update the `MOXFIELD_UA_HEADER` value to include your credentials.

## Usage

### Refreshing Metagames

Each metagame needs to be refreshed manually and will take several minutes to process. During this step, the Scryfall API is used to normalize card named for any card not already included in the `scryfall_name_map.json` file.

Individual metagames are stored in a separate file `{format_name}_metagame.json`.

```bash
python metagame.py --format {format_name}
```

### Comparing a Deck to the Metagame

The `compare.py` script will compare the supplied decklist with the format of the decklist as configured on the deck building website.

```bash
python compare.py --url {decklist_url}
```

#### Example Comparison

```bash
python compare.py --url https://moxfield.com/decks/Towvhi0hUUm1zS9YOVVd4w

[Warped Devotion](<https://moxfield.com/decks/Towvhi0hUUm1zS9YOVVd4w>)
    Similarity Scores to [UB Psychatog](<https://www.mtggoldfish.com/archetype/premodern-ub-psychatog#online>): With Basics 42.001%; Without Basics 34.418%
    Similarity Scores to [Dimir Stiflenought](<https://www.mtggoldfish.com/archetype/premodern-dimir-stiflenought#online>): With Basics 35.243%; Without Basics 28.244%
    Similarity Scores to [Dimir Midrange](<https://www.mtggoldfish.com/archetype/premodern-dimir-midrange#online>): With Basics 41.003%; Without Basics 23.625%
    Similarity Scores to [Mono-Black Midrange](<https://www.mtggoldfish.com/archetype/premodern-mono-black-midrange-ba3cf91e-df0c-47d4-8068-bbfc327bd0dc#online>): With Basics 40.648%; Without Basics 22.813%
    Similarity Scores to [Rakdos Midrange](<https://www.mtggoldfish.com/archetype/premodern-rakdos-midrange#online>): With Basics 31.0%; Without Basics 20.803%
```

#### Reading the Comparison

The tool only compares the mainboard against the mainboard of the metagame. You'll get 2 results for each of the 5 decks that have the closest match to your deck.
- `With Basics`: This is the entire decklist, inclusive of basic lands.
- `Without Basics`: This is the entire decklist with basic lands removed from both the decklist and the metagame lists.

## Disclaimer

This project is an independent tool and is not affiliated with or endorsed by Wizards of the Coast, MTGGoldfish, Moxfield, TappedOut, Archidekt, or Scryfall.

Magic: The Gathering and all related properties are trademarks of Wizards of the Coast.