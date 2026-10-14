// Display names for deck.json's `primary_role` keys: the 15 keys of
// VALID_ROLES (scripts/compute_deck_metrics.py) and `other`, the role of a
// card without one. The deck guide (normalize.ts) and Card Atlas
// (cardAtlas.ts) both read this map. A key without an entry shows raw.

export const ROLE_LABEL: Record<string, string> = {
  land: 'Lands',
  ramp: 'Ramp',
  // One word: "Mana Fixing" takes two lines in the role chart above 560px.
  'mana-fixing': 'Fixing',
  'card-draw': 'Card Draw',
  counterspell: 'Counters',
  'removal-spot': 'Spot Removal',
  'removal-board': 'Board Wipes',
  recursion: 'Recursion',
  protection: 'Protection',
  payoff: 'Payoffs',
  threat: 'Threats',
  wincon: 'Win-Cons',
  engine: 'Engine',
  tutor: 'Tutors',
  utility: 'Utility',
  other: 'Other',
};
