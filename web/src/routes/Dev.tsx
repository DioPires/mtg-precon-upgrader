import { ManaCost } from '../components/atoms/ManaCost';
import { GV1ManaPips } from '../components/atoms/GV1ManaPips';
import { CardTile, type CardTileCard } from '../components/molecules/CardTile';
import { GV1CommanderArt } from '../components/molecules/GV1CommanderArt';

const SAMPLE_TILES: CardTileCard[] = [
  { n: 'Sol Ring', mv: '{1}', type: 'Artifact', note: 'Fast mana — turn-1 enabler.' },
  { n: 'Lightning Bolt', mv: '{R}', type: 'Instant', price: '$0.50' },
  { n: 'Cyclonic Rift', mv: '{1}{U}', type: 'Instant', gc: true },
  { n: 'Forest', mv: 'LAND', type: 'Basic Land — Forest' },
];

const SAMPLE_COMMANDER = { name: 'Atraxa, Praetors\' Voice', slug: 'atraxa-praetors-voice' };

export function Dev() {
  return (
    <div className="gv1-dev" style={{ padding: '24px', display: 'grid', gap: '32px' }}>
      <header>
        <h1 className="gv1-serif-xl">/_dev — Phase 1 atoms & molecules</h1>
        <p className="gv1-mono-xs gv1-dim">
          Smoke surface for ManaCost, GV1ManaPips, CardTile, GV1CommanderArt, and the global card-hover layer.
        </p>
      </header>

      <section aria-labelledby="dev-mana-cost">
        <h2 id="dev-mana-cost" className="gv1-serif-md">ManaCost</h2>
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center', flexWrap: 'wrap' }}>
          <ManaCost mv="{2}{R}{R}" />
          <ManaCost mv="{W}{U}{B}{R}{G}" />
          <ManaCost mv="{C}{C}" />
          <ManaCost mv="LAND" />
          <ManaCost mv="—" />
          <ManaCost />
        </div>
      </section>

      <section aria-labelledby="dev-pips">
        <h2 id="dev-pips" className="gv1-serif-md">GV1ManaPips</h2>
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center', flexWrap: 'wrap' }}>
          <GV1ManaPips colors="🟢" />
          <GV1ManaPips colors="🔵⚫🔴" />
          <GV1ManaPips colors="⚪🔵⚫🔴🟢" />
          <GV1ManaPips colors="◇" />
        </div>
      </section>

      <section aria-labelledby="dev-card-tile">
        <h2 id="dev-card-tile" className="gv1-serif-md">CardTile</h2>
        <p className="gv1-mono-xs gv1-dim">
          Hover any tile to trigger the global card-hover layer. Live Scryfall art populates after the throttled fetch resolves.
        </p>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          {SAMPLE_TILES.map((card) => <CardTile key={card.n} card={card} size="md" />)}
        </div>
        <h3 className="gv1-serif-sm" style={{ marginTop: '16px' }}>sm</h3>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {SAMPLE_TILES.map((card) => <CardTile key={card.n} card={card} size="sm" />)}
        </div>
        <h3 className="gv1-serif-sm" style={{ marginTop: '16px' }}>lg</h3>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          {SAMPLE_TILES.slice(0, 2).map((card) => <CardTile key={card.n} card={card} size="lg" />)}
        </div>
      </section>

      <section aria-labelledby="dev-cmd-art">
        <h2 id="dev-cmd-art" className="gv1-serif-md">GV1CommanderArt</h2>
        <div style={{ maxWidth: '300px' }}>
          <GV1CommanderArt name={SAMPLE_COMMANDER.name} slug={SAMPLE_COMMANDER.slug} />
        </div>
      </section>
    </div>
  );
}
