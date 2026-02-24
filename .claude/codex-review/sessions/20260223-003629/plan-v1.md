# Plan: Mana Simulation Results — New "Analytics" Tab

## Context

Three Monte Carlo mana simulation scripts in `scripts/` run 100K games per deck but only print to stdout. The deck guide page is already long. Instead of adding more scroll depth, we create a new **"Analytics" tab** for simulation visualizations, keeping the existing Deck Statistics in the guide tab (it's lightweight and contextually useful there).

---

## Step 1: Create simulation export script

**New file:** `scripts/export_simulation_results.py`

Import each sim module under a namespace (they share function names like `run_simulation`, `merge_stats`, etc.):
```python
import mana_simulation as sim_titan
import mana_simulation_rakdos as sim_rakdos
import mana_simulation_grixis as sim_grixis
```

For each deck:
1. Load deck.json + card-metadata.json
2. Build decklist, classify cards, compute static analysis (avg CMC, composition)
3. Run simulation via multiprocessing (reuse existing `_run_chunk` + `merge_stats`)
4. Extract summary stats (medians, percentiles, percentages) from raw arrays
5. Write to `data/commanders/{id}/simulation.json`

**Module import safety:** Each sim uses module-level constants (ROCK_DEFS, etc.) and either module-global `_land_set` (titan) or local `land_set` (rakdos/grixis). No module-level side effects — safe to import. Run sequentially to avoid cross-contamination of titan's global `_land_set`.

**JSON schema per deck:**
```json
{
  "metadata": { "numGames": 100000, "numTurns": 10, "generatedAt": "2026-02-23" },
  "deckComposition": { "totalCards": 99, "lands": 36, "rocks": 10, "spells": 53, "avgCmc": 3.45 },
  "manaByTurn": { "1": { "median": 1, "p25": 1, "p75": 2, "mean": 1.3 }, ... },
  "mulliganStats": { "keptFirst": 85.2, "freeMulligan": 12.1, "paidMulligan": 2.7 },
  "openingHand": { "landDistribution": { "0": 0.5, "1": 5.2, ... } },
  "commanderTiming": { "name": "...", "cmc": 6, "byTurn": { "3": 25.3, ... }, "medianTurn": 4 },
  "colorBalance": null | { "colors": [...], "pipDemandVsSupply": { "demand": {...}, "supply": {...} } },
  "curveEfficiency": { "castableByTurn": { "1": 25.3, ... }, "curveOutRate": 12.5 },
  "specialMetrics": { "cascadeReadiness": {...} | null, "etbTapped": {...} | null },
  "assessment": { "manaAdequacy": "adequate", "mulliganVerdict": "acceptable", "commanderTiming": "on curve" }
}
```

**Error handling:** Process each deck independently; if one fails, continue with others and report at end.

## Step 2: Run all 3 simulations

`python scripts/export_simulation_results.py` — ~30-60s per deck, generates:
- `data/commanders/titan-convergence/simulation.json`
- `data/commanders/eternal-agony/simulation.json`
- `data/commanders/sauron-the-dark-lord/simulation.json`

---

## Step 3: Add "Analytics" tab to website

**File:** `index.html`

### 3a. Tab button (after line ~3581)

```html
<button class="view-toggle-btn" data-view="analytics" role="tab" aria-selected="false" id="tab-analytics">
  <svg><!-- bar-chart-2 icon --></svg>
  Analytics
</button>
```

Always enabled (not like Playtest which is disabled until deck loads). Existing `initViewToggle()` (line 6736) already queries all `.view-toggle-btn` dynamically — no listener changes needed.

### 3b. Analytics view container (after line 4090, before loading/footer)

Insert `<div id="analytics-view" style="display: none;">` between the closing `</div>` of playtest-view (line 4090) and `<div class="loading">` (line 4092).

```html
<div id="analytics-view" style="display: none;">
  <div id="analytics-content" style="display: none;">
    <div class="analytics-header">
      <h2 class="guide-section-title">Mana Base Simulation</h2>
      <span class="sim-badge">100,000 games simulated</span>
    </div>

    <div class="stats-panel sim-chart-panel">
      <h3 class="stats-panel-title">Mana Production by Turn</h3>
      <div class="sim-chart-container" id="sim-mana-chart"></div>
    </div>

    <div class="sim-metrics-grid" id="sim-metrics-grid"></div>

    <details class="sim-details">
      <summary>Detailed Breakdown</summary>
      <div class="sim-details-grid" id="sim-details-content"></div>
    </details>
  </div>

  <div id="analytics-no-deck" class="analytics-empty-state">
    <p>Select a deck to view analytics</p>
  </div>

  <div id="analytics-no-data" class="analytics-empty-state" style="display: none;">
    <p>No simulation data available for this deck.</p>
    <p class="sim-hint">Run <code>python scripts/export_simulation_results.py</code> to generate.</p>
  </div>
</div>
```

### 3c. `switchView()` changes (line ~6682)

**Current:** 2-way branch (playtest / guide). **New:** 3-way.

```js
// Add to variable declarations (line ~6692):
const analyticsView = document.getElementById('analytics-view');

// Add to "hide all" block (line ~6701-6705):
analyticsView.style.display = 'none';

// Replace the if/else with if/else if/else:
if (view === 'playtest') {
  // existing playtest code unchanged
} else if (view === 'analytics') {
  analyticsView.style.display = 'block';
  selectorSection.style.display = '';
  if (currentPrecon) {
    upgradeOverview.style.display = 'block';
    renderAnalyticsView();
  }
  if (currentPreconId) {
    history.replaceState(null, '', `#view=analytics&precon=${encodeURIComponent(currentPreconId)}`);
  } else {
    window.location.hash = 'view=analytics';
  }
} else {
  // existing guide code unchanged
}
```

### 3d. `selectPrecon()` changes (line ~5335-5346)

**Current:**
```js
if (currentView !== 'playtest') mainContent.style.display = 'grid';
if (currentView === 'playtest') initPlaytest(); else renderContent();
```

**New:**
```js
if (currentView === 'guide') {
  mainContent.style.display = 'grid';
  renderContent();
} else if (currentView === 'playtest') {
  initPlaytest();
} else if (currentView === 'analytics') {
  document.getElementById('analytics-view').style.display = 'block';
  renderAnalyticsView();
}
```

### 3e. `initializeApp()` URL hash (line ~7493)

**Current:** Only checks `view=playtest`. **Add** `view=analytics` handling:
```js
const isAnalyticsView = hash.startsWith('view=analytics');
if (isAnalyticsView) {
  // Parse precon from hash, load deck, switch to analytics
  const params = {};
  hash.split('&').forEach(part => {
    const [k, v] = part.split('=');
    if (k && v) params[k] = decodeURIComponent(v);
  });
  const aPrecon = params.precon || preconToLoad;
  if (aPrecon && allDecks.some(d => d.id === aPrecon)) {
    preconSelect.value = aPrecon;
    currentView = 'analytics';
    await selectPrecon(aPrecon);
    switchView('analytics');
  }
  return;
}
```

Note: `updateUrlHash()` (line 5886) already handles non-guide views generically — no changes needed.

### 3f. CSS additions (~130 lines)

Reuse existing vars and patterns:

```css
/* Analytics view layout */
.analytics-header       { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }
.analytics-empty-state  { text-align: center; padding: 60px 20px; color: var(--text-secondary); }

