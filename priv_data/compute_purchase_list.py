#!/usr/bin/env python3
"""Compute a purchase list across multiple commander decks, accounting for built decks.

Usage:
  python compute_purchase_list.py --owned Owned.csv --shop deck1 deck2 [--built deck3 deck4]

Example:
  python compute_purchase_list.py --owned Owned.csv --shop superfriends-esika \
    --built dark-dominion titan-convergence eternal-agony eternal-harvest \
           the-white-forge verdant-tide mutant-multiplication creeping-corruption
"""

import argparse
import csv
import json
import os
from collections import defaultdict
from pathlib import Path

BASIC_LANDS = {
    'Plains', 'Island', 'Swamp', 'Mountain', 'Forest', 'Wastes',
    'Snow-Covered Plains', 'Snow-Covered Island', 'Snow-Covered Swamp',
    'Snow-Covered Mountain', 'Snow-Covered Forest',
}

DECK_DATA_DIR = Path(__file__).resolve().parent.parent / 'data' / 'commanders'


def parse_owned_csv(filename: str) -> dict[str, int]:
    cards: dict[str, int] = defaultdict(int)
    with open(filename, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get('Name', row.get('name', '')).strip()
            if not name:
                continue
            qty = int(row.get('Quantity', row.get('quantity', '1')).strip() or '1')
            cards[name] += qty
    result = dict(cards)
    for name, qty in list(result.items()):
        if ' // ' in name:
            front_face = name.split(' // ')[0]
            if front_face not in result:
                result[front_face] = qty
    return result


def load_deck(deck_id: str) -> dict | None:
    path = DECK_DATA_DIR / deck_id / 'deck.json'
    if not path.exists():
        print(f"Warning: deck '{deck_id}' not found at {path}")
        return None
    with open(path, 'r') as f:
        return json.load(f)


def get_deck_card_names(deck: dict) -> set[str]:
    names = set()
    if deck.get('commander'):
        names.add(deck['commander'])
    if deck.get('partner'):
        names.add(deck['partner'])
    for card in deck.get('decklist', []):
        name = card.get('name', '')
        if name and name not in BASIC_LANDS:
            names.add(name)
    names -= BASIC_LANDS
    return names


def main():
    parser = argparse.ArgumentParser(description='Compute MTG deck purchase list')
    parser.add_argument('--owned', required=True, help='Path to owned cards CSV')
    parser.add_argument('--shop', nargs='+', required=True, help='Deck IDs to shop for')
    parser.add_argument('--built', nargs='*', default=[], help='Deck IDs already built')
    args = parser.parse_args()

    owned = parse_owned_csv(args.owned)

    built_claims: dict[str, int] = defaultdict(int)
    for deck_id in args.built:
        deck = load_deck(deck_id)
        if not deck:
            continue
        for name in get_deck_card_names(deck):
            built_claims[name] += 1

    shopping_needs: dict[str, int] = defaultdict(int)
    for deck_id in args.shop:
        deck = load_deck(deck_id)
        if not deck:
            continue
        for name in get_deck_card_names(deck):
            shopping_needs[name] += 1

    buy_list = []
    for name, needed in sorted(shopping_needs.items()):
        owned_qty = owned.get(name, 0)
        built_used = built_claims.get(name, 0)
        available = max(0, owned_qty - built_used)
        to_buy = max(0, needed - available)
        if to_buy > 0:
            buy_list.append((name, to_buy))

    if buy_list:
        for name, qty in buy_list:
            print(f'{qty}x {name}')
        print(f'\nTotal: {sum(q for _, q in buy_list)} cards')
    else:
        print('Nothing to buy — you own everything needed.')


if __name__ == '__main__':
    main()
