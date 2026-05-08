import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Tokens } from '../../components/organisms/Tokens';
import type { DeckToken } from '../../data/types';

const SAMPLE: DeckToken[] = [
  {
    name: 'Eldrazi Scion',
    type_line: 'Token Creature — Eldrazi Scion',
    oracle_text: 'Sacrifice this creature: Add {C}.',
    power: '1',
    toughness: '1',
    colors: [],
    scryfall_id: '6ef7df0d-d7d6-463d-b452-32666973234a',
    image_uri: 'https://cards.scryfall.io/normal/scion.jpg',
    produced_by: ['Warping Wail', 'Eldrazi Spawner'],
  },
  {
    name: 'Spirit',
    type_line: 'Token Creature — Spirit',
    power: '2',
    toughness: '2',
    colors: [],
    image_uri: 'https://cards.scryfall.io/normal/spirit.jpg',
    produced_by: ['Ugin, the Ineffable'],
  },
];

describe('Tokens', () => {
  it('renders nothing when tokens is empty', () => {
    const { container } = render(<Tokens tokens={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders one token card per entry with name, type, P/T, and producers', () => {
    render(<Tokens tokens={SAMPLE} />);

    expect(screen.getByRole('heading', { name: /tokens/i })).toBeInTheDocument();
    expect(
      screen.getByText(new RegExp(`${SAMPLE.length} tokens? created by this deck`)),
    ).toBeInTheDocument();

    expect(screen.getByText('Eldrazi Scion')).toBeInTheDocument();
    expect(screen.getByText('Spirit')).toBeInTheDocument();
    expect(screen.getByText(/Token Creature — Eldrazi Scion/)).toBeInTheDocument();
    expect(screen.getAllByText(/1\/1/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/2\/2/).length).toBeGreaterThan(0);
  });

  it('exposes producer names with data-card-name for the hover layer', () => {
    const { container } = render(<Tokens tokens={SAMPLE} />);

    const warping = container.querySelector('[data-card-name="Warping Wail"]');
    expect(warping).not.toBeNull();
    expect(warping?.textContent).toBe('Warping Wail');

    const ugin = container.querySelector('[data-card-name="Ugin, the Ineffable"]');
    expect(ugin).not.toBeNull();
  });

  it('falls back to a stub frame when image_uri is missing', () => {
    const tokens: DeckToken[] = [
      {
        name: 'Treasure',
        type_line: 'Token Artifact — Treasure',
        produced_by: ['Dockside Extortionist'],
      },
    ];
    render(<Tokens tokens={tokens} />);
    expect(screen.getByText(/no frame/i)).toBeInTheDocument();
  });
});