/* Sim badge */
.sim-badge {
  background: var(--accent-purple-dim);
  color: var(--accent-purple);
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 600;
}

/* Chart panel */
.sim-chart-panel        { padding: 20px; margin-bottom: 20px; }
.sim-chart-container    { width: 100%; height: 200px; }
.sim-chart-container svg { width: 100%; height: 100%; }

/* SVG styles */
.sim-area-band          { fill: var(--accent-purple); opacity: 0.15; }
.sim-median-line        { fill: none; stroke: var(--accent-purple); stroke-width: 2.5; }
.sim-median-dot         { fill: var(--accent-purple); r: 4; cursor: pointer; }
.sim-median-dot:hover   { r: 6; filter: drop-shadow(0 0 6px var(--accent-purple)); }
.sim-chart-gridline     { stroke: var(--border-subtle); stroke-width: 0.5; }
.sim-chart-label        { font-size: 11px; fill: var(--text-secondary); }

/* Metrics grid */
.sim-metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}
.sim-metric-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  padding: 20px;
  text-align: center;
}

/* Commander timing ring */
.sim-ring { width: 100px; height: 100px; border-radius: 50%; margin: 0 auto 12px; position: relative; }
.sim-ring-value { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font-size: 1.4rem; font-weight: 700; }

/* Mulligan donut */
.sim-donut { width: 100px; height: 100px; border-radius: 50%; margin: 0 auto 12px; position: relative; }
.sim-donut-center { position: absolute; inset: 15px; border-radius: 50%; background: var(--bg-surface); display: flex; align-items: center; justify-content: center; }

/* Counter */
.sim-counter-value { font-size: 2rem; font-weight: 700; color: var(--accent-purple); }
.sim-metric-label  { font-size: 0.85rem; color: var(--text-secondary); margin-top: 8px; }

