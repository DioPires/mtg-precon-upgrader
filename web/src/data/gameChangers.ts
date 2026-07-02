// Official MTG Commander Game Changers list (53 cards, Feb 9 2026 update).
// Used by the Scrying Pool's Swap Analyzer to flag GC additions/removals.
// Source of truth: data/game-changers.json (port of legacy gv1-game-changers.js).

export const GAME_CHANGERS: readonly string[] = [
  'Ad Nauseam',
  'Ancient Tomb',
  'Aura Shards',
  'Biorhythm',
  "Bolas's Citadel",
  'Braids, Cabal Minion',
  'Chrome Mox',
  'Coalition Victory',
  'Consecrated Sphinx',
  'Crop Rotation',
  'Cyclonic Rift',
  'Demonic Tutor',
  'Drannith Magistrate',
  'Enlightened Tutor',
  'Farewell',
  'Fierce Guardianship',
  'Field of the Dead',
  'Force of Will',
  "Gaea's Cradle",
  'Gamble',
  'Gifts Ungiven',
  'Glacial Chasm',
  'Grand Arbiter Augustin IV',
  'Grim Monolith',
  'Humility',
  'Imperial Seal',
  'Intuition',
  "Jeska's Will",
  "Lion's Eye Diamond",
  'Mana Vault',
  "Mishra's Workshop",
  'Mox Diamond',
  'Mystical Tutor',
  'Narset, Parter of Veils',
  'Natural Order',
  'Necropotence',
  'Notion Thief',
  'Opposition Agent',
  'Orcish Bowmasters',
  'Panoptic Mirror',
  'Rhystic Study',
  'Seedborn Muse',
  "Serra's Sanctum",
  'Smothering Tithe',
  'Survival of the Fittest',
  "Teferi's Protection",
  'Tergrid, God of Fright',
  'The One Ring',
  'The Tabernacle at Pendrell Vale',
  "Thassa's Oracle",
  'Underworld Breach',
  'Vampiric Tutor',
  'Worldly Tutor',
];

export const GAME_CHANGERS_SET: ReadonlySet<string> = new Set(
  GAME_CHANGERS.map((n) => n.toLowerCase()),
);

export function isGameChanger(name: string | undefined | null): boolean {
  if (!name) return false;
  return GAME_CHANGERS_SET.has(name.toLowerCase());
}