/* Color balance bars */
.sim-color-bar-row    { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.sim-color-bar-label  { width: 60px; font-size: 0.8rem; }
.sim-color-bar-track  { flex: 1; height: 12px; background: var(--bg-primary); border-radius: 6px; overflow: hidden; }
.sim-color-bar-fill   { height: 100%; border-radius: 6px; transition: width 0.8s ease-out; }

/* Details section */
.sim-details           { margin-top: 20px; }
.sim-details summary   { cursor: pointer; color: var(--accent-purple); font-weight: 600; padding: 12px; }
.sim-details-grid      { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; padding: 16px 0; }
@media (max-width: 768px) { .sim-details-grid { grid-template-columns: 1fr; } }

/* Assessment badges */
.sim-assessment-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 600;
}
.sim-assessment-good  { background: var(--accent-green-dim); color: var(--accent-green); }
.sim-assessment-warn  { background: var(--accent-gold-dim); color: var(--accent-gold); }
.sim-assessment-bad   { background: var(--accent-red-dim); color: var(--accent-red); }

/* Animations */
@keyframes sim-fade-up { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
.sim-animate { animation: sim-fade-up 0.5s ease-out forwards; }
```

### 3g. JS additions (~250 lines)

**Data layer:**
```js
const simulationCache = {};

async function loadSimulationData(preconId) {
  if (simulationCache[preconId]) return simulationCache[preconId];
  try {
    const resp = await fetch(`data/commanders/${preconId}/simulation.json`);
    if (!resp.ok) return null;
    const data = await resp.json();
    simulationCache[preconId] = data;
    return data;
  } catch { return null; }
}
```

**Main render:**
```js
async function renderAnalyticsView() {
  if (!currentPrecon) {
    document.getElementById('analytics-content').style.display = 'none';
    document.getElementById('analytics-no-deck').style.display = '';
    document.getElementById('analytics-no-data').style.display = 'none';
    return;
  }

  document.getElementById('analytics-no-deck').style.display = 'none';
  const simData = await loadSimulationData(currentPreconId);
  if (!simData) {
    document.getElementById('analytics-content').style.display = 'none';
    document.getElementById('analytics-no-data').style.display = '';
    return;
  }

  document.getElementById('analytics-no-data').style.display = 'none';
  document.getElementById('analytics-content').style.display = '';

  renderManaRampChart(simData.manaByTurn, simData.metadata.numTurns);
  renderSimMetrics(simData);
  renderDetailedBreakdown(simData);
  setupSimAnimations();
}
```

**Chart + metric renderers:**
- `renderManaRampChart(manaByTurn, numTurns)` — SVG with viewBox, P25-P75 area path, median line path, dots, gridlines, labels
- `renderSimMetrics(simData)` — builds metric cards HTML into `#sim-metrics-grid`:
  - Commander ring (conic-gradient)
  - Mulligan donut (conic-gradient)
  - Curve-out counter
  - Color balance bars (only if `colorBalance !== null`)
- `renderDetailedBreakdown(simData)` — opening hand bars, commander by-turn, castable by-turn, assessment badges
- `setupSimAnimations()` — IntersectionObserver + counter animations

---

## Critical files

| File | Action |
|------|--------|
| `scripts/export_simulation_results.py` | **Create** |
| `scripts/mana_simulation.py` | Read/import |
| `scripts/mana_simulation_rakdos.py` | Read/import |
| `scripts/mana_simulation_grixis.py` | Read/import |
| `data/commanders/*/simulation.json` | **Create** (3 files) |
| `index.html` | **Edit** — tab, HTML, CSS, JS |

## Reuse from existing code

| What | Location | Reuse |
|------|----------|-------|
| `.stats-panel` CSS | line ~1783 | Chart and metric card containers |
| `.stats-panel-title` | line ~1790 | Panel headers |
| `.view-toggle-btn` CSS | line ~2787 | Tab button (inherits all styling) |
| `switchView()` | line ~6682 | Extend with analytics branch |
| `initViewToggle()` | line ~6736 | Already dynamic — no changes needed |
| `selectPrecon()` | line ~5290 | Add analytics rendering branch |
| `updateUrlHash()` | line ~5886 | Already handles non-guide views generically |
| `escapeHtml()` | existing | Safe text rendering |
| `loadPreconData()` pattern | line ~5260 | Pattern for async fetch + cache |
| `cardMetadataCache` | existing | Card CMC lookups |

## Verification

1. `python scripts/export_simulation_results.py` — generates 3 JSON files
2. `python -c "import json; [json.load(open(f'data/commanders/{d}/simulation.json')) for d in ['titan-convergence','eternal-agony','sauron-the-dark-lord']]"`
3. Open site — 3 tabs: "Commander Decks", "Playtest", "Analytics"
4. Click Analytics with no deck → "Select a deck" message
5. Select each deck → sim visualizations render
6. SVG chart: P25-P75 band, median line, hover tooltips on dots
7. Commander ring animates to target %
8. Mulligan donut: 3 color segments
9. Color balance hidden for Titan Convergence, visible for Rakdos/Grixis
10. "Detailed Breakdown" expands with tables/bars
11. Mobile responsive: metrics grid stacks
12. URL `#view=analytics&precon=titan-convergence` loads correctly on refresh
13. Tab switching preserves deck selection
14. Guide tab Deck Statistics unchanged
15. Playtest tab unchanged
