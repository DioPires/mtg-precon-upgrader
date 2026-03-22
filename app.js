// === UTILITY FUNCTIONS ===
function debounce(fn, delay) {
  let timeoutId;
  return function(...args) {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn.apply(this, args), delay);
  };
}

function throttle(fn, limit) {
  let inThrottle;
  return function(...args) {
    if (!inThrottle) {
      fn.apply(this, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}


function getEffectiveCommander() {
  return currentDeck?.commander || '';
}

// === SECURITY: HTML ESCAPING ===
function escapeHtml(str) {
  if (typeof str !== 'string') return String(str ?? '');
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// === SECURITY: URL SANITIZATION ===
function sanitizeUrl(url) {
  if (typeof url !== 'string') return '#';
  const trimmed = url.trim();
  if (trimmed.startsWith('https://') || trimmed.startsWith('http://')) {
    return escapeHtml(trimmed);
  }
  return '#';
}

// === SOURCE ATTRIBUTION ===
function getSourceTypeIcon(type) {
  const icons = {
    'youtube': '<svg class="source-icon-youtube" viewBox="0 0 24 24" fill="currentColor"><path d="M23.5 6.2s-.2-1.6-.9-2.3c-.9-.9-1.8-.9-2.3-1C17 2.6 12 2.6 12 2.6s-5 0-8.3.3c-.5.1-1.4.1-2.3 1-.7.7-.9 2.3-.9 2.3S.2 8.1.2 10v1.8c0 1.9.3 3.8.3 3.8s.2 1.6.9 2.3c.9.9 2 .9 2.5 1 1.8.2 7.6.2 7.6.2s5 0 8.3-.3c.5-.1 1.4-.1 2.3-1 .7-.7.9-2.3.9-2.3s.3-1.9.3-3.8V10c0-1.9-.3-3.8-.3-3.8zM9.5 15.5V8l6.5 3.8-6.5 3.7z"/></svg>',
    'edhrec': '<svg class="source-icon-edhrec" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>',
    'draftsim': '<svg class="source-icon-draftsim" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14,2 14,8 20,8"/></svg>',
    'article': '<svg class="source-icon-article" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/></svg>',
    'scryfall': '<svg class="source-icon-scryfall" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>',
    'ai-inferred': '<svg class="source-icon-ai-inferred" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 16.8l-6.2 4.5 2.4-7.4L2 9.4h7.6z"/></svg>',
    'other': '<svg class="source-icon-other" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
  };
  return icons[type] || icons['other'];
}

function renderTierSources(upgrade) {
  const section = document.getElementById('tier-sources-section');
  const list = document.getElementById('tier-sources-list');
  const label = document.getElementById('tier-sources-label');

  const allSources = [];
  if (upgrade.sources) allSources.push(...upgrade.sources);
  if (upgrade.highlights) upgrade.highlights.forEach(a => { if (a.sources) allSources.push(...a.sources); });
  if (upgrade.synergies) upgrade.synergies.forEach(s => { if (s.sources) allSources.push(...s.sources); });

  const seen = new Set();
  const unique = allSources.filter(s => {
    if (seen.has(s.name)) return false;
    seen.add(s.name);
    return true;
  });

  if (unique.length === 0) {
    section.style.display = 'none';
    return;
  }

  label.textContent = `Sources (${unique.length})`;
  list.innerHTML = unique.map(s => {
    const icon = getSourceTypeIcon(s.type);
    const nameHtml = s.url
      ? `<a href="${sanitizeUrl(s.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(s.name)}</a>`
      : escapeHtml(s.name);
    const detailHtml = s.detail ? ` <span class="tier-source-detail">${escapeHtml(s.detail)}</span>` : '';
    return `<div class="tier-source-item">${icon} ${nameHtml}${detailHtml}</div>`;
  }).join('');

  section.style.display = '';
  section.classList.remove('expanded');
}

// === ACCESSIBILITY: FOCUS TRAP ===
class FocusTrap {
  constructor(containerElement) {
    this.container = containerElement;
    this.previouslyFocused = null;
    this.onKeyDown = this.handleKeyDown.bind(this);
  }

  activate() {
    this.previouslyFocused = document.activeElement;
    this.container.addEventListener('keydown', this.onKeyDown);
    const first = this.getFocusableElements()[0];
    if (first) first.focus();
  }

  deactivate() {
    this.container.removeEventListener('keydown', this.onKeyDown);
    if (this.previouslyFocused && this.previouslyFocused.focus) {
      this.previouslyFocused.focus();
    }
  }

  getFocusableElements() {
    return Array.from(this.container.querySelectorAll(
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    ));
  }

  handleKeyDown(e) {
    if (e.key !== 'Tab') return;
    const focusable = this.getFocusableElements();
    if (focusable.length === 0) {
      e.preventDefault();
      return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (e.shiftKey) {
      if (document.activeElement === first) {
        e.preventDefault();
        last.focus();
      }
    } else {
      if (document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  }
}

// === ACCESSIBILITY: STATUS ANNOUNCEMENTS ===
function announceStatus(message) {
  const el = document.getElementById('status-announcement');
  if (el) {
    el.textContent = '';
    setTimeout(() => { el.textContent = message; }, 200);
  }
}

// === STATE ===
let deckIndex = null;  // Lightweight manifest
let loadedDecks = {};  // Cache of full deck data
let currentDeck = null;
let currentDeckId = null;
let synergyGraph = new Map(); // For interactive synergy explorer
let currentHoveredCard = null;
const selectedCards = new Set();

function toggleCardSelection(cardName) {
  if (selectedCards.has(cardName)) {
    selectedCards.delete(cardName);
  } else {
    selectedCards.add(cardName);
  }
  // Update checkbox and highlight for this card
  document.querySelectorAll(`.decklist-card[data-card-name="${CSS.escape(cardName)}"]`).forEach(el => {
    const cb = el.querySelector('.decklist-checkbox');
    if (cb) cb.checked = selectedCards.has(cardName);
    el.classList.toggle('selected', selectedCards.has(cardName));
  });
  updateCopyButtonState();
}

function clearSelection() {
  selectedCards.clear();
  document.querySelectorAll('.decklist-card.selected').forEach(el => el.classList.remove('selected'));
  document.querySelectorAll('.decklist-checkbox').forEach(cb => cb.checked = false);
  updateCopyButtonState();
}

function selectAllVisible() {
  document.querySelectorAll('#decklist-content .decklist-card').forEach(el => {
    const name = el.dataset.cardName;
    if (name) {
      selectedCards.add(name);
      el.classList.add('selected');
      const cb = el.querySelector('.decklist-checkbox');
      if (cb) cb.checked = true;
    }
  });
  updateCopyButtonState();
}

function updateCopyButtonState() {
  const label = document.getElementById('copy-deck-label');
  if (!label) return;
  label.textContent = selectedCards.size > 0
    ? `Copy Selected (${selectedCards.size})`
    : 'Copy Deck';
}

function restoreCheckboxState() {
  if (selectedCards.size === 0) return;
  document.querySelectorAll('#decklist-content .decklist-card').forEach(el => {
    const name = el.dataset.cardName;
    if (name && selectedCards.has(name)) {
      el.classList.add('selected');
      const cb = el.querySelector('.decklist-checkbox');
      if (cb) cb.checked = true;
    }
  });
}

let currentView = 'guide';

// Analytics state
let simulationCache = {};
let analyticsRenderVersion = 0;

// TiltEffect cleanup tracking
let activeTiltEffects = [];

// Focus traps for modals
const searchFocusTrap = new FocusTrap(document.getElementById('search-modal'));
const mobileFocusTrap = new FocusTrap(document.getElementById('mobile-preview-modal'));
const bracketFocusTrap = new FocusTrap(document.getElementById('bracket-info-modal'));

// === HELPER FUNCTIONS ===
function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

// === BRACKET CONFIGURATION ===
const BRACKET_CONFIG = {
  1: { name: 'Exhibition', class: 'exhibition' },
  2: { name: 'Core', class: 'core' },
  3: { name: 'Upgraded', class: 'upgraded' },
  4: { name: 'Optimized', class: 'optimized' },
  5: { name: 'cEDH', class: 'cedh' }
};

function parseBracket(bracketStr) {
  // Parse "1-2" → {min: 1, max: 2} or "3" → {min: 3, max: 3}
  if (!bracketStr) return { min: 1, max: 1 };
  const str = String(bracketStr);
  if (str.includes('-')) {
    const [min, max] = str.split('-').map(Number);
    return { min, max };
  }
  const val = parseInt(str, 10);
  return { min: val, max: val };
}

function renderBracketVisualization() {
  if (!currentDeck) return;

  const target = parseBracket(currentDeck.bracket || '3');

  // Update label
  const bracketLabel = document.getElementById('bracket-label');
  const targetName = BRACKET_CONFIG[target.max]?.name || 'Unknown';
  bracketLabel.textContent = `Bracket ${target.max}: ${targetName}`;

  // Animate bracket bar fill left-to-right
  const bracketBar = document.querySelector('.bracket-bar');
  bracketBar.classList.add('bracket-animating');
  document.querySelectorAll('.bracket-segment').forEach(segment => {
    segment.classList.remove('animate-fill');
    const bracket = parseInt(segment.dataset.bracket, 10);
    segment.classList.toggle('filled', bracket <= target.max);
  });
  // Trigger reflow, then add animation class
  void bracketBar.offsetWidth;
  document.querySelectorAll('.bracket-segment').forEach(segment => {
    segment.classList.add('animate-fill');
  });
  // Remove animating class after animation completes
  setTimeout(() => bracketBar.classList.remove('bracket-animating'), 600);

  // Update legend active states
  document.querySelectorAll('.bracket-legend span').forEach(span => {
    const bracket = parseInt(span.dataset.bracket, 10);
    const isInTargetRange = bracket >= target.min && bracket <= target.max;
    span.classList.toggle('active', isInTargetRange);
  });

  // Position indicators
  const currentIndicator = document.getElementById('bracket-current-indicator');
  const targetIndicator = document.getElementById('bracket-target-indicator');
  const targetMarker = document.getElementById('bracket-target-marker');

  // Update bracket visualization accessible description
  const bracketViz = document.getElementById('bracket-visualization');
  bracketViz.setAttribute('aria-label', `Bracket: ${target.max} (${targetName})`);
  // No current→target display; hide current indicator
  currentIndicator.style.display = 'none';
  targetIndicator.classList.add('hidden');
  targetMarker.classList.add('hidden');

  // Target indicator and marker: position at the center of the target range
  const targetCenter = ((target.min + target.max) / 2 - 1) * 20 + 10;
  targetIndicator.style.left = `${targetCenter}%`;
  targetMarker.style.left = `${targetCenter}%`;
}

// === 3D CARD TILT EFFECT ===
class TiltEffect {
  constructor(element, options = {}) {
    this.element = element;
    this.options = {
      maxTilt: options.maxTilt || 15,
      scale: options.scale || 1.05,
      perspective: options.perspective || 1000,
      glare: options.glare !== undefined ? options.glare : true,
      ...options
    };

    this.rafId = null;
    this.currentTransform = { rotateX: 0, rotateY: 0, scale: 1 };

    // Check for reduced motion preference
    this.prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (this.prefersReducedMotion) return;

    this.setupGlare();
    this.bindEvents();
  }

  setupGlare() {
    if (!this.options.glare) return;

    // Create glare overlay if it doesn't exist
    if (!this.element.querySelector('.tilt-glare')) {
      const glare = document.createElement('div');
      glare.className = 'tilt-glare';
      glare.innerHTML = '<div class="tilt-glare-inner"></div>';

      // Make parent relative if needed
      const computedStyle = window.getComputedStyle(this.element);
      if (computedStyle.position === 'static') {
        this.element.style.position = 'relative';
      }

      this.element.appendChild(glare);
      this.glareElement = glare;
      this.glareInner = glare.querySelector('.tilt-glare-inner');
    }
  }

  bindEvents() {
    this.onMouseMove = this.handleMouseMove.bind(this);
    this.onMouseLeave = this.handleMouseLeave.bind(this);
    this.onMouseEnter = this.handleMouseEnter.bind(this);

    this.element.addEventListener('mousemove', this.onMouseMove);
    this.element.addEventListener('mouseleave', this.onMouseLeave);
    this.element.addEventListener('mouseenter', this.onMouseEnter);
  }

  handleMouseEnter() {
    this.element.classList.add('tilting');
  }

  handleMouseMove(e) {
    if (this.rafId) return;

    this.rafId = requestAnimationFrame(() => {
      this.updateTransform(e);
      this.rafId = null;
    });
  }

  updateTransform(e) {
    const rect = this.element.getBoundingClientRect();

    // Calculate cursor position relative to card center (-1 to 1 range)
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    const normalizedX = (e.clientX - centerX) / (rect.width / 2);
    const normalizedY = (e.clientY - centerY) / (rect.height / 2);

    // Calculate rotation (invert Y for natural tilt feel)
    const rotateX = -normalizedY * this.options.maxTilt;
    const rotateY = normalizedX * this.options.maxTilt;

    // Apply transform
    this.element.style.transform = `
      perspective(${this.options.perspective}px)
      rotateX(${rotateX}deg)
      rotateY(${rotateY}deg)
      scale(${this.options.scale})
    `;

    // Dynamic shadow (shifts opposite to tilt)
    const shadowX = -normalizedX * 10;
    const shadowY = -normalizedY * 10;
    this.element.style.boxShadow = `
      ${shadowX}px ${shadowY}px 30px rgba(157, 78, 221, 0.4),
      0 4px 15px rgba(0, 0, 0, 0.3)
    `;

    // Update glare position
    if (this.glareElement && this.glareInner) {
      this.glareElement.style.opacity = '1';
      const glareX = 50 + normalizedX * 30;
      const glareY = 50 + normalizedY * 30;
      this.glareInner.style.background = `radial-gradient(
        circle at ${glareX}% ${glareY}%,
        rgba(255, 255, 255, 0.25) 0%,
        rgba(255, 255, 255, 0) 80%
      )`;
    }
  }

  handleMouseLeave() {
    if (this.rafId) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }

    this.element.classList.remove('tilting');

    // Reset transform with smooth transition
    this.element.style.transform = '';
    this.element.style.boxShadow = '';

    // Hide glare
    if (this.glareElement) {
      this.glareElement.style.opacity = '0';
    }
  }

  destroy() {
    if (this.rafId) {
      cancelAnimationFrame(this.rafId);
    }
    this.element.removeEventListener('mousemove', this.onMouseMove);
    this.element.removeEventListener('mouseleave', this.onMouseLeave);
    this.element.removeEventListener('mouseenter', this.onMouseEnter);
    if (this.glareElement) {
      this.glareElement.remove();
    }
  }
}

function initializeTiltEffect(element, options) {
  if (!element || element._tiltEffect) return;
  element._tiltEffect = new TiltEffect(element, options);
  activeTiltEffects.push(element._tiltEffect);
}

function cleanupTiltEffects(selector) {
  if (selector) {
    activeTiltEffects = activeTiltEffects.filter(effect => {
      if (effect.element && effect.element.matches(selector)) {
        effect.destroy();
        return false;
      }
      return true;
    });
  } else {
    activeTiltEffects.forEach(effect => effect.destroy());
    activeTiltEffects = [];
  }
}

function initializeCommanderTilt() {
  document.querySelectorAll('.commander-card-preview').forEach(img => {
    if (!img._tiltInitialized) {
      initializeTiltEffect(img, { maxTilt: 12, scale: 1.03, glare: true });
      img._tiltInitialized = true;
    }
  });
}


// === DECK STATISTICS ===
const CATEGORY_CONFIG = [
  { id: 'lands', name: 'Lands', class: 'lands' },
  { id: 'ramp', name: 'Ramp', class: 'ramp' },
  { id: 'card-draw', name: 'Card Draw', class: 'card-draw' },
  { id: 'removal', name: 'Removal', class: 'removal' },
  { id: 'counter-spells', name: 'Counter Spells', class: 'counter-spells' },
  { id: 'board-wipes', name: 'Board Wipes', class: 'board-wipes' },
  { id: 'graveyard-hate', name: 'Graveyard Hate', class: 'graveyard-hate' },
  { id: 'reanimation', name: 'Reanimation', class: 'reanimation' },
  { id: 'finishers', name: 'Finishers', class: 'finishers' },
  { id: 'protection', name: 'Protection', class: 'protection' },
  { id: 'value', name: 'Value', class: 'value' }
];

// Known ramp cards by name
const KNOWN_RAMP_CARDS = new Set([
  'Sol Ring', 'Mana Vault', 'Mana Crypt', 'Arcane Signet', 'Mind Stone',
  'Thought Vessel', 'Hedron Archive', 'Thran Dynamo', 'Worn Powerstone',
  'Everflowing Chalice', 'Basalt Monolith', 'Grim Monolith', 'Coalition Relic',
  "Commander's Sphere", 'Coldsteel Heart', 'Fellwar Stone', 'Prismatic Lens',
  'Cultivate', 'Kodama\'s Reach', 'Rampant Growth', 'Farseek', 'Nature\'s Lore',
  'Three Visits', 'Sakura-Tribe Elder', 'Wood Elves', 'Farhaven Elf',
  'Birds of Paradise', 'Llanowar Elves', 'Elvish Mystic', 'Elves of Deep Shadow',
  'Urza\'s Incubator', 'Semblance Anvil',
  'Crypt Ghast', 'Nirkana Revenant',
  'Forsaken Monument', 'Ugin, the Ineffable'
]);

function categorizeCard(cardName, metadata) {
  const categories = [];
  const name = cardName.toLowerCase();
  const oracle = (metadata?.oracle_text || '').toLowerCase();
  const typeLine = (metadata?.type_line || '').toLowerCase();
  const cmc = metadata?.cmc ?? 0;

  const isLand = typeLine.includes('land');

  // Lands
  if (isLand) {
    categories.push('lands');
  }

  // Ramp detection (exclude lands — they belong in 'lands' category)
  if (!isLand && (
      KNOWN_RAMP_CARDS.has(cardName) ||
      oracle.includes('add {') ||
      oracle.includes('add one mana') ||
      oracle.includes('search your library for a basic land') ||
      oracle.includes('search your library for a land') ||
      (oracle.includes('mana') && oracle.includes('add')) ||
      (oracle.includes('costs {') && oracle.includes('less to cast') && !oracle.includes('this spell costs')))) {
    categories.push('ramp');
  }

  // Removal detection
  if ((oracle.includes('destroy target') && !oracle.includes('destroy target land')) ||
      oracle.includes('exile target') ||
      oracle.includes('deals damage to any target') ||
      oracle.includes('deals damage to target creature') ||
      (oracle.includes('destroy') && oracle.includes('creature')) ||
      oracle.includes('shuffles it into') ||
      (oracle.includes('opponent') && oracle.includes('sacrifices a')) ||
      (oracle.includes('gets -') && oracle.includes('target')) ||
      name.includes('path to exile') ||
      name.includes('swords to plowshares')) {
    categories.push('removal');
  }

  // Card draw detection
  if (oracle.includes('draw a card') ||
      oracle.includes('draw cards') ||
      oracle.includes('draw two cards') ||
      oracle.includes('draw three cards') ||
      oracle.includes('draws a card') ||
      oracle.includes('draw x cards') ||
      name.includes('rhystic study') ||
      name.includes('mystic remora')) {
    categories.push('card-draw');
  }

  // Counter spells detection
  if (oracle.includes('counter target') ||
      oracle.includes('counter that spell') ||
      oracle.includes('counter all spells') ||
      name.includes('counterspell') ||
      name.includes('swan song') ||
      name.includes('negate') ||
      name.includes('mana drain') ||
      name.includes('force of will') ||
      name.includes('force of negation') ||
      name.includes('fierce guardianship') ||
      name.includes('pact of negation') ||
      name.includes('flusterstorm') ||
      name.includes('dispel') ||
      name.includes('spell pierce') ||
      name.includes('dovin\'s veto') ||
      name.includes('arcane denial') ||
      name.includes('delay') ||
      name.includes('tale\'s end') ||
      name.includes('an offer you can\'t refuse') ||
      name.includes('wash away')) {
    categories.push('counter-spells');
  }

  // Board wipes detection
  if (oracle.includes('destroy all creatures') ||
      oracle.includes('destroy all nonland') ||
      oracle.includes('exile all') ||
      oracle.includes('deals damage to each creature') ||
      oracle.includes('all creatures get -') ||
      name.includes('wrath') ||
      name.includes('damnation') ||
      name.includes('blasphemous act')) {
    categories.push('board-wipes');
  }

  // Graveyard hate detection
  if ((oracle.includes('exile') && oracle.includes('graveyard')) ||
      oracle.includes('exile all cards from') ||
      oracle.includes('exile target card from a graveyard') ||
      name.includes('bojuka bog') ||
      name.includes('rest in peace') ||
      name.includes('leyline of the void') ||
      name.includes('scavenger grounds')) {
    categories.push('graveyard-hate');
  }

  // Reanimation detection
  if (oracle.includes('return target creature card from') ||
      oracle.includes('put target creature card from a graveyard') ||
      oracle.includes('from your graveyard to the battlefield') ||
      name.includes('reanimate') ||
      name.includes('animate dead') ||
      name.includes('stitch together')) {
    categories.push('reanimation');
  }

  // Finishers detection
  if ((cmc >= 6 && typeLine.includes('eldrazi')) ||
      oracle.includes('annihilator') ||
      (cmc >= 7 && typeLine.includes('creature') && oracle.includes('when')) ||
      oracle.includes('each opponent loses') ||
      (oracle.includes('opponent lose') && !oracle.includes('you lose')) ||
      (oracle.includes('opponent loses life') && oracle.includes('equal to')) ||
      (oracle.includes('damage to') && oracle.includes('target opponent')) ||
      oracle.includes('you win the game') ||
      name.includes('kozilek') ||
      name.includes('ulamog') ||
      name.includes('emrakul') ||
      name.includes('it that betrays') ||
      name.includes('void winnower') ||
      name.includes('blightsteel colossus')) {
    categories.push('finishers');
  }

  // Value engines — token generators and sacrifice/death payoffs
  if (!isLand && (
      (oracle.includes('create') && oracle.includes('token')) ||
      (oracle.includes('whenever') && (oracle.includes('sacrifice') || oracle.includes('dies'))))) {
    categories.push('value');
  }

  // Protection detection
  if (oracle.includes('hexproof') ||
      oracle.includes('shroud') ||
      oracle.includes('indestructible') ||
      oracle.includes('can\'t be countered') ||
      oracle.includes('protection from') ||
      oracle.includes('can\'t be the target') ||
      name.includes('lightning greaves') ||
      name.includes('swiftfoot boots') ||
      name.includes('heroic intervention')) {
    categories.push('protection');
  }

  return categories;
}

function compareByCmc(a, b) {
  const cmcA = cardMetadataCache.get(a.name)?.cmc ?? 0;
  const cmcB = cardMetadataCache.get(b.name)?.cmc ?? 0;
  return cmcA - cmcB || a.name.localeCompare(b.name);
}

function getPrimaryRole(card) {
  if (card.role) return card.role;
  const metadata = cardMetadataCache.get(card.name);
  const roles = categorizeCard(card.name, metadata);
  const priority = CATEGORY_CONFIG.map(c => c.id);
  for (const p of priority) {
    if (roles.includes(p)) return p;
  }
  return 'other';
}

function calculateDeckStats(deckCards) {
  // Initialize mana curve (0-10+)
  const manaCurve = {};
  for (let i = 0; i <= 10; i++) {
    manaCurve[i] = { count: 0, cards: [] };
  }

  // Initialize categories
  const categories = {};
  CATEGORY_CONFIG.forEach(cat => {
    categories[cat.id] = { count: 0, cards: [] };
  });

  let totalCmc = 0;
  let nonLandCount = 0;
  let totalCards = 0;

  deckCards.forEach(card => {
    const metadata = cardMetadataCache.get(card.name);
    if (!metadata) return;

    const qty = card.quantity || 1;
    totalCards += qty;

    const typeLine = (metadata.type_line || '').toLowerCase();
    const isLand = typeLine.includes('land');

    // Skip lands for mana curve and average
    if (!isLand) {
      const cmc = Math.floor(metadata.cmc || 0);
      const bucket = Math.min(cmc, 10);
      manaCurve[bucket].count += qty;
      manaCurve[bucket].cards.push(card.name);
      totalCmc += cmc * qty;
      nonLandCount += qty;
    }

    // Use stored role (single-count) or fall back to heuristic detection (multi-category)
    const cardCategories = card.role ? [card.role] : categorizeCard(card.name, metadata);
    cardCategories.forEach(catId => {
      if (categories[catId]) {
        categories[catId].count += qty;
        categories[catId].cards.push(card.name);
      }
    });
  });

  const avgCmc = nonLandCount > 0 ? (totalCmc / nonLandCount).toFixed(2) : '0.00';

  return { manaCurve, categories, avgCmc, nonLandCount, totalCards };
}

function renderDeckStats() {
  if (!currentDeck) return;

  const statsSection = document.getElementById('deck-stats-section');
  if (!statsSection) return;

  const deckCards = (currentDeck.decklist || []).map(card => ({ name: card.name, quantity: card.quantity || 1, role: card.role }));

  // Calculate stats
  const stats = calculateDeckStats(deckCards);

  // Render mana curve
  renderManaCurve(stats.manaCurve, stats.nonLandCount);

  // Update summary stats
  document.getElementById('avg-cmc').textContent = stats.avgCmc;
  document.getElementById('nonland-count').textContent = stats.nonLandCount;

  // Render category bars — use totalCards from stats (quantity-aware)
  renderCategoryBars(stats.categories, stats.totalCards);
}

function renderManaCurve(manaCurve, nonLandCount) {
  const chart = document.getElementById('mana-curve-chart');
  if (!chart) return;

  // Find highest occupied bucket, show at least 7 bars (0–6)
  let maxBucket = 0;
  for (let i = 10; i >= 0; i--) {
    if (manaCurve[i] && manaCurve[i].count > 0) { maxBucket = i; break; }
  }
  const renderMax = Math.max(maxBucket, 6);

  // Find max count for scaling
  const maxCount = Math.max(...Object.values(manaCurve).map(m => m.count), 1);

  let html = '';
  for (let i = 0; i <= renderMax; i++) {
    const data = manaCurve[i];
    const widthPercent = (data.count / maxCount) * 100;
    const label = i === 10 ? '10+' : String(i);
    const pct = nonLandCount > 0 ? Math.round((data.count / nonLandCount) * 100) : 0;

    html += `
      <div class="mana-bar-container">
        <div class="mana-bar-label">${escapeHtml(label)}</div>
        <div class="mana-bar-wrapper">
          <div class="mana-bar" style="width: ${Math.max(widthPercent, 2)}%"
               data-cmc="${i}" data-cards="${escapeHtml(data.cards.join(', '))}"
               title="${escapeHtml(String(data.count))} card${data.count !== 1 ? 's' : ''} (${pct}%) at ${escapeHtml(label)} mana">
            <span class="mana-bar-count">${escapeHtml(String(data.count))}</span>
          </div>
        </div>
        <div class="mana-bar-pct">${pct}%</div>
      </div>
    `;
  }

  chart.innerHTML = html;

  // Add click handlers to show cards in preview
  chart.querySelectorAll('.mana-bar').forEach(bar => {
    bar.addEventListener('click', () => {
      const cards = bar.dataset.cards.split(', ').filter(c => c);
      if (cards.length > 0) {
        showCardPreview(cards[0]);
      }
    });
  });
}

function renderCategoryBars(categories, totalCards) {
  const container = document.getElementById('category-bars');
  if (!container) return;

  // Find max count for scaling
  const maxCount = Math.max(...Object.values(categories).map(c => c.count), 1);

  let html = '';
  CATEGORY_CONFIG.forEach(config => {
    const data = categories[config.id];
    const widthPercent = (data.count / maxCount) * 100;
    const pct = totalCards > 0 ? Math.round((data.count / totalCards) * 100) : 0;

    html += `
      <div class="category-bar-item" data-category="${escapeHtml(config.id)}"
           data-cards="${escapeHtml(data.cards.join('|'))}">
        <span class="category-bar-label">${escapeHtml(config.name)}</span>
        <div class="category-bar-track">
          <div class="category-bar-fill ${config.class}" style="width: ${widthPercent}%"></div>
        </div>
        <span class="category-bar-count">${escapeHtml(String(data.count))} <span class="category-bar-pct">(${pct}%)</span></span>
      </div>
    `;
  });

  container.innerHTML = html;

  // Add hover/click handlers
  const tooltip = document.getElementById('category-tooltip');
  container.querySelectorAll('.category-bar-item').forEach(item => {
    item.addEventListener('mouseenter', (e) => {
      const category = item.dataset.category;
      const cards = item.dataset.cards.split('|').filter(c => c);
      const config = CATEGORY_CONFIG.find(c => c.id === category);

      if (cards.length > 0 && tooltip) {
        tooltip.querySelector('.category-tooltip-title').textContent = `${config.name} (${cards.length})`;
        tooltip.querySelector('.category-tooltip-cards').textContent = cards.slice(0, 10).join(', ') +
          (cards.length > 10 ? `, +${cards.length - 10} more` : '');

        // Position tooltip
        const rect = item.getBoundingClientRect();
        tooltip.style.left = `${rect.right + 10}px`;
        tooltip.style.top = `${rect.top}px`;
        tooltip.classList.add('visible');
      }
    });

    item.addEventListener('mouseleave', () => {
      if (tooltip) {
        tooltip.classList.remove('visible');
      }
    });

    item.addEventListener('click', () => {
      const categoryId = item.dataset.category;
      filterState.category = categoryId;
      document.querySelectorAll('#filter-category-chips .filter-chip').forEach(c => {
        const isMatch = c.dataset.category === categoryId;
        c.classList.toggle('active', isMatch);
        c.setAttribute('aria-pressed', isMatch);
      });
      applyFilters();
      document.getElementById('decklist-content')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
}

// === CACHES ===
const imageCache = new Map();
const cardMetadataCache = new Map();

// === SCRYFALL IMAGE THROTTLE ===
// Prevents 429 rate limits by throttling <img> src assignments to max 10/s.
// Images use data-scryfall-src instead of src; an IntersectionObserver + queue
// progressively loads them as they enter the viewport.
const IMAGE_LOAD_INTERVAL = 100; // 100ms = 10 req/s max
const IMAGE_URL_CACHE_KEY = 'grimoire-image-urls';
const IMAGE_CACHE_MAX = 2000;
const scryfallImageQueue = [];
let isProcessingImageQueue = false;

// Persist imageCache to localStorage for cross-session caching
function loadImageCacheFromStorage() {
  try {
    const stored = JSON.parse(localStorage.getItem(IMAGE_URL_CACHE_KEY) || '{}');
    for (const [k, v] of Object.entries(stored)) imageCache.set(k, v);
  } catch { /* ignore corrupt data */ }
}

function saveImageCacheToStorage() {
  try {
    // Trim to max size (keep most recent entries)
    const entries = [...imageCache.entries()];
    const trimmed = entries.slice(-IMAGE_CACHE_MAX);
    localStorage.setItem(IMAGE_URL_CACHE_KEY, JSON.stringify(Object.fromEntries(trimmed)));
  } catch { /* storage full — ignore */ }
}

// Debounced save
let imageCacheSaveTimer = null;
function scheduleImageCacheSave() {
  clearTimeout(imageCacheSaveTimer);
  imageCacheSaveTimer = setTimeout(saveImageCacheToStorage, 2000);
}

function scryfallImageUrl(cardName, version) {
  const encoded = encodeURIComponent(cardName);
  const versionParam = version && version !== 'normal' ? `&version=${version}` : '';
  return `https://api.scryfall.com/cards/named?format=image&exact=${encoded}${versionParam}`;
}

function getCachedImageUrl(cardName, version) {
  const key = version ? `${cardName}|${version}` : cardName;
  return imageCache.get(key);
}

function setCachedImageUrl(cardName, version, url) {
  const key = version ? `${cardName}|${version}` : cardName;
  imageCache.set(key, url);
  scheduleImageCacheSave();
}

function queueImageLoad(imgEl) {
  scryfallImageQueue.push(imgEl);
  processImageLoadQueue();
}

async function processImageLoadQueue() {
  if (isProcessingImageQueue) return;
  isProcessingImageQueue = true;
  while (scryfallImageQueue.length > 0) {
    const img = scryfallImageQueue.shift();
    const src = img.dataset.scryfallSrc;
    if (!src || img.src === src) continue;
    img.src = src;
    img.removeAttribute('data-scryfall-src');
    if (scryfallImageQueue.length > 0) {
      await new Promise(r => setTimeout(r, IMAGE_LOAD_INTERVAL));
    }
  }
  isProcessingImageQueue = false;
}

// IntersectionObserver: when a data-scryfall-src image enters viewport, queue it
let scryfallObserver = null;
function initScryfallObserver() {
  if (scryfallObserver) return;
  scryfallObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        scryfallObserver.unobserve(entry.target);
        queueImageLoad(entry.target);
      }
    });
  }, { rootMargin: '200px' });
}

function observeScryfallImages(container) {
  if (!scryfallObserver) initScryfallObserver();
  container.querySelectorAll('img[data-scryfall-src]').forEach(img => {
    scryfallObserver.observe(img);
  });
}

// Pre-load local metadata cache (eliminates Scryfall API calls for known cards)
async function loadLocalMetadata() {
  loadImageCacheFromStorage();
  try {
    const resp = await fetch('data/card-metadata.json');
    if (resp.ok) {
      const data = await resp.json();
      for (const [name, meta] of Object.entries(data)) {
        cardMetadataCache.set(name, meta);
      }
      console.log(`Pre-loaded ${cardMetadataCache.size} cards from local metadata cache`);
    }
  } catch (e) {
    console.warn('Local metadata cache not available, falling back to Scryfall API');
  }
}

// === RATE LIMITING ===
const requestQueue = [];
const inFlightRequests = new Map();
let isProcessingQueue = false;
const RATE_LIMIT_DELAY = 100; // 100ms between requests (10 per second)

// === DOM ELEMENTS ===
const deckSelect = document.getElementById('deck-select');
const commanderInfo = document.getElementById('commander-info');
const commanderName = document.getElementById('commander-name');
const altCommander = document.getElementById('alt-commander');
const commanderCards = document.getElementById('commander-cards');
const upgradeOverview = document.getElementById('deck-overview');
const mainContent = document.getElementById('main-content');
const summaryCost = document.getElementById('summary-cost');
const summaryChangers = document.getElementById('summary-changers');
const previewContainer = document.getElementById('preview-container');
const previewName = document.getElementById('preview-name');
const loading = document.getElementById('loading');
const error = document.getElementById('error');
const guideView = document.getElementById('guide-view');
const guideStrategy = document.getElementById('guide-strategy');
const addGroups = document.getElementById('add-groups');
const winconsList = document.getElementById('wincons-list');
const synergiesList = document.getElementById('synergies-list');
const combosList = document.getElementById('combos-list');
const tokensList = document.getElementById('tokens-list');
const decklistContent = document.getElementById('decklist-content');
const decklistCount = document.getElementById('decklist-count');

// === EVENT DELEGATION ===
let lastHoveredGuideCard = null;
let lastHoveredDeckCard = null;

function setupDelegatedListeners() {
  const mainContent = document.getElementById('main-content');

  // --- Guide cards ---
  addGroups.addEventListener('mouseover', (e) => {
    const card = e.target.closest('.guide-card');
    if (card && card !== lastHoveredGuideCard) {
      lastHoveredGuideCard = card;
      showCardPreview(card.dataset.cardName);
    }
  });
  addGroups.addEventListener('mouseout', (e) => {
    const card = e.target.closest('.guide-card');
    if (card && card === lastHoveredGuideCard && (!e.relatedTarget || !card.contains(e.relatedTarget))) {
      lastHoveredGuideCard = null;
    }
  });
  addGroups.addEventListener('click', (e) => {
    const card = e.target.closest('.guide-card');
    if (card && !e.target.closest('a')) {
      showCardPreview(card.dataset.cardName);
      if (exploreModeActive && synergyGraph.has(card.dataset.cardName)) {
        highlightSynergyCards(card.dataset.cardName);
      }
    }
  });
  addGroups.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      const card = e.target.closest('.guide-card');
      if (card) {
        e.preventDefault();
        showCardPreview(card.dataset.cardName);
        if (exploreModeActive && synergyGraph.has(card.dataset.cardName)) {
          highlightSynergyCards(card.dataset.cardName);
        }
      }
    }
  });

  // --- Decklist cards ---
  decklistContent.addEventListener('mouseover', (e) => {
    const card = e.target.closest('.decklist-card');
    if (card && card !== lastHoveredDeckCard) {
      lastHoveredDeckCard = card;
      showCardPreview(card.dataset.cardName);
    }
  });
  decklistContent.addEventListener('mouseout', (e) => {
    const card = e.target.closest('.decklist-card');
    if (card && card === lastHoveredDeckCard && (!e.relatedTarget || !card.contains(e.relatedTarget))) {
      lastHoveredDeckCard = null;
    }
  });
  decklistContent.addEventListener('click', (e) => {
    if (e.target.closest('.decklist-checkbox')) {
      const cb = e.target.closest('.decklist-checkbox');
      toggleCardSelection(cb.dataset.cardName);
      return;
    }
    const card = e.target.closest('.decklist-card');
    if (card && !e.target.closest('a')) {
      showCardPreview(card.dataset.cardName);
    }
  });
  decklistContent.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      const card = e.target.closest('.decklist-card');
      if (card) {
        e.preventDefault();
        showCardPreview(card.dataset.cardName);
      }
    }
  });

  // --- Decklist gallery cards ---
  const galleryEl = document.getElementById('decklist-gallery');
  galleryEl.addEventListener('mouseover', (e) => {
    const card = e.target.closest('.decklist-gallery-card');
    if (card && card !== lastHoveredDeckCard) {
      lastHoveredDeckCard = card;
      showCardPreview(card.dataset.cardName);
    }
  });
  galleryEl.addEventListener('mouseout', (e) => {
    const card = e.target.closest('.decklist-gallery-card');
    if (card && card === lastHoveredDeckCard && (!e.relatedTarget || !card.contains(e.relatedTarget))) {
      lastHoveredDeckCard = null;
    }
  });
  galleryEl.addEventListener('click', (e) => {
    const card = e.target.closest('.decklist-gallery-card');
    if (card) showCardPreview(card.dataset.cardName);
  });
  galleryEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      const card = e.target.closest('.decklist-gallery-card');
      if (card) {
        e.preventDefault();
        showCardPreview(card.dataset.cardName);
      }
    }
  });

  // --- Win condition card tags ---
  winconsList.addEventListener('mouseover', (e) => {
    const tag = e.target.closest('.synergy-card-tag');
    if (tag) showCardPreview(tag.dataset.cardName);
  });
  winconsList.addEventListener('click', (e) => {
    const tag = e.target.closest('.synergy-card-tag');
    if (tag) showCardPreview(tag.dataset.cardName);
  });
  winconsList.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      const tag = e.target.closest('.synergy-card-tag');
      if (tag) {
        e.preventDefault();
        showCardPreview(tag.dataset.cardName);
      }
    }
  });

  // --- Synergy card tags ---
  synergiesList.addEventListener('mouseover', (e) => {
    const tag = e.target.closest('.synergy-card-tag');
    if (tag) showCardPreview(tag.dataset.cardName);
  });
  synergiesList.addEventListener('click', (e) => {
    const tag = e.target.closest('.synergy-card-tag');
    if (tag) {
      showCardPreview(tag.dataset.cardName);
      if (exploreModeActive) {
        e.stopPropagation();
        highlightSynergyCards(tag.dataset.cardName);
      }
    }
  });
  synergiesList.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      const tag = e.target.closest('.synergy-card-tag');
      if (tag) {
        e.preventDefault();
        showCardPreview(tag.dataset.cardName);
        if (exploreModeActive) {
          highlightSynergyCards(tag.dataset.cardName);
        }
      }
    }
  });

  // --- Combo card tags ---
  combosList.addEventListener('mouseover', (e) => {
    const tag = e.target.closest('.synergy-card-tag');
    if (tag) showCardPreview(tag.dataset.cardName);
  });
  combosList.addEventListener('click', (e) => {
    const tag = e.target.closest('.synergy-card-tag');
    if (tag) {
      showCardPreview(tag.dataset.cardName);
      if (exploreModeActive) {
        e.stopPropagation();
        highlightSynergyCards(tag.dataset.cardName);
      }
    }
  });
  combosList.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      const tag = e.target.closest('.synergy-card-tag');
      if (tag) {
        e.preventDefault();
        showCardPreview(tag.dataset.cardName);
        if (exploreModeActive) {
          highlightSynergyCards(tag.dataset.cardName);
        }
      }
    }
  });

  // --- Token producer names ---
  tokensList.addEventListener('mouseover', (e) => {
    const tag = e.target.closest('.producer-name');
    if (tag) showCardPreview(tag.dataset.cardName);
  });
  tokensList.addEventListener('click', (e) => {
    const tag = e.target.closest('.producer-name');
    if (tag) showCardPreview(tag.dataset.cardName);
  });
  tokensList.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      const tag = e.target.closest('.producer-name');
      if (tag) {
        e.preventDefault();
        showCardPreview(tag.dataset.cardName);
      }
    }
  });

  // --- Shopping list card rows ---
  const shoppingView = document.getElementById('shopping-view');
  let lastHoveredShoppingCard = null;
  const shoppingTooltip = document.getElementById('shopping-card-tooltip');
  const shoppingTooltipImg = document.getElementById('shopping-tooltip-img');
  const shoppingTooltipName = document.getElementById('shopping-tooltip-name');
  let shoppingTooltipCard = null;

  function positionShoppingTooltip(e) {
    const pad = 16;
    const tooltipW = shoppingTooltip.offsetWidth || 390;
    const tooltipH = shoppingTooltip.offsetHeight || 578;
    let x = e.clientX + pad;
    let y = e.clientY - tooltipH / 2;
    if (x + tooltipW > window.innerWidth - pad) x = e.clientX - tooltipW - pad;
    if (y < pad) y = pad;
    if (y + tooltipH > window.innerHeight - pad) y = window.innerHeight - tooltipH - pad;
    shoppingTooltip.style.left = x + 'px';
    shoppingTooltip.style.top = y + 'px';
  }

  function showShoppingTooltip(cardName, e) {
    if (window.innerWidth <= 768) return;
    shoppingTooltipCard = cardName;
    shoppingTooltipName.textContent = cardName;
    const cached = getCachedImageUrl(cardName, null);
    const imageUrl = cached || scryfallImageUrl(cardName);
    shoppingTooltipImg.src = imageUrl;
    if (!cached) {
      const preload = new Image();
      preload.onload = () => setCachedImageUrl(cardName, null, imageUrl);
      preload.src = imageUrl;
    }
    positionShoppingTooltip(e);
    shoppingTooltip.classList.add('visible');
  }

  function hideShoppingTooltip() {
    shoppingTooltip.classList.remove('visible');
    shoppingTooltipCard = null;
    lastHoveredShoppingCard = null;
  }

  shoppingView.addEventListener('mouseover', (e) => {
    const row = e.target.closest('.shopping-card-row');
    if (row && row !== lastHoveredShoppingCard) {
      lastHoveredShoppingCard = row;
      showShoppingTooltip(row.dataset.cardName, e);
    }
  });
  shoppingView.addEventListener('mousemove', (e) => {
    if (shoppingTooltipCard) positionShoppingTooltip(e);
  });
  shoppingView.addEventListener('mouseout', (e) => {
    const row = e.target.closest('.shopping-card-row');
    if (row && row === lastHoveredShoppingCard && (!e.relatedTarget || !row.contains(e.relatedTarget))) {
      hideShoppingTooltip();
    }
  });
  shoppingView.addEventListener('click', (e) => {
    const row = e.target.closest('.shopping-card-row');
    if (row) {
      if (window.innerWidth <= 768) {
        showMobilePreview(row.dataset.cardName);
      }
    }
  });

  // --- Opening hand cards ---
  const handSimulator = document.getElementById('hand-simulator');
  let lastHoveredHandSimCard = null;
  const handSimTooltip = document.getElementById('hand-sim-card-tooltip');
  const handSimTooltipImg = document.getElementById('hand-sim-tooltip-img');
  const handSimTooltipName = document.getElementById('hand-sim-tooltip-name');
  let handSimTooltipCard = null;

  function positionHandSimTooltip(e) {
    const pad = 16;
    const tooltipW = handSimTooltip.offsetWidth || 390;
    const tooltipH = handSimTooltip.offsetHeight || 578;
    let x = e.clientX + pad;
    let y = e.clientY - tooltipH / 2;
    if (x + tooltipW > window.innerWidth - pad) x = e.clientX - tooltipW - pad;
    if (y < pad) y = pad;
    if (y + tooltipH > window.innerHeight - pad) y = window.innerHeight - tooltipH - pad;
    handSimTooltip.style.left = x + 'px';
    handSimTooltip.style.top = y + 'px';
  }

  function showHandSimTooltip(cardName, e) {
    if (window.innerWidth <= 768) return;
    handSimTooltipCard = cardName;
    handSimTooltipName.textContent = cardName;
    const cached = getCachedImageUrl(cardName, null);
    const imageUrl = cached || scryfallImageUrl(cardName);
    handSimTooltipImg.src = imageUrl;
    if (!cached) {
      const preload = new Image();
      preload.onload = () => setCachedImageUrl(cardName, null, imageUrl);
      preload.src = imageUrl;
    }
    positionHandSimTooltip(e);
    handSimTooltip.classList.add('visible');
  }

  function hideHandSimTooltip() {
    handSimTooltip.classList.remove('visible');
    handSimTooltipCard = null;
    lastHoveredHandSimCard = null;
  }

  handSimulator.addEventListener('mouseover', (e) => {
    const card = e.target.closest('.hand-sim-card');
    if (card && card !== lastHoveredHandSimCard) {
      lastHoveredHandSimCard = card;
      showHandSimTooltip(card.dataset.cardName, e);
    }
  });
  handSimulator.addEventListener('mousemove', (e) => {
    if (handSimTooltipCard) positionHandSimTooltip(e);
  });
  handSimulator.addEventListener('mouseout', (e) => {
    const card = e.target.closest('.hand-sim-card');
    if (card && card === lastHoveredHandSimCard && (!e.relatedTarget || !card.contains(e.relatedTarget))) {
      hideHandSimTooltip();
    }
  });
  handSimulator.addEventListener('click', (e) => {
    const card = e.target.closest('.hand-sim-card');
    if (card && window.innerWidth <= 768 && handSimState.phase !== 'bottoming') {
      showMobilePreview(card.dataset.cardName);
    }
  });

}

// === SCRYFALL API ===
async function fetchCardMetadata(cardName) {
  // Check cache first
  if (cardMetadataCache.has(cardName)) {
    return cardMetadataCache.get(cardName);
  }

  // Prevent redundant queue entries for the same card
  if (inFlightRequests.has(cardName)) {
    return inFlightRequests.get(cardName);
  }

  // Return a promise that will be resolved when the request is processed
  const promise = new Promise((resolve) => {
    requestQueue.push({ cardName, resolve });
    processQueue();
  });
  inFlightRequests.set(cardName, promise);
  promise.then(() => inFlightRequests.delete(cardName));
  return promise;
}

async function processQueue() {
  if (isProcessingQueue || requestQueue.length === 0) return;

  isProcessingQueue = true;

  while (requestQueue.length > 0) {
    const { cardName, resolve } = requestQueue.shift();

    // Check cache again (might have been fetched while waiting)
    if (cardMetadataCache.has(cardName)) {
      resolve(cardMetadataCache.get(cardName));
      continue;
    }

    try {
      const response = await fetch(
        `https://api.scryfall.com/cards/named?exact=${encodeURIComponent(cardName)}`
      );

      if (!response.ok) {
        const fallback = { type_line: 'Unknown', cmc: '?', colors: [], mana_cost: '', oracle_text: '' };
        cardMetadataCache.set(cardName, fallback);
        resolve(fallback);
      } else {
        const data = await response.json();
        const metadata = {
          type_line: data.type_line || 'Unknown',
          cmc: data.cmc ?? '?',
          colors: data.colors || [],
          mana_cost: data.mana_cost || '',
          oracle_text: data.oracle_text || ''
        };
        cardMetadataCache.set(cardName, metadata);
        resolve(metadata);
      }
    } catch (err) {
      const fallback = { type_line: 'Unknown', cmc: '?', colors: [], mana_cost: '', oracle_text: '' };
      cardMetadataCache.set(cardName, fallback);
      resolve(fallback);
    }

    // Rate limit delay
    if (requestQueue.length > 0) {
      await new Promise(r => setTimeout(r, RATE_LIMIT_DELAY));
    }
  }

  isProcessingQueue = false;
}

// Batch fetch using Scryfall's Collection API (up to 75 cards per request)
async function fetchCardMetadataBatch(cardNames) {
  // Filter out already cached cards
  const uncachedNames = cardNames.filter(name => !cardMetadataCache.has(name));

  if (uncachedNames.length === 0) return;

  // Scryfall collection API accepts up to 75 cards per request
  const BATCH_SIZE = 75;
  const batches = [];

  for (let i = 0; i < uncachedNames.length; i += BATCH_SIZE) {
    batches.push(uncachedNames.slice(i, i + BATCH_SIZE));
  }

  // Process batches with rate limiting (100ms between batches)
  for (const batch of batches) {
    try {
      const response = await fetch('https://api.scryfall.com/cards/collection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          identifiers: batch.map(name => ({ name }))
        })
      });

      if (response.ok) {
        const data = await response.json();
        data.data.forEach(card => {
          const metadata = {
            type_line: card.type_line || 'Unknown',
            cmc: card.cmc ?? '?',
            colors: card.colors || [],
            mana_cost: card.mana_cost || '',
            oracle_text: card.oracle_text || ''
          };
          cardMetadataCache.set(card.name, metadata);
        });
      }
    } catch (err) {
      console.error('Batch fetch failed:', err);
    }

    // Rate limit between batches
    if (batches.indexOf(batch) < batches.length - 1) {
      await new Promise(r => setTimeout(r, RATE_LIMIT_DELAY));
    }
  }
}

// === HELPER FUNCTIONS ===
function getCardmarketUrl(cardName) {
  const formattedName = cardName
    .replace(/,/g, '')      // Remove commas
    .replace(/'/g, '')      // Remove apostrophes
    .replace(/\s+/g, '-');  // Replace spaces with hyphens
  return `https://www.cardmarket.com/en/Magic/Cards/${formattedName}?sellerType=1,2&sellerReputation=2&language=1&minCondition=2`;
}

function renderManaCost(manaCost) {
  if (!manaCost) return '';
  // Parse {2}{G}{G} into Scryfall SVG images
  return manaCost.replace(/\{([^}]+)\}/g, (match, symbol) => {
    const svgUrl = `https://svgs.scryfall.io/card-symbols/${symbol.replace(/\//g, '')}.svg`;
    return `<img class="mana-symbol-img" src="${svgUrl}" alt="${symbol}" title="${symbol}">`;
  });
}

// === DECK LOADING ===
async function loadDeckIndex() {
  try {
    const response = await fetch('data/index.json');
    if (!response.ok) throw new Error('Failed to load deck index');
    deckIndex = await response.json();

    loading.style.display = 'none';
    populateDeckSelector();
  } catch (err) {
    loading.style.display = 'none';
    error.style.display = 'block';
    error.textContent = `Error loading deck index: ${err.message}. Make sure you're running a local server (e.g., python -m http.server 8000)`;
  }
}

async function loadDeckData(deckId) {
  if (loadedDecks[deckId]) {
    return loadedDecks[deckId];  // Return cached
  }

  const response = await fetch(`data/commanders/${deckId}/deck.json`);
  if (!response.ok) throw new Error(`Failed to load ${deckId}`);
  const data = await response.json();
  loadedDecks[deckId] = data;  // Cache it
  return data;
}

function populateDeckSelector() {
  deckSelect.innerHTML = '<option value="">-- Select a Deck --</option>';

  const allDecks = deckIndex.commanders || [];
  allDecks.forEach(cmd => {
    const option = document.createElement('option');
    option.value = cmd.id;
    option.textContent = cmd.name;
    deckSelect.appendChild(option);
  });

  // Render visual deck gallery
  const gallery = document.getElementById('deck-gallery');
  gallery.innerHTML = allDecks.map(cmd => {
    const cachedArt = getCachedImageUrl(cmd.commander, 'art_crop');
    const artUrl = cachedArt || scryfallImageUrl(cmd.commander, 'art_crop');
    const colorPips = (cmd.colors || []).map(c =>
      `<div class="deck-gallery-pip pip-${escapeHtml(c)}"></div>`
    ).join('');
    const bracketPill = cmd.bracket
      ? `<span class="deck-gallery-bracket" data-bracket="${escapeHtml(cmd.bracket)}">B${escapeHtml(cmd.bracket)}</span>`
      : '';
    const setPill = cmd.lastUpdatedSet
      ? `<div class="deck-gallery-set">Updated for ${escapeHtml(cmd.lastUpdatedSet)}</div>`
      : '';
    const imgAttr = cachedArt ? `src="${artUrl}"` : `data-scryfall-src="${artUrl}"`;
    return `
      <div class="deck-gallery-card" data-deck-id="${escapeHtml(cmd.id)}" tabindex="0" role="button" aria-label="Select ${escapeHtml(cmd.name)}">
        <img class="deck-gallery-art" ${imgAttr} alt="${escapeHtml(cmd.commander)}" loading="lazy" />
        <div class="deck-gallery-info">
          <div class="deck-gallery-name">${escapeHtml(cmd.name)}</div>
          <div class="deck-gallery-subtitle">${escapeHtml(cmd.theme || '')}</div>
          <div class="deck-gallery-meta">
            <div class="deck-gallery-colors">${colorPips}</div>
            ${bracketPill}
          </div>
          ${setPill}
        </div>
      </div>
    `;
  }).join('');

  // Throttled image loading for gallery
  observeScryfallImages(gallery);

  // Gallery click handlers
  gallery.querySelectorAll('.deck-gallery-card').forEach(card => {
    card.addEventListener('click', () => {
      const id = card.dataset.deckId;
      deckSelect.value = id;
      selectDeck(id);
    });
    card.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        card.click();
      }
    });
  });

  // Auto-select if only one deck exists
  if (allDecks.length === 1) {
    deckSelect.value = allDecks[0].id;
    selectDeck(allDecks[0].id);
  }
}

async function selectDeck(deckId) {
  if (!deckId) {
    // Handle empty selection
    commanderInfo.style.display = 'none';
    upgradeOverview.style.display = 'none';
    mainContent.style.display = 'none';
    updateTabStates();
    return;
  }

  try {
    // Show loading state while fetching
    loading.style.display = 'block';
    loading.textContent = 'Consulting the Grimoire...';

    currentDeckId = deckId;
    clearSelection();
    currentDeck = await loadDeckData(deckId);

    document.body.classList.add('commander-deck');

    // Apply per-deck color identity theming
    document.body.className = document.body.className.replace(/\bcolors-\S+/g, '');
    const deckMeta = (deckIndex.commanders || []).find(d => d.id === deckId);
    if (deckMeta?.colors) {
      document.body.classList.add('colors-' + deckMeta.colors.sort().join(''));
    }

    // Set commander art as blurred background
    const effectiveCmd = getEffectiveCommander();
    const bgArtUrl = getCachedImageUrl(effectiveCmd, 'art_crop') || scryfallImageUrl(effectiveCmd, 'art_crop');
    let bgEl = document.getElementById('commander-bg');
    if (!bgEl) {
      bgEl = document.createElement('div');
      bgEl.id = 'commander-bg';
      document.body.prepend(bgEl);
    }
    bgEl.style.backgroundImage = `url(${bgArtUrl})`;
    bgEl.classList.add('visible');
    if (!getCachedImageUrl(effectiveCmd, 'art_crop')) {
      const probe = new Image();
      probe.onload = () => setCachedImageUrl(effectiveCmd, 'art_crop', bgArtUrl);
      probe.src = bgArtUrl;
    }

    // Update gallery active state
    document.querySelectorAll('.deck-gallery-card').forEach(card => {
      card.classList.toggle('active', card.dataset.deckId === deckId);
    });

    loading.style.display = 'none';

    // Begin deck reveal sequence
    document.body.classList.remove('deck-reveal');
    void document.body.offsetWidth;
    document.body.classList.add('deck-reveal');

    // Update commander info
    const partnerCmd = currentDeck.partner || '';
    commanderName.textContent = partnerCmd
      ? `Commanders: ${effectiveCmd} + ${partnerCmd}`
      : `Commander: ${effectiveCmd}`;
    altCommander.textContent = '';
    renderBracketVisualization();

    // Render commander card images
    let commanderCardsHtml = '';
    const commanderImageUrl = getCachedImageUrl(effectiveCmd, null) || scryfallImageUrl(effectiveCmd);
    commanderCardsHtml += `<img class="commander-card-preview" src="${commanderImageUrl}" alt="${escapeHtml(effectiveCmd)}" loading="lazy" />`;
    if (!getCachedImageUrl(effectiveCmd, null)) {
      const p = new Image(); p.onload = () => setCachedImageUrl(effectiveCmd, null, commanderImageUrl); p.src = commanderImageUrl;
    }
    if (partnerCmd) {
      const partnerImageUrl = getCachedImageUrl(partnerCmd, null) || scryfallImageUrl(partnerCmd);
      commanderCardsHtml += `<img class="commander-card-preview" src="${partnerImageUrl}" alt="${escapeHtml(partnerCmd)}" loading="lazy" />`;
      if (!getCachedImageUrl(partnerCmd, null)) {
        const p = new Image(); p.onload = () => setCachedImageUrl(partnerCmd, null, partnerImageUrl); p.src = partnerImageUrl;
      }
    }
    commanderCards.innerHTML = commanderCardsHtml;

    // Initialize tilt effect after DOM is ready
    setTimeout(() => initializeCommanderTilt(), 0);

    // Render deck sigil and start ambient art
    renderDeckSigil();
    startAmbientArt();
    updateTabStates();

    const showDeckChrome = currentView !== 'analytics' && currentView !== 'shopping';
    commanderInfo.style.display = showDeckChrome ? 'block' : 'none';
    upgradeOverview.style.display = showDeckChrome ? 'block' : 'none';

    if (showDeckChrome) {
      mainContent.style.display = 'grid';
    }

    // Render content based on current view
    if (currentView === 'analytics') {
      renderAnalyticsView();
    } else if (currentView === 'shopping') {
      // Add this deck to shopping selection and re-render
      shoppingSelectedDecks.add(deckId);
      renderShoppingList();
    } else {
      renderContent();
    }

    // Add cascade-in class to main content sections
    mainContent.querySelectorAll('.guide-section, .sidebar-section').forEach(el => {
      el.classList.add('cascade-in');
    });

    // Update URL hash
    updateUrlHash();
    savePreferences();
    announceStatus(`Loaded ${currentDeck.name || deckId} deck guide`);
  } catch (err) {
    loading.style.display = 'none';
    error.style.display = 'block';
    error.textContent = `Error loading deck: ${err.message}`;
  }
}

function getMvDisplay(cardName) {
  const metadata = cardMetadataCache.get(cardName);
  if (!metadata || metadata.cmc == null) return '';
  return `<span class="decklist-mv">(${Math.floor(metadata.cmc)})</span>`;
}

function renderDeckList() {
  if (!currentDeck) return;

  if (!currentDeck.decklist) return;
  const highlightNames = new Set(currentDeck.highlights.map(c => c.name));
  const deckList = currentDeck.decklist.map(card => ({
    ...card,
    isHighlighted: highlightNames.has(card.name)
  }));

  // Group by type
  const typeOrder = ['Creature', 'Planeswalker', 'Artifact', 'Enchantment', 'Instant', 'Sorcery', 'Land'];
  const grouped = {};

  deckList.forEach(card => {
    let type = card.type || 'Other';
    if (!typeOrder.includes(type)) {
      if (type.includes('Creature')) type = 'Creature';
      else if (type.includes('Land')) type = 'Land';
      else if (type.includes('Artifact')) type = 'Artifact';
      else if (type.includes('Enchantment')) type = 'Enchantment';
    }
    if (!grouped[type]) grouped[type] = [];
    grouped[type].push(card);
  });

  // Sort cards within each category by CMC
  Object.keys(grouped).forEach(type => {
    grouped[type].sort(compareByCmc);
  });

  // Calculate total count (accounting for Wastes quantity)
  let totalCount = 0;
  deckList.forEach(card => {
    totalCount += card.quantity || 1;
  });
  const effCmd = getEffectiveCommander();
  const partnerName = currentDeck.partner || '';
  const commanderCount = partnerName ? 2 : 1;
  decklistCount.textContent = totalCount + commanderCount;

  // Get commander names to filter from Creatures
  const commanderNames = new Set([effCmd]);
  if (partnerName) commanderNames.add(partnerName);

  // Render categorized deck list
  let html = '';

  // Add Commander section first
  html += `<div class="decklist-category">`;
  html += `<div class="decklist-category-title">Commander${partnerName ? 's' : ''}</div>`;
  html += `<div class="decklist-card commander" data-card-name="${escapeHtml(effCmd)}" tabindex="0" role="button"><input type="checkbox" class="decklist-checkbox" data-card-name="${escapeHtml(effCmd)}"><a href="${getCardmarketUrl(effCmd)}" target="_blank" rel="noopener noreferrer">${escapeHtml(effCmd)}</a>${getMvDisplay(effCmd)}</div>`;
  if (partnerName) {
    html += `<div class="decklist-card commander" data-card-name="${escapeHtml(partnerName)}" tabindex="0" role="button"><input type="checkbox" class="decklist-checkbox" data-card-name="${escapeHtml(partnerName)}"><a href="${getCardmarketUrl(partnerName)}" target="_blank" rel="noopener noreferrer">${escapeHtml(partnerName)}</a>${getMvDisplay(partnerName)}</div>`;
  }
  html += `</div>`;

  typeOrder.forEach(type => {
    if (grouped[type] && grouped[type].length > 0) {
      // Filter out commanders from Creature category
      const filteredCards = type === 'Creature'
        ? grouped[type].filter(card => !commanderNames.has(card.name))
        : grouped[type];

      if (filteredCards.length === 0) return;

      const categoryCount = filteredCards.reduce((sum, c) => sum + (c.quantity || 1), 0);
      html += `<div class="decklist-category">`;
      html += `<div class="decklist-category-title">${escapeHtml(type)}s (${categoryCount})</div>`;
      filteredCards.forEach(card => {
        const addedClass = card.isHighlighted ? ' highlighted' : '';
        const quantity = card.quantity > 1 ? `${card.quantity}x ` : '';
        const cardmarketUrl = getCardmarketUrl(card.name);
        html += `<div class="decklist-card${addedClass}" data-card-name="${escapeHtml(card.name)}" tabindex="0" role="button"><input type="checkbox" class="decklist-checkbox" data-card-name="${escapeHtml(card.name)}">${escapeHtml(quantity)}<a href="${cardmarketUrl}" target="_blank" rel="noopener noreferrer">${escapeHtml(card.name)}</a>${type !== 'Land' ? getMvDisplay(card.name) : ''}</div>`;
      });
      html += `</div>`;
    }
  });

  // Handle any 'Other' types
  if (grouped['Other'] && grouped['Other'].length > 0) {
    html += `<div class="decklist-category">`;
    html += `<div class="decklist-category-title">Other (${grouped['Other'].length})</div>`;
    grouped['Other'].forEach(card => {
      const addedClass = card.isHighlighted ? ' highlighted' : '';
      const cardmarketUrl = getCardmarketUrl(card.name);
      html += `<div class="decklist-card${addedClass}" data-card-name="${escapeHtml(card.name)}" tabindex="0" role="button"><input type="checkbox" class="decklist-checkbox" data-card-name="${escapeHtml(card.name)}"><a href="${cardmarketUrl}" target="_blank" rel="noopener noreferrer">${escapeHtml(card.name)}</a>${getMvDisplay(card.name)}</div>`;
    });
    html += `</div>`;
  }

  decklistContent.innerHTML = html;
  restoreCheckboxState();
}

let decklistGalleryMode = false;

function renderDeckListGallery() {
  if (!currentDeck || !currentDeck.decklist) return;
  const highlightNames = new Set(currentDeck.highlights.map(c => c.name));
  const galleryEl = document.getElementById('decklist-gallery');
  const effCmd = getEffectiveCommander();
  const partnerGallery = currentDeck.partner || '';
  const commanderNames = new Set([effCmd]);
  if (partnerGallery) commanderNames.add(partnerGallery);

  const allCards = currentDeck.decklist
    .filter(c => !commanderNames.has(c.name))
    .map(card => ({ ...card, isHighlighted: highlightNames.has(card.name) }));

  function cardHtml(name, isHighlighted, quantity) {
    const cached = getCachedImageUrl(name, null);
    const imgUrl = cached || scryfallImageUrl(name);
    const imgAttr = cached ? `src="${imgUrl}"` : `data-scryfall-src="${imgUrl}"`;
    const cls = isHighlighted ? ' highlighted' : '';
    const badge = quantity > 1 ? `<span class="gallery-quantity-badge">${quantity}x</span>` : '';
    return `<div class="decklist-gallery-card${cls}" data-card-name="${escapeHtml(name)}" tabindex="0" role="button" aria-label="${escapeHtml(name)}">${badge}<img ${imgAttr} alt="${escapeHtml(name)}" loading="lazy" /></div>`;
  }

  function renderSection(title, cards) {
    if (cards.length === 0) return '';
    const count = cards.reduce((sum, c) => sum + (c.quantity || 1), 0);
    let h = `<div class="gallery-type-section"><div class="gallery-type-header">${escapeHtml(title)} (${count})</div><div class="gallery-stack">`;
    cards.forEach(card => { h += cardHtml(card.name, card.isHighlighted, card.quantity || 1); });
    h += `</div></div>`;
    return h;
  }

  let html = '';

  // Commander section always first
  html += `<div class="gallery-type-section"><div class="gallery-type-header">Commander${partnerGallery ? 's' : ''}</div><div class="gallery-stack">${cardHtml(effCmd, false, 1)}${partnerGallery ? cardHtml(partnerGallery, false, 1) : ''}</div></div>`;

  const sortMode = filterState.sort;

  if (sortMode === 'role') {
    const roleGroups = {};
    allCards.forEach(card => {
      const role = getPrimaryRole(card);
      if (!roleGroups[role]) roleGroups[role] = [];
      roleGroups[role].push(card);
    });
    Object.values(roleGroups).forEach(g => g.sort(compareByCmc));
    const roleOrder = CATEGORY_CONFIG.map(c => c.id);
    roleOrder.forEach(roleId => {
      if (!roleGroups[roleId]) return;
      const config = CATEGORY_CONFIG.find(c => c.id === roleId);
      html += renderSection(config.name, roleGroups[roleId]);
    });
    if (roleGroups['other']) {
      html += renderSection('Other', roleGroups['other']);
    }
  } else if (sortMode === 'name') {
    allCards.sort((a, b) => a.name.localeCompare(b.name));
    html += `<div class="gallery-type-section"><div class="gallery-type-header">All Cards (${allCards.reduce((s, c) => s + (c.quantity || 1), 0)})</div><div class="gallery-stack">`;
    allCards.forEach(card => { html += cardHtml(card.name, card.isHighlighted, card.quantity || 1); });
    html += `</div></div>`;
  } else if (sortMode === 'cmc') {
    allCards.sort(compareByCmc);
    html += `<div class="gallery-type-section"><div class="gallery-type-header">All Cards (${allCards.reduce((s, c) => s + (c.quantity || 1), 0)})</div><div class="gallery-stack">`;
    allCards.forEach(card => { html += cardHtml(card.name, card.isHighlighted, card.quantity || 1); });
    html += `</div></div>`;
  } else {
    // Default: group by type
    const typeOrder = ['Creature', 'Planeswalker', 'Artifact', 'Enchantment', 'Instant', 'Sorcery', 'Land'];
    const grouped = {};
    allCards.forEach(card => {
      let type = card.type || 'Other';
      if (!typeOrder.includes(type)) {
        if (type.includes('Creature')) type = 'Creature';
        else if (type.includes('Land')) type = 'Land';
        else if (type.includes('Artifact')) type = 'Artifact';
        else if (type.includes('Enchantment')) type = 'Enchantment';
      }
      if (!grouped[type]) grouped[type] = [];
      grouped[type].push(card);
    });
    Object.values(grouped).forEach(g => g.sort(compareByCmc));
    typeOrder.forEach(type => {
      if (!grouped[type] || grouped[type].length === 0) return;
      html += renderSection(type + 's', grouped[type]);
    });
    if (grouped['Other'] && grouped['Other'].length > 0) {
      html += renderSection('Other', grouped['Other']);
    }
  }

  galleryEl.innerHTML = html;
  observeScryfallImages(galleryEl);
}

function toggleDecklistView() {
  decklistGalleryMode = !decklistGalleryMode;
  const listEl = document.getElementById('decklist-content');
  const galleryEl = document.getElementById('decklist-gallery');
  const btn = document.getElementById('decklist-view-toggle');

  if (decklistGalleryMode) {
    listEl.style.display = 'none';
    galleryEl.style.display = '';
    btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line></svg> List`;
    renderDeckListGallery();
  } else {
    galleryEl.style.display = 'none';
    listEl.style.display = '';
    btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect></svg> Gallery`;
  }
}

// Generative deck sigil — deterministic geometric symbol from deck data
function renderDeckSigil() {
  const canvas = document.getElementById('deck-sigil');
  if (!canvas || !currentDeck) return;
  const ctx = canvas.getContext('2d');
  const size = canvas.width;
  const cx = size / 2;
  const cy = size / 2;
  ctx.clearRect(0, 0, size, size);

  // Seed RNG from deck id
  let seed = 0;
  for (let i = 0; i < (currentDeck.id || '').length; i++) {
    seed = ((seed << 5) - seed + currentDeck.id.charCodeAt(i)) | 0;
  }
  function seededRand() {
    seed = (seed * 16807 + 0) % 2147483647;
    return (seed & 0x7fffffff) / 2147483647;
  }

  // Derive properties from deck data
  const deckMeta = (deckIndex.commanders || []).find(d => d.id === currentDeck.id);
  const deckColorIds = deckMeta?.colors || ['C'];
  const bracket = parseInt(currentDeck.bracket) || 3;
  const deckSize = (currentDeck.decklist || []).length;
  const creatureCount = (currentDeck.decklist || []).filter(c => (c.type || '').includes('Creature')).length;
  const landCount = (currentDeck.decklist || []).filter(c => c.type === 'Land').length;

  // Color palette from deck identity
  const colorMap = { C: '#a8b5c4', W: '#f9faf4', U: '#0e68ab', B: '#150b00', R: '#d3202a', G: '#00733e' };
  const deckColors = deckColorIds.map(c => colorMap[c] || '#a8b5c4');
  const accentColor = getComputedStyle(document.body).getPropertyValue('--deck-accent').trim() || '#9d4edd';

  // Geometry: polygon sides from bracket (3-7)
  const sides = bracket + 2;
  const outerR = 48;
  const innerR = outerR * (0.4 + creatureCount / deckSize * 0.4);

  // Draw outer polygon
  ctx.strokeStyle = accentColor;
  ctx.lineWidth = 1.5;
  ctx.globalAlpha = 0.6;
  ctx.beginPath();
  for (let i = 0; i <= sides; i++) {
    const angle = (Math.PI * 2 * i / sides) - Math.PI / 2;
    const x = cx + Math.cos(angle) * outerR;
    const y = cy + Math.sin(angle) * outerR;
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  }
  ctx.closePath();
  ctx.stroke();

  // Draw inner star from vertices to center offset
  ctx.globalAlpha = 0.4;
  ctx.lineWidth = 1;
  for (let i = 0; i < sides; i++) {
    const angle = (Math.PI * 2 * i / sides) - Math.PI / 2;
    const outerX = cx + Math.cos(angle) * outerR;
    const outerY = cy + Math.sin(angle) * outerR;
    const innerAngle = angle + Math.PI / sides;
    const innerX = cx + Math.cos(innerAngle) * innerR;
    const innerY = cy + Math.sin(innerAngle) * innerR;
    ctx.beginPath();
    ctx.moveTo(outerX, outerY);
    ctx.lineTo(innerX, innerY);
    ctx.stroke();

    // Connect inner points
    const nextAngle = innerAngle + Math.PI * 2 / sides;
    const nextX = cx + Math.cos(nextAngle) * innerR;
    const nextY = cy + Math.sin(nextAngle) * innerR;
    ctx.beginPath();
    ctx.moveTo(innerX, innerY);
    ctx.lineTo(nextX, nextY);
    ctx.stroke();
  }

  // Draw concentric rings based on land ratio
  const rings = Math.max(1, Math.round(landCount / 10));
  ctx.globalAlpha = 0.15;
  for (let r = 1; r <= rings; r++) {
    ctx.beginPath();
    ctx.arc(cx, cy, outerR * (r / (rings + 1)), 0, Math.PI * 2);
    ctx.stroke();
  }

  // Draw seed-based decorative dots
  ctx.globalAlpha = 0.5;
  const dotCount = Math.min(bracket * 3, 15);
  for (let i = 0; i < dotCount; i++) {
    const angle = seededRand() * Math.PI * 2;
    const dist = seededRand() * outerR * 0.9;
    const dotR = 1 + seededRand() * 2;
    ctx.fillStyle = deckColors[Math.floor(seededRand() * deckColors.length)] || accentColor;
    ctx.beginPath();
    ctx.arc(cx + Math.cos(angle) * dist, cy + Math.sin(angle) * dist, dotR, 0, Math.PI * 2);
    ctx.fill();
  }

  ctx.globalAlpha = 1;
}

// Ambient card art crossfade — cycle highlight cards as faint background
let ambientInterval = null;
function startAmbientArt() {
  stopAmbientArt();
  if (!currentDeck?.highlights?.length) return;

  let ambientEl = document.getElementById('ambient-art');
  if (!ambientEl) {
    ambientEl = document.createElement('div');
    ambientEl.id = 'ambient-art';
    document.body.prepend(ambientEl);
  }

  const cards = currentDeck.highlights
    .slice(0, 8)
    .map(c => c.name);
  let idx = 0;

  function cycle() {
    if (!cards.length) return;
    const cardName = cards[idx % cards.length];
    const artUrl = getCachedImageUrl(cardName, 'art_crop') || scryfallImageUrl(cardName, 'art_crop');
    ambientEl.style.backgroundImage = `url(${artUrl})`;
    if (!getCachedImageUrl(cardName, 'art_crop')) {
      const p = new Image(); p.onload = () => setCachedImageUrl(cardName, 'art_crop', artUrl); p.src = artUrl;
    }
    ambientEl.classList.add('visible');
    idx++;
  }

  cycle();
  ambientInterval = setInterval(cycle, 15000);
}

function stopAmbientArt() {
  if (ambientInterval) {
    clearInterval(ambientInterval);
    ambientInterval = null;
  }
  const el = document.getElementById('ambient-art');
  if (el) el.classList.remove('visible');
}

// === RENDER CONTENT ===
async function renderContent() {
  await renderGuide();

  // Render deck statistics
  renderDeckStats();

  // Update bracket bar
  renderBracketVisualization();

  // Update summary stats
  if (currentDeck) {
    summaryCost.textContent = currentDeck.cost;
    summaryChangers.textContent = currentDeck.gameChangers;
  }

  // Apply any active filters
  if (filterState.cmc !== 'all' || filterState.type !== 'all' || filterState.sort !== 'type' || filterState.category !== 'all') {
    applyFilters();
  }

  // Save preferences
  savePreferences();
}

// === GUIDE VIEW RENDERING ===
async function renderGuide() {
  if (!currentDeck) return;

  // Show loading state
  guideView.classList.add('is-loading');

  const guideContent = currentDeck.guideContent;

  // Collect all card names for pre-fetching metadata
  const allCardNames = new Set();

  // Collect from decklist
  if (currentDeck.decklist) {
    currentDeck.decklist.forEach(card => allCardNames.add(card.name));
  }

  // Add cards from add categories
  currentDeck.categories.forEach(category => {
    category.cards.forEach(cardName => allCardNames.add(cardName));
  });

  // Add commander(s)
  allCardNames.add(getEffectiveCommander());
  if (currentDeck.partner) allCardNames.add(currentDeck.partner);

  // Pre-fetch metadata for all cards using batch API
  await fetchCardMetadataBatch(Array.from(allCardNames));

  // Render strategy overview
  document.getElementById('strategy-content').textContent = guideContent.strategyOverview;
  renderTierSources(currentDeck);

  // Update section headers
  document.getElementById('engine-header').textContent = 'Deck Engine';
  document.querySelector('.guide-section.deck-engine')?.setAttribute('aria-label', 'Deck engine section');
  renderCommanderThemeGroups(currentDeck.categories, currentDeck.highlights);
  // Render win conditions and synergies
  renderWinConditions(currentDeck.winConditions || []);
  renderSynergies(currentDeck.synergies);
  renderCombos(currentDeck.synergies);
  renderTokens(currentDeck.tokens || []);

  // Render upgrade paths (non-blocking)
  renderUpgradePaths();

  // Render full deck list
  renderDeckList();

  // Hide loading state
  guideView.classList.remove('is-loading');
}

function renderCommanderThemeGroups(categories, highlights) {
  const highlightsMap = new Map(highlights.map(a => [a.name, a]));
  const categorizedCards = new Set();

  let html = categories.map(category => {
    category.cards.forEach(c => categorizedCards.add(c));

    const gameChangerCount = category.cards.filter(name => {
      const cardData = highlightsMap.get(name);
      return cardData?.isGameChanger;
    }).length;

    const gcBadge = gameChangerCount > 0
      ? `<span class="game-changer-warning">${escapeHtml(String(gameChangerCount))} Game Changer${gameChangerCount > 1 ? 's' : ''}</span>`
      : '';

    const cardsHtml = category.cards.map(cardName => {
      const cardData = highlightsMap.get(cardName);
      const metadata = cardMetadataCache.get(cardName);
      const manaCost = metadata?.mana_cost || null;
      return createGuideCardHtml(
        cardName,
        cardData?.reason || '',
        cardData?.isGameChanger || false,
        manaCost
      );
    }).join('');

    const descriptionHtml = category.description
      ? `<div class="card-group-description">${escapeHtml(category.description)}</div>`
      : '';

    return `
      <div class="card-group">
        <div class="card-group-header">
          <div class="card-group-name">${escapeHtml(category.name)}${gcBadge}</div>
          ${descriptionHtml}
        </div>
        ${cardsHtml}
      </div>
    `;
  }).join('');

  // Orphan safety net: cards in highlights not in any category
  const orphans = highlights.filter(a => !categorizedCards.has(a.name));
  if (orphans.length > 0) {
    const orphanCardsHtml = orphans.map(cardData => {
      const metadata = cardMetadataCache.get(cardData.name);
      const manaCost = metadata?.mana_cost || null;
      return createGuideCardHtml(
        cardData.name,
        cardData.reason || '',
        cardData.isGameChanger || false,
        manaCost
      );
    }).join('');

    html += `
      <div class="card-group">
        <div class="card-group-header">
          <div class="card-group-name">Other Highlights</div>
          <div class="card-group-description">Additional notable cards in this build.</div>
        </div>
        ${orphanCardsHtml}
      </div>
    `;
  }

  addGroups.innerHTML = html;
  observeScryfallImages(addGroups);
  addGuideCardHoverEvents();
}



function createGuideCardHtml(cardName, reason, isGameChanger, manaCost = null) {
  const safeCardName = escapeHtml(cardName);
  const cached = getCachedImageUrl(cardName, 'art_crop');
  const imageUrl = cached || scryfallImageUrl(cardName, 'art_crop');
  const imgAttr = cached ? `src="${imageUrl}"` : `data-scryfall-src="${imageUrl}"`;
  const targetBracket = escapeHtml(currentDeck?.bracket || '3');
  const tooltipText = `Game Changer: Moves deck to Bracket ${targetBracket}`;
  const starHtml = isGameChanger ? `<span class="game-changer-star" data-tooltip="${tooltipText}" title="${tooltipText}">★</span>` : '';
  const manaCostHtml = manaCost ? `<span class="mana-cost">${renderManaCost(manaCost)}</span>` : '';
  const cardNameHtml = `<a href="${getCardmarketUrl(cardName)}" target="_blank" rel="noopener noreferrer">${safeCardName}</a>`;
  const reasonAttr = reason ? ` title="${escapeHtml(reason)}"` : '';

  return `
    <div class="guide-card" data-card-name="${safeCardName}" tabindex="0" role="button" aria-label="View ${safeCardName}"${reasonAttr}>
      <img class="guide-card-image" ${imgAttr} alt="${safeCardName}" loading="lazy" />
      <div class="guide-card-info">
        <div class="guide-card-name">${starHtml}${cardNameHtml}${manaCostHtml}</div>
      </div>
    </div>
  `;
}

// Build synergy graph for interactive explorer
function buildSynergyGraph(synergies) {
  const graph = new Map();
  const cardToSynergies = new Map(); // Maps card name to synergy info

  synergies.forEach(synergy => {
    synergy.cards.forEach(card => {
      if (!graph.has(card)) graph.set(card, new Set());
      if (!cardToSynergies.has(card)) cardToSynergies.set(card, []);

      cardToSynergies.get(card).push({ title: synergy.title, description: synergy.description });

      synergy.cards.forEach(related => {
        if (related !== card) graph.get(card).add(related);
      });
    });
  });

  return { graph, cardToSynergies };
}

// Highlight synergy cards in explore mode
function highlightSynergyCards(cardName) {
  // Remove existing highlights
  document.querySelectorAll('.synergy-highlight, .synergy-selected').forEach(el => {
    el.classList.remove('synergy-highlight', 'synergy-selected');
  });

  if (!cardName || !synergyGraph.has(cardName)) return;

  // Mark the selected card
  document.querySelectorAll(`[data-card-name="${CSS.escape(cardName)}"]`).forEach(el => {
    el.classList.add('synergy-selected');
  });

  // Highlight related cards
  const related = synergyGraph.get(cardName);
  if (related) {
    related.forEach(relatedCard => {
      document.querySelectorAll(`[data-card-name="${CSS.escape(relatedCard)}"]`).forEach(el => {
        el.classList.add('synergy-highlight');
      });
    });
  }
}

// Clear all synergy highlights
function clearSynergyHighlights() {
  document.querySelectorAll('.synergy-highlight, .synergy-selected').forEach(el => {
    el.classList.remove('synergy-highlight', 'synergy-selected');
  });
}

function renderWinConditions(winConditions) {
  const section = document.getElementById('wincons-section');
  if (!winConditions || winConditions.length === 0) {
    section.style.display = 'none';
    return;
  }
  section.style.display = '';
  winconsList.innerHTML = winConditions.map(wc => {
    const cardTags = wc.cards.map(cardName =>
      `<span class="synergy-card-tag" data-card-name="${escapeHtml(cardName)}" tabindex="0" role="button" aria-label="View ${escapeHtml(cardName)}">${escapeHtml(cardName)}</span>`
    ).join('');
    return `
      <div class="wincon-item">
        <div class="wincon-title">${escapeHtml(wc.title)}</div>
        <div class="wincon-cards">${cardTags}</div>
        <div class="wincon-description">${escapeHtml(wc.description)}</div>
      </div>
    `;
  }).join('');
}

let exploreModeActive = false;

function renderSynergies(synergies) {
  // Build synergy graph from ALL synergies (combos + non-combos) — keeps explore mode intact
  const { graph, cardToSynergies } = buildSynergyGraph(synergies);
  synergyGraph = graph;

  // Render only non-combo synergies (combos go in dedicated section)
  const nonCombos = synergies.filter(s => !s.sources?.some(src => src.type === 'commanderspellbook'));

  const synergiesSection = document.querySelector('.guide-section.synergies');
  if (nonCombos.length === 0) {
    synergiesSection.style.display = 'none';
  } else {
    synergiesSection.style.display = '';
  }

  synergiesList.innerHTML = nonCombos.map(synergy => {
    const cardTags = synergy.cards.map(cardName =>
      `<span class="synergy-card-tag" data-card-name="${escapeHtml(cardName)}" tabindex="0" role="button" aria-label="View ${escapeHtml(cardName)}">${escapeHtml(cardName)}</span>`
    ).join('');
    return `
      <div class="synergy-item">
        <div class="synergy-title">${escapeHtml(synergy.title)}</div>
        <div class="synergy-cards">${cardTags}</div>
        <div class="synergy-description">${escapeHtml(synergy.description)}</div>
      </div>
    `;
  }).join('');

}

function renderCombos(synergies) {
  const combos = synergies.filter(s => s.sources?.some(src => src.type === 'commanderspellbook'));
  const combosSection = document.getElementById('combos-section');
  const comboCount = document.getElementById('combo-count');

  if (combos.length === 0) {
    combosSection.style.display = 'none';
    return;
  }

  combosSection.style.display = '';
  comboCount.textContent = `(${combos.length})`;

  combosList.innerHTML = combos.map(combo => {
    const cardTags = combo.cards.map(cardName =>
      `<span class="synergy-card-tag" data-card-name="${escapeHtml(cardName)}" tabindex="0" role="button" aria-label="View ${escapeHtml(cardName)}">${escapeHtml(cardName)}</span>`
    ).join('');

    const csbSource = combo.sources.find(s => s.type === 'commanderspellbook');
    const resultBadge = csbSource?.detail
      ? `<span class="combo-result-badge">${escapeHtml(csbSource.detail)}</span>`
      : '';
    const sourceLink = csbSource?.url
      ? `<a class="combo-source-link" href="${escapeHtml(csbSource.url)}" target="_blank" rel="noopener noreferrer">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
          Commander Spellbook
        </a>`
      : '';

    return `
      <div class="combo-item">
        <div class="combo-title">${escapeHtml(combo.title)}</div>
        ${resultBadge}
        <div class="synergy-cards">${cardTags}</div>
        <div class="combo-steps">${escapeHtml(combo.description)}</div>
        ${sourceLink}
      </div>
    `;
  }).join('');
}

function renderTokens(tokens) {
  const tokensSection = document.getElementById('tokens-section');
  const tokenCount = document.getElementById('token-count');

  if (!tokens || tokens.length === 0) {
    tokensSection.style.display = 'none';
    return;
  }

  tokensSection.style.display = '';
  tokenCount.textContent = `(${tokens.length})`;

  document.getElementById('tokens-list').innerHTML = tokens.map(token => {
    const pt = token.power != null && token.toughness != null
      ? `<div class="token-card-details">${escapeHtml(token.power)}/${escapeHtml(token.toughness)}</div>`
      : '';
    const producers = token.produced_by.map(name =>
      `<span class="producer-name" data-card-name="${escapeHtml(name)}" tabindex="0" role="button">${escapeHtml(name)}</span>`
    ).join(', ');

    return `
      <div class="token-card">
        ${token.image_uri ? `<img class="token-card-image" src="${escapeHtml(token.image_uri)}" alt="${escapeHtml(token.name)} token" loading="lazy" />` : ''}
        <div class="token-card-name">${escapeHtml(token.name)}</div>
        ${pt}
        <div class="token-card-producers">Created by: ${producers}</div>
      </div>
    `;
  }).join('');
}

function addGuideCardHoverEvents() {
  // Event delegation handles hover/click/keyboard — see setupDelegatedListeners()
}

// Synergy constellation map
let constellationVisible = false;

function renderConstellationMap() {
  if (!currentDeck?.synergies?.length) return;
  const svg = document.getElementById('synergy-svg');
  if (!svg) return;

  const W = 800, H = 500;
  const synergies = currentDeck.synergies;

  // Collect unique cards and edges
  const cardSet = new Set();
  const edges = [];
  synergies.forEach(syn => {
    syn.cards.forEach(c => cardSet.add(c));
    for (let i = 0; i < syn.cards.length; i++) {
      for (let j = i + 1; j < syn.cards.length; j++) {
        edges.push([syn.cards[i], syn.cards[j]]);
      }
    }
  });

  const cards = Array.from(cardSet);
  const accentColor = getComputedStyle(document.body).getPropertyValue('--deck-accent').trim() || '#9d4edd';

  // Simple radial + jitter layout (no iterative simulation needed)
  const nodes = {};
  const centerX = W / 2, centerY = H / 2;
  const radius = Math.min(W, H) * 0.38;

  // Seed RNG from deck id for deterministic placement
  let seed = 0;
  for (let i = 0; i < (currentDeck.id || '').length; i++) {
    seed = ((seed << 5) - seed + currentDeck.id.charCodeAt(i)) | 0;
  }
  function sRand() {
    seed = (seed * 16807 + 0) % 2147483647;
    return (seed & 0x7fffffff) / 2147483647;
  }

  cards.forEach((name, i) => {
    const angle = (Math.PI * 2 * i / cards.length) - Math.PI / 2;
    const jitterR = radius * (0.7 + sRand() * 0.3);
    nodes[name] = {
      x: centerX + Math.cos(angle) * jitterR,
      y: centerY + Math.sin(angle) * jitterR,
      name
    };
  });

  // Build SVG
  let svgContent = '';

  // Edges
  edges.forEach(([a, b]) => {
    const na = nodes[a], nb = nodes[b];
    if (na && nb) {
      svgContent += `<line class="edge-line" data-from="${escapeHtml(a)}" data-to="${escapeHtml(b)}" x1="${na.x}" y1="${na.y}" x2="${nb.x}" y2="${nb.y}" />`;
    }
  });

  // Nodes
  cards.forEach(name => {
    const n = nodes[name];
    const connectionCount = edges.filter(([a, b]) => a === name || b === name).length;
    const r = Math.min(3 + connectionCount, 7);
    svgContent += `<circle class="node-circle" data-card="${escapeHtml(name)}" cx="${n.x}" cy="${n.y}" r="${r}" fill="${accentColor}" opacity="0.7" />`;
    svgContent += `<text class="node-label" x="${n.x}" y="${n.y - r - 3}" text-anchor="middle">${escapeHtml(name.length > 20 ? name.slice(0, 18) + '...' : name)}</text>`;
  });

  svg.innerHTML = svgContent;

  // Hover + touch interactions
  let activeConstellationNode = null;

  function highlightNode(cardName) {
    svg.querySelectorAll('.edge-line').forEach(line => {
      const isConnected = line.dataset.from === cardName || line.dataset.to === cardName;
      line.classList.toggle('active', isConnected);
    });
    const connected = new Set([cardName]);
    edges.forEach(([a, b]) => {
      if (a === cardName) connected.add(b);
      if (b === cardName) connected.add(a);
    });
    svg.querySelectorAll('.node-circle').forEach(n => {
      n.classList.toggle('dimmed', !connected.has(n.dataset.card));
    });
    svg.querySelectorAll('.node-label').forEach(l => {
      const labelCard = cards.find(c => l.textContent.startsWith(c.slice(0, 18)));
      l.classList.toggle('dimmed', labelCard && !connected.has(labelCard));
    });
    showCardPreview(cardName);
    activeConstellationNode = cardName;
  }

  function clearHighlight() {
    svg.querySelectorAll('.edge-line').forEach(l => l.classList.remove('active'));
    svg.querySelectorAll('.node-circle, .node-label').forEach(n => n.classList.remove('dimmed'));
    activeConstellationNode = null;
  }

  svg.querySelectorAll('.node-circle').forEach(circle => {
    circle.addEventListener('mouseenter', () => highlightNode(circle.dataset.card));
    circle.addEventListener('mouseleave', clearHighlight);
    // Touch: tap to highlight, tap again or tap elsewhere to clear
    circle.addEventListener('click', (e) => {
      e.stopPropagation();
      const cardName = circle.dataset.card;
      if (activeConstellationNode === cardName) {
        clearHighlight();
      } else {
        highlightNode(cardName);
      }
    });
  });

  // Tap outside nodes to clear highlight
  svg.addEventListener('click', (e) => {
    if (!e.target.classList.contains('node-circle')) clearHighlight();
  });
}

function toggleConstellationMap() {
  constellationVisible = !constellationVisible;
  const container = document.getElementById('synergy-constellation');
  container.style.display = constellationVisible ? '' : 'none';
  if (constellationVisible) renderConstellationMap();
}

// === CARD PREVIEW ===
function showCardPreview(cardName) {
  currentHoveredCard = cardName;
  previewName.textContent = cardName;

  // Check cache first
  const cached = getCachedImageUrl(cardName, null);
  if (cached) {
    displayImage(cached);
    return;
  }

  // Show loading state
  previewContainer.innerHTML = '<span class="preview-placeholder">Loading...</span>';

  // Fetch from Scryfall
  const imageUrl = scryfallImageUrl(cardName);

  const img = new Image();
  img.onload = () => {
    setCachedImageUrl(cardName, null, imageUrl);
    if (currentHoveredCard === cardName) {
      displayImage(imageUrl);
    }
  };
  img.onerror = () => {
    if (currentHoveredCard === cardName) {
      previewContainer.innerHTML = '<span class="preview-placeholder">Image not found</span>';
    }
  };
  img.src = imageUrl;
}

function displayImage(url) {
  previewContainer.innerHTML = '';
  const img = document.createElement('img');
  img.src = url;
  img.alt = currentHoveredCard;
  img.onload = () => {
    img.classList.add('loaded');
    // Initialize tilt for preview image
    initializeTiltEffect(img, { maxTilt: 15, scale: 1.02, glare: true });
  };
  previewContainer.appendChild(img);
}

// === EVENT LISTENERS ===

deckSelect.addEventListener('change', (e) => {
  selectDeck(e.target.value);
});

// Close preview on tap elsewhere (mobile)
document.addEventListener('touchstart', (e) => {
  if (!e.target.closest('.card-name') && !e.target.closest('.preview-panel')) {
    previewContainer.innerHTML = '<span class="preview-placeholder">Tap a card name</span>';
    previewName.textContent = '';
    currentHoveredCard = null;
  }
});

// === BRACKET INFO MODAL ===
document.querySelector('.bracket-info-icon').addEventListener('click', () => {
  document.getElementById('bracket-info-modal').classList.add('visible');
  bracketFocusTrap.activate();
});

function closeBracketInfoModal() {
  document.getElementById('bracket-info-modal').classList.remove('visible');
  bracketFocusTrap.deactivate();
}

document.getElementById('bracket-info-modal-close').addEventListener('click', closeBracketInfoModal);

document.getElementById('bracket-info-modal').addEventListener('click', (e) => {
  if (e.target.id === 'bracket-info-modal') {
    closeBracketInfoModal();
  }
});

// === URL DEEP LINKING ===
function parseUrlHash() {
  const hash = window.location.hash.slice(1);
  if (!hash) return { deck: null };

  const params = {};
  hash.split('&').forEach(part => {
    const [key, value] = part.split('=');
    if (key && value) {
      params[key] = decodeURIComponent(value);
    }
  });

  return {
    deck: params.deck || null,
    view: params.view || null
  };
}

function updateUrlHash() {
  if (!currentDeckId) return;
  let hash = '';
  if (currentView && currentView !== 'guide') {
    hash += `view=${encodeURIComponent(currentView)}&`;
  }
  hash += `deck=${encodeURIComponent(currentDeckId)}`;
  history.replaceState(null, '', `#${hash}`);
}

// === FILTER STATE ===
let filterState = {
  cmc: 'all',
  type: 'all',
  sort: 'type',
  category: 'all'
};

// === DECK EXPORT FUNCTIONS ===
function generateDecklistExport(format) {
  if (!currentDeck) return '';

  let deckCards = (currentDeck.decklist || []).map(card => ({
    name: card.name, quantity: card.quantity || 1
  }));

  // Filter to selected cards only if any are selected
  if (selectedCards.size > 0) {
    deckCards = deckCards.filter(card => selectedCards.has(card.name));
  }

  // Add commander(s)
  const effCmdExport = getEffectiveCommander();
  const partnerExport = currentDeck.partner || '';
  const commanderSection = [];
  if (selectedCards.size === 0 || selectedCards.has(effCmdExport)) {
    commanderSection.push(effCmdExport);
  }
  if (partnerExport && (selectedCards.size === 0 || selectedCards.has(partnerExport))) {
    commanderSection.push(partnerExport);
  }

  switch (format) {
    case 'plain':
      let plainText = '';
      if (commanderSection.length > 0) {
        plainText += '// Commander\n';
        commanderSection.forEach(c => plainText += `1x ${c}\n`);
        plainText += '\n';
      }
      plainText += '// Deck\n';
      deckCards.forEach(card => plainText += `${card.quantity}x ${card.name}\n`);
      return plainText;

    case 'arena':
      let arenaText = '';
      if (commanderSection.length > 0) {
        arenaText += 'Commander\n';
        commanderSection.forEach(c => arenaText += `1 ${c}\n`);
        arenaText += '\n';
      }
      arenaText += 'Deck\n';
      deckCards.forEach(card => arenaText += `${card.quantity} ${card.name}\n`);
      return arenaText;

    case 'moxfield':
    case 'archidekt':
      // For these, we'll generate a text list and open in new tab
      let importText = '';
      commanderSection.forEach(c => importText += `1 ${c} *CMDR*\n`);
      deckCards.forEach(card => importText += `${card.quantity} ${card.name}\n`);
      return importText;

    default:
      return '';
  }
}

async function copyToClipboard(text, button) {
  try {
    await navigator.clipboard.writeText(text);
    button.classList.add('success');
    const originalText = button.innerHTML;
    button.innerHTML = button.innerHTML.replace(/Copy Deck|Copy Selected \(\d+\)|Copy Shopping List|Moxfield|Archidekt|Copy|Export List|Export Cuts/, 'Copied!');
    setTimeout(() => {
      button.classList.remove('success');
      button.innerHTML = originalText;
    }, 2000);
  } catch (err) {
    console.error('Failed to copy:', err);
    alert('Failed to copy to clipboard. Please try again.');
  }
}

function generateAddsListExport() {
  if (!currentDeck) return '';

  // Cardmarket format: one card per line, quantity prefix
  return currentDeck.highlights.map(card => `1 ${card.name}`).join('\n');
}

function openMoxfieldImport(deckList, button) {
  copyToClipboard(deckList, button || document.getElementById('copy-deck-btn'));
  window.open('https://www.moxfield.com/decks/new', '_blank');
}

function openArchidektImport(deckList, button) {
  copyToClipboard(deckList, button || document.getElementById('copy-deck-btn'));
  window.open('https://archidekt.com/decks', '_blank');
}

// === QUICK SEARCH ===
let searchResults = [];
let selectedResultIndex = -1;

function openSearch() {
  const modal = document.getElementById('search-modal');
  const input = document.getElementById('search-input');
  modal.classList.add('open');
  input.value = '';
  input.focus();
  updateSearchResults('');
  searchFocusTrap.activate();
}

function closeSearch() {
  searchFocusTrap.deactivate();
  document.getElementById('search-modal').classList.remove('open');
  selectedResultIndex = -1;
}

function updateSearchResults(query) {
  if (!currentDeck) return;

  const resultsContainer = document.getElementById('search-results');

  if (!query.trim()) {
    resultsContainer.innerHTML = '<div class="search-empty">Type to search cards in the current deck...</div>';
    searchResults = [];
    return;
  }

  const queryLower = query.toLowerCase();
  searchResults = [];

  // Search in adds / key cards
  const highlightNames = new Set(currentDeck.highlights.map(c => c.name));
  currentDeck.highlights.forEach(card => {
    if (card.name.toLowerCase().includes(queryLower)) {
      searchResults.push({ name: card.name, type: 'add' });
    }
  });

  // Search the full decklist (excluding already-matched adds)
  (currentDeck.decklist || []).forEach(card => {
    if (!highlightNames.has(card.name) && card.name.toLowerCase().includes(queryLower)) {
      searchResults.push({ name: card.name, type: 'deck' });
    }
  });

  if (searchResults.length === 0) {
    resultsContainer.innerHTML = '<div class="search-empty">No cards found matching your search.</div>';
    return;
  }

  // Group results
  const highlights = searchResults.filter(r => r.type === 'add');
  const deck = searchResults.filter(r => r.type === 'deck');

  let html = '';

  if (highlights.length > 0) {
    html += `<div class="search-result-group" role="group" aria-label="Deck Engine">`;
    html += `<div class="search-result-group-title">Deck Engine</div>`;
    highlights.forEach((result, i) => {
      const highlighted = highlightMatch(result.name, query);
      html += `<div class="search-result" data-index="${searchResults.indexOf(result)}" data-card="${escapeHtml(result.name)}">
        <span class="search-result-name">${highlighted}</span>
        <span class="search-result-tag add">Key</span>
      </div>`;
    });
    html += '</div>';
  }

  if (deck.length > 0) {
    html += '<div class="search-result-group" role="group" aria-label="In Deck">';
    html += '<div class="search-result-group-title">In Deck</div>';
    deck.forEach(result => {
      const highlighted = highlightMatch(result.name, query);
      html += `<div class="search-result" data-index="${searchResults.indexOf(result)}" data-card="${escapeHtml(result.name)}">
        <span class="search-result-name">${highlighted}</span>
        <span class="search-result-tag">Deck</span>
      </div>`;
    });
    html += '</div>';
  }

  resultsContainer.innerHTML = html;

  // Add click handlers
  resultsContainer.querySelectorAll('.search-result').forEach(result => {
    result.addEventListener('click', () => {
      selectSearchResult(result.dataset.card);
    });
  });

  selectedResultIndex = -1;
}

function highlightMatch(text, query) {
  const escaped = escapeHtml(text);
  const escapedQuery = escapeHtml(query);
  const regex = new RegExp(`(${escapedQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
  return escaped.replace(regex, '<mark>$1</mark>');
}

function selectSearchResult(cardName) {
  closeSearch();
  showCardPreview(cardName);

  // Try to scroll to the card in the deck list
  const cardElement = document.querySelector(`[data-card-name="${CSS.escape(cardName)}"]`);
  if (cardElement) {
    cardElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
    cardElement.style.outline = '2px solid var(--accent-purple)';
    setTimeout(() => {
      cardElement.style.outline = '';
    }, 2000);
  }
}

function navigateSearchResults(direction) {
  if (searchResults.length === 0) return;

  selectedResultIndex += direction;
  if (selectedResultIndex < 0) selectedResultIndex = searchResults.length - 1;
  if (selectedResultIndex >= searchResults.length) selectedResultIndex = 0;

  document.querySelectorAll('.search-result').forEach((el, i) => {
    el.classList.toggle('selected', parseInt(el.dataset.index) === selectedResultIndex);
  });
}

// === FILTER AND SORT DECK LIST ===
function applyFilters() {
  if (!currentDeck) return;

  if (!currentDeck.decklist) return;
  const highlightNames = new Set(currentDeck.highlights.map(c => c.name));
  let deckList = currentDeck.decklist.map(card => ({
    ...card,
    isHighlighted: highlightNames.has(card.name)
  }));

  // Apply filters
  let filtered = deckList.filter(card => {
    // CMC filter
    if (filterState.cmc !== 'all') {
      const metadata = cardMetadataCache.get(card.name);
      const cmc = Math.floor(metadata?.cmc || 0);
      if (filterState.cmc === '7+') {
        if (cmc < 7) return false;
      } else {
        if (cmc !== parseInt(filterState.cmc)) return false;
      }
    }

    // Type filter
    if (filterState.type !== 'all') {
      const metadata = cardMetadataCache.get(card.name);
      const typeLine = metadata?.type_line || '';
      if (!typeLine.includes(filterState.type) && !(card.type || '').includes(filterState.type)) return false;
    }

    // Category filter (check heuristic detection AND stored role)
    if (filterState.category !== 'all') {
      const catMetadata = cardMetadataCache.get(card.name);
      const categories = categorizeCard(card.name, catMetadata);
      if (!categories.includes(filterState.category) && card.role !== filterState.category) return false;
    }

    return true;
  });

  // Apply sorting
  switch (filterState.sort) {
    case 'name':
      filtered.sort((a, b) => a.name.localeCompare(b.name));
      break;
    case 'cmc':
      filtered.sort(compareByCmc);
      break;
    case 'role':
    case 'type':
    default:
      // Grouped rendering handled in renderFilteredDeckList
      break;
  }

  // Render filtered list
  renderFilteredDeckList(filtered);
  if (decklistGalleryMode) renderDeckListGallery();
}

function renderFilteredDeckList(cards) {
  const effCmdFiltered = getEffectiveCommander();
  const partnerFiltered = currentDeck.partner || '';
  const commanderNames = new Set([effCmdFiltered]);
  if (partnerFiltered) commanderNames.add(partnerFiltered);
  const showCommander = filterState.type === 'all' && filterState.cmc === 'all' && filterState.category === 'all';

  function renderCardLine(card, showMv) {
    const addedClass = card.isHighlighted ? ' highlighted' : '';
    const quantity = card.quantity > 1 ? `${card.quantity}x ` : '';
    const cardmarketUrl = getCardmarketUrl(card.name);
    return `<div class="decklist-card${addedClass}" data-card-name="${escapeHtml(card.name)}" tabindex="0" role="button"><input type="checkbox" class="decklist-checkbox" data-card-name="${escapeHtml(card.name)}">${escapeHtml(quantity)}<a href="${cardmarketUrl}" target="_blank" rel="noopener noreferrer">${escapeHtml(card.name)}</a>${showMv ? getMvDisplay(card.name) : ''}</div>`;
  }

  function renderGroupedList(groups, groupOrder, labelFn, mvFn) {
    let html = '';
    if (showCommander) {
      html += `<div class="decklist-category">`;
      html += `<div class="decklist-category-title">Commander${partnerFiltered ? 's' : ''}</div>`;
      html += `<div class="decklist-card commander" data-card-name="${escapeHtml(effCmdFiltered)}" tabindex="0" role="button"><input type="checkbox" class="decklist-checkbox" data-card-name="${escapeHtml(effCmdFiltered)}"><a href="${getCardmarketUrl(effCmdFiltered)}" target="_blank" rel="noopener noreferrer">${escapeHtml(effCmdFiltered)}</a>${getMvDisplay(effCmdFiltered)}</div>`;
      if (partnerFiltered) {
        html += `<div class="decklist-card commander" data-card-name="${escapeHtml(partnerFiltered)}" tabindex="0" role="button"><input type="checkbox" class="decklist-checkbox" data-card-name="${escapeHtml(partnerFiltered)}"><a href="${getCardmarketUrl(partnerFiltered)}" target="_blank" rel="noopener noreferrer">${escapeHtml(partnerFiltered)}</a>${getMvDisplay(partnerFiltered)}</div>`;
      }
      html += `</div>`;
    }
    groupOrder.forEach(key => {
      if (!groups[key] || groups[key].length === 0) return;
      const groupCards = groups[key].filter(c => !commanderNames.has(c.name));
      if (groupCards.length === 0) return;
      const count = groupCards.reduce((sum, c) => sum + (c.quantity || 1), 0);
      html += `<div class="decklist-category">`;
      html += `<div class="decklist-category-title">${escapeHtml(labelFn(key))} (${count})</div>`;
      groupCards.forEach(card => { html += renderCardLine(card, mvFn(key)); });
      html += `</div>`;
    });
    return html;
  }

  if (filterState.sort === 'type') {
    const typeOrder = ['Creature', 'Planeswalker', 'Artifact', 'Enchantment', 'Instant', 'Sorcery', 'Land'];
    const grouped = {};
    cards.forEach(card => {
      const metadata = cardMetadataCache.get(card.name);
      let type = card.type || 'Other';
      if (metadata && metadata.type_line) {
        const typeLine = metadata.type_line;
        if (typeLine.includes('Creature')) type = 'Creature';
        else if (typeLine.includes('Land')) type = 'Land';
        else if (typeLine.includes('Artifact')) type = 'Artifact';
        else if (typeLine.includes('Enchantment')) type = 'Enchantment';
        else if (typeLine.includes('Instant')) type = 'Instant';
        else if (typeLine.includes('Sorcery')) type = 'Sorcery';
        else if (typeLine.includes('Planeswalker')) type = 'Planeswalker';
      }
      if (!grouped[type]) grouped[type] = [];
      grouped[type].push(card);
    });
    Object.values(grouped).forEach(g => g.sort(compareByCmc));
    const allKeys = [...typeOrder];
    if (grouped['Other']) allKeys.push('Other');
    decklistContent.innerHTML = renderGroupedList(grouped, allKeys,
      key => key + 's',
      key => key !== 'Land'
    );
  } else if (filterState.sort === 'role') {
    const roleGroups = {};
    cards.forEach(card => {
      const role = getPrimaryRole(card);
      if (!roleGroups[role]) roleGroups[role] = [];
      roleGroups[role].push(card);
    });
    Object.values(roleGroups).forEach(g => g.sort(compareByCmc));
    const roleOrder = CATEGORY_CONFIG.map(c => c.id);
    const allKeys = [...roleOrder.filter(id => roleGroups[id])];
    if (roleGroups['other']) allKeys.push('other');
    const roleLabelMap = {};
    CATEGORY_CONFIG.forEach(c => { roleLabelMap[c.id] = c.name; });
    roleLabelMap['other'] = 'Other';
    decklistContent.innerHTML = renderGroupedList(roleGroups, allKeys,
      key => roleLabelMap[key] || key,
      key => key !== 'lands'
    );
  } else {
    // Flat list for name/cmc sort
    let html = '';
    if (showCommander) {
      html += `<div class="decklist-category">`;
      html += `<div class="decklist-category-title">Commander${partnerFiltered ? 's' : ''}</div>`;
      html += `<div class="decklist-card commander" data-card-name="${escapeHtml(effCmdFiltered)}" tabindex="0" role="button"><input type="checkbox" class="decklist-checkbox" data-card-name="${escapeHtml(effCmdFiltered)}"><a href="${getCardmarketUrl(effCmdFiltered)}" target="_blank" rel="noopener noreferrer">${escapeHtml(effCmdFiltered)}</a>${getMvDisplay(effCmdFiltered)}</div>`;
      if (partnerFiltered) {
        html += `<div class="decklist-card commander" data-card-name="${escapeHtml(partnerFiltered)}" tabindex="0" role="button"><input type="checkbox" class="decklist-checkbox" data-card-name="${escapeHtml(partnerFiltered)}"><a href="${getCardmarketUrl(partnerFiltered)}" target="_blank" rel="noopener noreferrer">${escapeHtml(partnerFiltered)}</a>${getMvDisplay(partnerFiltered)}</div>`;
      }
      html += `</div>`;
    }
    html += '<div class="decklist-category">';
    cards.forEach(card => {
      if (commanderNames.has(card.name)) return;
      const metadata = cardMetadataCache.get(card.name);
      const isLand = metadata && metadata.type_line && metadata.type_line.includes('Land');
      html += renderCardLine(card, !isLand);
    });
    html += '</div>';
    decklistContent.innerHTML = html;
  }

  // Update count
  let totalCount = cards.reduce((sum, c) => sum + (c.quantity || 1), 0);
  if (showCommander) totalCount += 1;
  decklistCount.textContent = totalCount;

  // Hover/click/keyboard handled by delegated listeners on decklistContent
  restoreCheckboxState();
}

function resetFilters() {
  filterState = { cmc: 'all', type: 'all', sort: 'type', category: 'all' };

  document.getElementById('filter-cmc').value = 'all';
  document.getElementById('filter-sort').value = 'type';
  document.querySelectorAll('#filter-type-chips .filter-chip').forEach(chip => {
    chip.classList.toggle('active', chip.dataset.type === 'all');
    chip.setAttribute('aria-pressed', chip.dataset.type === 'all');
  });
  document.querySelectorAll('#filter-category-chips .filter-chip').forEach(chip => {
    chip.classList.toggle('active', chip.dataset.category === 'all');
    chip.setAttribute('aria-pressed', chip.dataset.category === 'all');
  });

  renderDeckList();
  if (decklistGalleryMode) renderDeckListGallery();
}

// === LOCALSTORAGE PERSISTENCE ===
function savePreferences() {
  const prefs = {
    lastDeck: currentDeckId,
    filters: filterState
  };
  try { localStorage.setItem('grimoire-prefs', JSON.stringify(prefs)); } catch (e) { /* quota exceeded or private mode */ }
}

function loadPreferences() {
  const stored = localStorage.getItem('grimoire-prefs');
  if (!stored) return null;

  try {
    return JSON.parse(stored);
  } catch {
    return null;
  }
}

// === SHOPPING LIST ===

let shoppingSortMode = 'type'; // 'type' or 'az'
const shoppingSelectedDecks = new Set(); // deck IDs selected for shopping
let ownedCards = new Map(); // cardName -> quantity owned

function loadOwnedCards() {
  try {
    const raw = localStorage.getItem('grimoire-owned-cards');
    if (raw) {
      const parsed = JSON.parse(raw);
      ownedCards = new Map(parsed);
      updateOwnedStatus();
    }
  } catch { /* ignore */ }
}

function saveOwnedCards() {
  try {
    localStorage.setItem('grimoire-owned-cards', JSON.stringify([...ownedCards]));
  } catch { /* quota exceeded */ }
}

function clearOwnedCards() {
  ownedCards = new Map();
  localStorage.removeItem('grimoire-owned-cards');
  updateOwnedStatus();
  renderShoppingList();
}

function parseOwnedFile(text) {
  const cards = new Map();
  text.split('\n').forEach(line => {
    line = line.trim();
    if (!line) return;
    const match = line.match(/^(\d+)x?\s+(.+)$/);
    if (match) {
      const qty = parseInt(match[1], 10);
      const name = match[2].trim();
      cards.set(name, (cards.get(name) || 0) + qty);
    }
  });
  return cards;
}

function updateOwnedStatus() {
  const statusEl = document.getElementById('shopping-owned-status');
  const clearBtn = document.getElementById('shopping-owned-clear');
  const hintEl = document.querySelector('.shopping-upload-hint');
  if (ownedCards.size > 0) {
    const totalCards = [...ownedCards.values()].reduce((s, q) => s + q, 0);
    statusEl.textContent = `${totalCards} owned cards loaded`;
    clearBtn.style.display = '';
    if (hintEl) hintEl.style.display = 'none';
  } else {
    statusEl.textContent = 'Import owned cards';
    clearBtn.style.display = 'none';
    if (hintEl) hintEl.style.display = '';
  }
}

function renderShoppingDeckChips() {
  const chipsEl = document.getElementById('shopping-deck-chips');
  if (!deckIndex?.commanders) return;
  const chipColorMap = { C: '#6B7280', W: '#c4b998', U: '#1a7cc0', B: '#4a3a5c', R: '#c23028', G: '#2d8a56' };
  chipsEl.innerHTML = deckIndex.commanders.map(cmd => {
    const selected = shoppingSelectedDecks.has(cmd.id);
    const colors = cmd.colors || ['C'];
    const colorPips = colors.map(c =>
      `<span class="shopping-chip-pip pip-${escapeHtml(c)}"></span>`
    ).join('');
    const chipColors = colors.map(c => chipColorMap[c] || chipColorMap.C);
    const gradientStart = chipColors[0];
    const gradientEnd = chipColors.length > 1 ? chipColors[chipColors.length - 1] : chipColors[0];
    const chipStyle = selected ? `style="--chip-color-start:${gradientStart};--chip-color-end:${gradientEnd}"` : '';
    return `<button class="shopping-deck-chip${selected ? ' selected' : ''}" data-deck-id="${escapeHtml(cmd.id)}" ${chipStyle}>
      ${colorPips}<span class="shopping-chip-name">${escapeHtml(cmd.name)}</span>
    </button>`;
  }).join('');
}

function normalizeCardType(type) {
  const typeOrder = ['Creature', 'Planeswalker', 'Artifact', 'Enchantment', 'Instant', 'Sorcery', 'Land'];
  if (typeOrder.includes(type)) return type;
  if (type?.includes('Creature')) return 'Creature';
  if (type?.includes('Land')) return 'Land';
  if (type?.includes('Artifact')) return 'Artifact';
  if (type?.includes('Enchantment')) return 'Enchantment';
  return 'Other';
}

const BASIC_LAND_NAMES = new Set([
  'Plains', 'Island', 'Swamp', 'Mountain', 'Forest', 'Wastes',
  'Snow-Covered Plains', 'Snow-Covered Island', 'Snow-Covered Swamp',
  'Snow-Covered Mountain', 'Snow-Covered Forest'
]);

async function aggregateShoppingCards() {
  const cardMap = new Map(); // name -> { quantity: 1, type, isCommander, decks: Set }
  for (const deckId of shoppingSelectedDecks) {
    const deck = await loadDeckData(deckId);
    if (!deck?.decklist) continue;
    const cmd = deck.commander || '';
    const partner = deck.partner || '';
    // Add commander(s) — deduplicated, 1 copy each
    if (cmd) {
      if (!cardMap.has(cmd)) {
        cardMap.set(cmd, { quantity: 1, type: 'Creature', isCommander: true, decks: new Set([deckId]) });
      } else {
        cardMap.get(cmd).decks.add(deckId);
      }
    }
    if (partner) {
      if (!cardMap.has(partner)) {
        cardMap.set(partner, { quantity: 1, type: 'Creature', isCommander: true, decks: new Set([deckId]) });
      } else {
        cardMap.get(partner).decks.add(deckId);
      }
    }
    // Add decklist cards, skipping basic lands — deduplicated across decks
    deck.decklist.forEach(card => {
      const name = card.name;
      if (BASIC_LAND_NAMES.has(name)) return;
      if (!cardMap.has(name)) {
        cardMap.set(name, { quantity: 1, type: normalizeCardType(card.type || 'Other'), isCommander: false, decks: new Set([deckId]) });
      } else {
        cardMap.get(name).decks.add(deckId);
      }
    });
  }
  return cardMap;
}

function splitByOwnership(cardMap) {
  const buy = [];
  const own = [];
  for (const [name, info] of cardMap) {
    const ownedQty = ownedCards.get(name) || 0;
    const needQty = Math.max(0, info.quantity - ownedQty);
    const ownQty = Math.min(info.quantity, ownedQty);
    if (needQty > 0) {
      buy.push({ name, quantity: needQty, type: info.type, isCommander: info.isCommander, decks: info.decks });
    }
    if (ownQty > 0) {
      own.push({ name, quantity: ownQty, type: info.type, isCommander: info.isCommander, decks: info.decks });
    }
  }
  return { buy, own };
}

function renderShoppingCardRows(cards, sortMode) {
  const multiDeck = shoppingSelectedDecks.size > 1;
  if (sortMode === 'az') {
    cards.sort((a, b) => a.name.localeCompare(b.name));
    return cards.map(c => renderShoppingCardRow(c.name, c.quantity, c.type !== 'Land', multiDeck ? c.decks : null)).join('');
  }
  // Group by type
  const typeOrder = ['Creature', 'Planeswalker', 'Artifact', 'Enchantment', 'Instant', 'Sorcery', 'Land', 'Other'];
  const grouped = {};
  const commanders = cards.filter(c => c.isCommander);
  const nonCmd = cards.filter(c => !c.isCommander);
  nonCmd.forEach(card => {
    const t = card.type;
    if (!grouped[t]) grouped[t] = [];
    grouped[t].push(card);
  });
  Object.values(grouped).forEach(arr => arr.sort(compareByCmc));

  let html = '';
  if (commanders.length > 0) {
    const cmdCount = commanders.reduce((s, c) => s + c.quantity, 0);
    html += `<div class="shopping-group-header"><span class="shopping-group-name">Commander${commanders.length > 1 ? 's' : ''}</span><span class="shopping-group-count">(${cmdCount})</span></div>`;
    commanders.forEach(c => { html += renderShoppingCardRow(c.name, c.quantity, true, multiDeck ? c.decks : null); });
  }
  typeOrder.forEach(type => {
    const list = grouped[type];
    if (!list?.length) return;
    const count = list.reduce((s, c) => s + c.quantity, 0);
    html += `<div class="shopping-group-header"><span class="shopping-group-name">${escapeHtml(type)}${type !== 'Other' ? 's' : ''}</span><span class="shopping-group-count">(${count})</span></div>`;
    list.forEach(c => { html += renderShoppingCardRow(c.name, c.quantity, type !== 'Land', multiDeck ? c.decks : null); });
  });
  return html;
}

function renderShoppingCardRow(cardName, quantity, showMana, decks) {
  const qtyPrefix = quantity > 1 ? `${quantity}x ` : '';
  const metadata = cardMetadataCache.get(cardName);
  const cmc = metadata?.cmc != null ? Math.floor(metadata.cmc) : null;
  const manaHtml = (showMana !== false && cmc != null) ? `<span class="shopping-card-mana">${cmc}</span>` : '';
  let deckDotsHtml = '';
  if (decks && decks.size > 0 && deckIndex?.commanders) {
    const dots = [];
    for (const deckId of decks) {
      const cmd = deckIndex.commanders.find(c => c.id === deckId);
      if (!cmd) continue;
      const colors = cmd.colors || ['C'];
      const dotColor = deckDotColor(colors);
      dots.push(`<span class="shopping-deck-dot" style="background:${dotColor}" title="${escapeHtml(cmd.name)}"></span>`);
    }
    if (dots.length > 0) {
      deckDotsHtml = `<span class="shopping-deck-dots">${dots.join('')}</span>`;
    }
  }
  return `<div class="shopping-card-row" data-card-name="${escapeHtml(cardName)}">
    <span class="shopping-card-name">${escapeHtml(qtyPrefix)}${escapeHtml(cardName)}</span>
    ${deckDotsHtml}
    ${manaHtml}
  </div>`;
}

function deckDotColor(colors) {
  const colorMap = { W: '#c4b998', U: '#1a7cc0', B: '#4a3a5c', R: '#c23028', G: '#2d8a56', C: '#6B7280' };
  if (colors.length === 1) return colorMap[colors[0]] || colorMap.C;
  const c1 = colorMap[colors[0]] || colorMap.C;
  const c2 = colorMap[colors[colors.length - 1]] || colorMap.C;
  return `linear-gradient(135deg, ${c1} 50%, ${c2} 50%)`;
}

function generateShoppingExportText() {
  const buyCardsEl = document.getElementById('shopping-buy-cards');
  if (!buyCardsEl) return '';
  const rows = buyCardsEl.querySelectorAll('.shopping-card-row');
  const lines = [];
  rows.forEach(row => {
    const name = row.dataset.cardName;
    const text = row.querySelector('.shopping-card-name')?.textContent?.trim() || '';
    const match = text.match(/^(\d+)x\s+/);
    const qty = match ? parseInt(match[1], 10) : 1;
    lines.push(`${qty}x ${name}`);
  });
  return lines.join('\n');
}

async function renderShoppingList() {
  const emptyEl = document.getElementById('shopping-empty');
  const summaryBar = document.getElementById('shopping-summary-bar');
  const sortToggle = document.getElementById('shopping-sort-toggle');
  const buySection = document.getElementById('shopping-buy-section');
  const ownSection = document.getElementById('shopping-own-section');
  const buyCardsEl = document.getElementById('shopping-buy-cards');
  const ownCardsEl = document.getElementById('shopping-own-cards');
  const buyCountEl = document.getElementById('shopping-buy-count');
  const ownCountEl = document.getElementById('shopping-own-count');
  const totalCountEl = document.getElementById('shopping-card-count');
  const buySectionCount = document.getElementById('shopping-buy-section-count');
  const ownSectionCount = document.getElementById('shopping-own-section-count');

  renderShoppingDeckChips();

  if (shoppingSelectedDecks.size === 0) {
    summaryBar.style.display = 'none';
    sortToggle.style.display = 'none';
    buySection.style.display = 'none';
    ownSection.style.display = 'none';
    emptyEl.style.display = 'flex';
    return;
  }

  const cardMap = await aggregateShoppingCards();
  const { buy, own } = splitByOwnership(cardMap);
  const buyTotal = buy.reduce((s, c) => s + c.quantity, 0);
  const ownTotal = own.reduce((s, c) => s + c.quantity, 0);

  emptyEl.style.display = 'none';
  summaryBar.style.display = 'flex';
  sortToggle.style.display = 'flex';

  buyCountEl.textContent = buyTotal;
  ownCountEl.textContent = ownTotal;
  totalCountEl.textContent = buyTotal + ownTotal;

  // Render buy section
  if (buy.length > 0) {
    buySection.style.display = '';
    buySectionCount.textContent = `(${buyTotal})`;
    buyCardsEl.innerHTML = renderShoppingCardRows(buy, shoppingSortMode);
    animateShoppingRows(buyCardsEl);
  } else {
    buySection.style.display = 'none';
  }

  // Render own section
  if (own.length > 0) {
    ownSection.style.display = '';
    ownSectionCount.textContent = `(${ownTotal})`;
    ownCardsEl.innerHTML = renderShoppingCardRows(own, shoppingSortMode);
    animateShoppingRows(ownCardsEl);
  } else {
    ownSection.style.display = 'none';
  }
}

function animateShoppingRows(container) {
  const rows = container.querySelectorAll('.shopping-card-row, .shopping-group-header');
  rows.forEach((row, i) => {
    row.style.animationDelay = `${Math.min(i * 0.02, 0.6)}s`;
  });
  container.classList.add('shopping-row-animate');
}

// === MOBILE PREVIEW MODAL ===
function showMobilePreview(cardName) {
  if (window.innerWidth > 768) return; // Only on mobile

  const modal = document.getElementById('mobile-preview-modal');
  const img = document.getElementById('mobile-preview-image');
  const name = document.getElementById('mobile-preview-name');

  const imageUrl = getCachedImageUrl(cardName, null) || scryfallImageUrl(cardName);
  img.src = imageUrl;
  img.alt = cardName;
  name.textContent = cardName;
  if (!getCachedImageUrl(cardName, null)) {
    img.addEventListener('load', () => setCachedImageUrl(cardName, null, imageUrl), { once: true });
  }

  modal.classList.add('open');
  mobileFocusTrap.activate();
}

function closeMobilePreview() {
  mobileFocusTrap.deactivate();
  document.getElementById('mobile-preview-modal').classList.remove('open');
}

// === ACCESSIBILITY: ANNOUNCE CARD PREVIEW ===
function announcePreview(cardName) {
  const announcement = document.getElementById('preview-announcement');
  if (announcement) {
    announcement.textContent = `Showing preview for ${cardName}`;
  }
}

// Enhance showCardPreview to announce for screen readers
const originalShowCardPreview = showCardPreview;
showCardPreview = function(cardName) {
  originalShowCardPreview(cardName);
  announcePreview(cardName);

  // On mobile, show full-screen modal
  if (window.innerWidth <= 768) {
    showMobilePreview(cardName);
  }
};

// === EVENT LISTENERS FOR NEW FEATURES ===

// Export dropdown
document.getElementById('copy-deck-btn')?.addEventListener('click', (e) => {
  const menu = document.getElementById('copy-deck-menu');
  const isOpen = menu.classList.contains('open');
  menu.classList.toggle('open');
  e.currentTarget.setAttribute('aria-expanded', !isOpen);
});

// Close dropdown when clicking outside
document.addEventListener('click', (e) => {
  if (!e.target.closest('.export-dropdown')) {
    document.getElementById('copy-deck-menu')?.classList.remove('open');
    document.getElementById('copy-deck-btn')?.setAttribute('aria-expanded', 'false');
  }
});

// Export format buttons
document.querySelectorAll('.export-dropdown-item').forEach(item => {
  item.addEventListener('click', async (e) => {
    const format = e.currentTarget.dataset.format;
    const deckList = generateDecklistExport(format);

    if (format === 'moxfield') {
      openMoxfieldImport(deckList);
    } else if (format === 'archidekt') {
      openArchidektImport(deckList);
    } else {
      await copyToClipboard(deckList, document.getElementById('copy-deck-btn'));
    }

    document.getElementById('copy-deck-menu').classList.remove('open');
  });
});


// Export adds list button
document.getElementById('export-engine-btn')?.addEventListener('click', async (e) => {
  const list = generateAddsListExport();
  await copyToClipboard(list, e.currentTarget);
});

// Print button
document.getElementById('print-btn')?.addEventListener('click', () => {
  window.print();
});

document.getElementById('decklist-view-toggle')?.addEventListener('click', toggleDecklistView);
document.getElementById('synergy-map-btn')?.addEventListener('click', toggleConstellationMap);

// Selection controls
document.getElementById('select-all-btn')?.addEventListener('click', () => selectAllVisible());
document.getElementById('clear-selection-btn')?.addEventListener('click', () => clearSelection());


// Filter controls
document.getElementById('filter-cmc')?.addEventListener('change', (e) => {
  filterState.cmc = e.target.value;
  applyFilters();
});

document.getElementById('filter-sort')?.addEventListener('change', (e) => {
  filterState.sort = e.target.value;
  applyFilters();
});

document.querySelectorAll('#filter-type-chips .filter-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    document.querySelectorAll('#filter-type-chips .filter-chip').forEach(c => {
      c.classList.remove('active');
      c.setAttribute('aria-pressed', 'false');
    });
    chip.classList.add('active');
    chip.setAttribute('aria-pressed', 'true');
    filterState.type = chip.dataset.type;
    applyFilters();
  });
});

document.querySelectorAll('#filter-category-chips .filter-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    document.querySelectorAll('#filter-category-chips .filter-chip').forEach(c => {
      c.classList.remove('active');
      c.setAttribute('aria-pressed', 'false');
    });
    chip.classList.add('active');
    chip.setAttribute('aria-pressed', 'true');
    filterState.category = chip.dataset.category;
    applyFilters();
  });
});

document.getElementById('filter-clear')?.addEventListener('click', resetFilters);

// Synergy Explorer Mode toggle
document.getElementById('explore-mode-btn')?.addEventListener('click', (e) => {
  exploreModeActive = !exploreModeActive;
  const btn = e.currentTarget;
  btn.classList.toggle('active', exploreModeActive);
  btn.setAttribute('aria-pressed', exploreModeActive);

  // Toggle explore mode class on synergies and combos sections
  const synergiesSection = document.querySelector('.guide-section.synergies');
  synergiesSection?.classList.toggle('explore-mode-active', exploreModeActive);
  document.getElementById('combos-section')?.classList.toggle('explore-mode-active', exploreModeActive);

  // Also toggle on cards sections for visual dimming
  document.querySelector('.guide-section.deck-engine')?.classList.toggle('explore-mode-active', exploreModeActive);

  if (!exploreModeActive) {
    clearSynergyHighlights();
  }
});

// Clear highlights when clicking outside cards in explore mode
document.addEventListener('click', (e) => {
  if (exploreModeActive &&
      !e.target.closest('.synergy-card-tag') &&
      !e.target.closest('.guide-card') &&
      !e.target.closest('.synergy-explorer-btn')) {
    clearSynergyHighlights();
  }
});

// Share button
document.getElementById('share-btn')?.addEventListener('click', async (e) => {
  if (!currentDeckId) return;

  // Build share URL
  const url = new URL(window.location.href);
  url.hash = `deck=${encodeURIComponent(currentDeckId)}`;

  try {
    await navigator.clipboard.writeText(url.toString());

    // Show success feedback
    const btn = e.currentTarget;
    const tooltip = document.getElementById('share-tooltip');
    btn.classList.add('success');
    tooltip.classList.add('visible');

    // Reset after delay
    setTimeout(() => {
      btn.classList.remove('success');
      tooltip.classList.remove('visible');
    }, 2000);
  } catch (err) {
    console.error('Failed to copy share URL:', err);
    // Fallback: select and prompt copy
    prompt('Copy this link to share:', url.toString());
  }
});

// Quick search keyboard shortcut
document.addEventListener('keydown', (e) => {
  // Cmd/Ctrl + K to open search
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault();
    openSearch();
  }

  // ESC to close modals
  if (e.key === 'Escape') {
    closeSearch();
    closeMobilePreview();
    closeBracketInfoModal();
  }
});

// Cmd+K search hint click/keyboard
const searchHint = document.getElementById('search-hint');
if (searchHint) {
  searchHint.addEventListener('click', openSearch);
  searchHint.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openSearch(); }
  });
}

// Shopping deck chip toggle
document.getElementById('shopping-deck-chips')?.addEventListener('click', (e) => {
  const chip = e.target.closest('.shopping-deck-chip');
  if (!chip) return;
  const deckId = chip.dataset.deckId;
  if (shoppingSelectedDecks.has(deckId)) {
    shoppingSelectedDecks.delete(deckId);
  } else {
    shoppingSelectedDecks.add(deckId);
  }
  renderShoppingList();
});

// Owned cards file upload
document.getElementById('shopping-owned-upload')?.addEventListener('change', (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    ownedCards = parseOwnedFile(reader.result);
    saveOwnedCards();
    updateOwnedStatus();
    renderShoppingList();
  };
  reader.readAsText(file);
  e.target.value = ''; // allow re-upload of same file
});

// Clear owned cards
document.getElementById('shopping-owned-clear')?.addEventListener('click', clearOwnedCards);

// Shopping section collapse toggle
document.getElementById('shopping-view')?.addEventListener('click', (e) => {
  const header = e.target.closest('.shopping-section-header');
  if (!header) return;
  const section = header.closest('.shopping-section');
  if (section) section.classList.toggle('collapsed');
});

// Shopping list sort toggle
document.getElementById('shopping-sort-toggle')?.addEventListener('click', (e) => {
  const btn = e.target.closest('.shopping-sort-btn');
  if (!btn || btn.classList.contains('active')) return;
  document.querySelectorAll('.shopping-sort-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  shoppingSortMode = btn.dataset.sort;
  renderShoppingList();
});

// Shopping list export buttons (buy list only)
document.getElementById('shopping-copy-btn')?.addEventListener('click', () => {
  const text = generateShoppingExportText();
  if (text) copyToClipboard(text, document.getElementById('shopping-copy-btn'));
});

// Search modal
document.getElementById('search-modal')?.addEventListener('click', (e) => {
  if (e.target.id === 'search-modal') {
    closeSearch();
  }
});

// Debounced search to reduce API calls and improve performance
const debouncedSearch = debounce((value) => updateSearchResults(value), 150);
document.getElementById('search-input')?.addEventListener('input', (e) => {
  debouncedSearch(e.target.value);
});

document.getElementById('search-input')?.addEventListener('keydown', (e) => {
  if (e.key === 'ArrowDown') {
    e.preventDefault();
    navigateSearchResults(1);
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    navigateSearchResults(-1);
  } else if (e.key === 'Enter' && selectedResultIndex >= 0) {
    e.preventDefault();
    selectSearchResult(searchResults[selectedResultIndex].name);
  }
});

// Mobile preview modal close
document.querySelector('.mobile-preview-close')?.addEventListener('click', closeMobilePreview);
document.getElementById('mobile-preview-modal')?.addEventListener('click', (e) => {
  if (e.target.id === 'mobile-preview-modal') {
    closeMobilePreview();
  }
});




function switchView(view) {
  // Prevent switching to disabled tabs
  if (view === 'analytics' && document.getElementById('tab-analytics')?.classList.contains('disabled')) return;
  if (currentView === view) return;

  const container = document.querySelector('.container');
  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function doSwitch() {
    currentView = view;
    const selectorSection = document.querySelector('.selector-section');
    const commanderInfo = document.getElementById('commander-info');
    const upgradeOverview = document.getElementById('deck-overview');
    const mainContent = document.getElementById('main-content');
    const analyticsView = document.getElementById('analytics-view');
    const shoppingView = document.getElementById('shopping-view');

    // Update toggle buttons
    document.querySelectorAll('.view-toggle-btn').forEach(btn => {
      const isActive = btn.dataset.view === view;
      btn.classList.toggle('active', isActive);
      btn.setAttribute('aria-selected', String(isActive));
    });

    // Hide all views first
    selectorSection.style.display = 'none';
    commanderInfo.style.display = 'none';
    upgradeOverview.style.display = 'none';
    mainContent.style.display = 'none';
    analyticsView.style.display = 'none';
    shoppingView.style.display = 'none';

    if (view === 'analytics') {
      analyticsView.style.display = 'block';
      selectorSection.style.display = '';
      if (currentDeckId) {
        renderAnalyticsView();
      }
      updateUrlHash();
    } else if (view === 'shopping') {
      shoppingView.style.display = 'flex';
      // Shopping view is self-contained with its own deck chips
      loadOwnedCards();
      // Pre-select current deck if one is loaded
      if (currentDeckId && shoppingSelectedDecks.size === 0) {
        shoppingSelectedDecks.add(currentDeckId);
      }
      renderShoppingList();
      savePreferences();
      history.replaceState(null, '', '#view=shopping');
    } else {
      // Guide view
      selectorSection.style.display = '';
      if (currentDeck) {
        commanderInfo.style.display = '';
        upgradeOverview.style.display = '';
        mainContent.style.display = '';
      }
      if (currentDeckId) {
        updateUrlHash();
      } else {
        window.location.hash = '';
      }
    }

    // Fade in
    if (!prefersReduced) {
      container.style.opacity = '0';
      container.style.transform = 'translateY(8px)';
      void container.offsetWidth;
      container.style.transition = 'opacity 0.15s ease, transform 0.15s ease';
      container.style.opacity = '1';
      container.style.transform = 'translateY(0)';
      setTimeout(() => {
        container.style.transition = '';
        container.style.transform = '';
      }, 160);
    }
  }

  // Fade out current view, then switch
  if (!prefersReduced) {
    container.style.transition = 'opacity 0.12s ease';
    container.style.opacity = '0';
    setTimeout(doSwitch, 120);
  } else {
    doSwitch();
  }
}

function initViewToggle() {
  document.querySelectorAll('.view-toggle-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      switchView(btn.dataset.view);
    });
  });

}

// === UPGRADE PATHS (RECOMMENDATIONS ENGINE) ===

let recommendationsCache = {};
let ownedCardsSet = null;

async function loadRecommendations(deckId) {
  if (recommendationsCache[deckId]) return recommendationsCache[deckId];
  if (recommendationsCache[deckId] === null) return null;

  try {
    const response = await fetch(`data/commanders/${deckId}/recommendations.json`);
    if (!response.ok) {
      recommendationsCache[deckId] = null;
      return null;
    }
    const data = await response.json();
    recommendationsCache[deckId] = data;
    return data;
  } catch {
    recommendationsCache[deckId] = null;
    return null;
  }
}

async function loadOwnedCards() {
  if (ownedCardsSet !== null) return ownedCardsSet;
  try {
    const response = await fetch('priv_data/owned_formatted.csv');
    if (!response.ok) {
      ownedCardsSet = new Set();
      return ownedCardsSet;
    }
    const text = await response.text();
    ownedCardsSet = new Set();
    for (const line of text.split('\n')) {
      const match = line.trim().match(/^\d+x\s+(.+)$/);
      if (match) ownedCardsSet.add(match[1].trim());
    }
    return ownedCardsSet;
  } catch {
    ownedCardsSet = new Set();
    return ownedCardsSet;
  }
}

function renderScoreRing(score, maxScore = 100) {
  const radius = 16;
  const circumference = 2 * Math.PI * radius;
  const pct = Math.min(score / maxScore, 1);
  const offset = circumference * (1 - pct);
  return `<div class="upgrade-score-ring">
    <svg width="40" height="40" viewBox="0 0 40 40">
      <circle class="ring-bg" cx="20" cy="20" r="${radius}" />
      <circle class="ring-fill" cx="20" cy="20" r="${radius}"
        stroke-dasharray="${circumference}"
        stroke-dashoffset="${offset}" />
    </svg>
  </div>
  <span class="upgrade-score-label">${score}</span>`;
}

function getHealthGradeClass(grade) {
  if (!grade) return '';
  const letter = grade.charAt(0).toUpperCase();
  return `grade-${letter}`;
}

const HEALTH_COMPONENT_LABELS = {
  manaReliability: 'Mana Reliability',
  threatDeployment: 'Threat Deployment',
  interactionDensity: 'Interaction Density',
  comboConsistency: 'Combo Consistency',
  commanderIndependence: 'Commander Independence',
};

const HEALTH_COMPONENT_DESCRIPTIONS = {
  manaReliability: 'How consistently the deck hits land drops and produces the right colors on curve.',
  threatDeployment: 'How quickly and reliably the deck deploys its key threats and win conditions.',
  interactionDensity: 'The density of removal, counterspells, and other answers to opponent threats.',
  comboConsistency: 'How reliably the deck assembles its synergy engines or combo finishers.',
  commanderIndependence: 'How well the deck functions when the commander is unavailable or removed.',
};

async function renderUpgradePaths() {
  const section = document.getElementById('upgrade-paths-section');
  const content = document.getElementById('upgrade-paths-content');
  const countEl = document.getElementById('upgrade-paths-count');
  const ownedToggle = document.getElementById('upgrade-owned-toggle');

  if (!section || !content) return;

  if (!currentDeckId || !currentDeck) {
    section.style.display = 'none';
    return;
  }

  const [recData, owned] = await Promise.all([
    loadRecommendations(currentDeckId),
    loadOwnedCards(),
  ]);

  if (!recData || !recData.recommendations || recData.recommendations.length === 0) {
    section.style.display = 'none';
    return;
  }

  section.style.display = '';

  // Show owned filter toggle if user has owned cards
  if (owned.size > 0) {
    ownedToggle.style.display = '';
  } else {
    ownedToggle.style.display = 'none';
  }

  const showOwnedOnly = document.getElementById('upgrade-owned-filter')?.checked || false;

  let recs = recData.recommendations;

  // Tag owned status from live owned data
  recs.forEach(rec => {
    rec._owned = owned.has(rec.card);
  });

  if (showOwnedOnly) {
    recs = recs.filter(r => r._owned);
  }

  countEl.textContent = recs.length;

  let html = '';

  // Health baseline summary
  const health = recData.healthBaseline;
  if (health && health.grade) {
    const weakLabel = HEALTH_COMPONENT_LABELS[health.weakestComponent] || health.weakestComponent;
    const weakScore = health.components?.[health.weakestComponent];

    // Build component breakdown rows
    let componentRows = '';
    if (health.components) {
      const entries = Object.entries(health.components);
      for (const [key, score] of entries) {
        const label = HEALTH_COMPONENT_LABELS[key] || key;
        const desc = HEALTH_COMPONENT_DESCRIPTIONS[key] || '';
        const isWeakest = key === health.weakestComponent;
        const barColor = score >= 75 ? 'var(--accent-green)' : score >= 50 ? 'var(--accent-gold)' : 'var(--accent-red)';
        componentRows += `<div class="health-component-row${isWeakest ? ' is-weakest' : ''}">
          <div class="health-component-header">
            <span class="health-component-label">${escapeHtml(label)}${isWeakest ? ' <span class="health-weakest-badge">Weakest</span>' : ''}</span>
            <span class="health-component-score" style="color: ${barColor}">${score}</span>
          </div>
          <div class="health-component-bar-track"><div class="health-component-bar-fill" style="width: ${Math.min(score, 100)}%; background: ${barColor}"></div></div>
          <div class="health-component-desc">${escapeHtml(desc)}</div>
        </div>`;
      }
    }

    html += `<details class="upgrade-health-baseline">
      <summary class="upgrade-health-summary">
        <span class="upgrade-health-grade ${getHealthGradeClass(health.grade)}">${escapeHtml(health.grade)}</span>
        <span class="upgrade-health-detail">
          Deck Health: ${health.score}/100
          ${health.weakestComponent ? ` · Weakest: <span class="upgrade-health-weak">${escapeHtml(weakLabel)}${weakScore != null ? ` (${weakScore})` : ''}</span>` : ''}
        </span>
        <span class="health-expand-hint">Details</span>
      </summary>
      <div class="health-breakdown">
        <div class="health-breakdown-intro">Deck Health measures how well the deck performs across 5 key reliability dimensions.</div>
        ${componentRows}
      </div>
    </details>`;
  }

  if (recs.length === 0) {
    html += '<div class="upgrade-empty">No upgrade recommendations available' +
      (showOwnedOnly ? ' in your collection' : '') + '.</div>';
    content.innerHTML = html;
    return;
  }

  for (const rec of recs) {
    const imgUrl = getCachedImageUrl(rec.card, null) || scryfallImageUrl(rec.card);
    const cached = imageCache.get(rec.card);
    const imgAttr = cached ? `src="${cached}"` : `src="" data-scryfall-src="${imgUrl}"`;
    const ownedClass = rec._owned ? ' is-owned' : '';

    // Tags
    let tags = '';
    if (rec.category === 'combo-enabler') {
      tags += '<span class="upgrade-tag upgrade-tag-combo">Combo</span>';
    }
    if (rec.scoring?.healthGapFill > 0) {
      tags += '<span class="upgrade-tag upgrade-tag-health">Health Fix</span>';
    }
    if (rec._owned) {
      tags += '<span class="upgrade-tag upgrade-tag-owned">Owned</span>';
    }
    if (rec.impact?.gameChangerAdded) {
      tags += '<span class="upgrade-tag upgrade-tag-gc">Game Changer</span>';
    }

    // Swap suggestion
    let swapHtml = '';
    if (rec.swapSuggestion) {
      swapHtml = `<div class="upgrade-swap">Swap for <span class="upgrade-swap-cut">${escapeHtml(rec.swapSuggestion.cut)}</span></div>`;
    }

    // Source links
    let sourceHtml = '';
    if (rec.sources) {
      for (const src of rec.sources) {
        if (src.url) {
          sourceHtml += `<a class="upgrade-source-link" href="${sanitizeUrl(src.url)}" target="_blank" rel="noopener">${escapeHtml(src.name || src.type)}</a> `;
        }
      }
    }

    html += `<div class="upgrade-card${ownedClass}" data-card-name="${escapeHtml(rec.card)}">
      <div class="upgrade-card-img">
        <img ${imgAttr} alt="${escapeHtml(rec.card)}" loading="lazy">
      </div>
      <div class="upgrade-card-body">
        <div class="upgrade-card-name">${escapeHtml(rec.card)}</div>
        <div class="upgrade-card-type">${escapeHtml(rec.impact?.typeLine || '')}</div>
        <div class="upgrade-card-rationale">${escapeHtml(rec.rationale || '')}</div>
        <div class="upgrade-card-tags">${tags}</div>
        ${swapHtml}
        ${sourceHtml ? `<div style="margin-top:4px">${sourceHtml}</div>` : ''}
      </div>
      <div class="upgrade-card-score">
        ${renderScoreRing(rec.score)}
      </div>
    </div>`;
  }

  content.innerHTML = html;

  // Lazy-load card images
  content.querySelectorAll('img[data-scryfall-src]').forEach(img => {
    const src = img.dataset.scryfallSrc;
    if (src) {
      img.src = src;
      img.removeAttribute('data-scryfall-src');
    }
  });
}

// Wire up owned-only filter
document.getElementById('upgrade-owned-filter')?.addEventListener('change', () => {
  renderUpgradePaths();
});

// === OPENING HAND SIMULATOR ===

let handSimState = {
  hand: [],
  mulliganCount: 0,
  bottomCards: [],
  phase: 'empty', // empty, drawn, bottoming, kept
  deckPool: [],
};

function getBottomCountForMulliganCount(mulliganCount) {
  return Math.max(0, mulliganCount - 1);
}

function getKeptHandSize(mulliganCount) {
  return Math.max(0, 7 - getBottomCountForMulliganCount(mulliganCount));
}

function shuffleDeck(cards) {
  const arr = [...cards];
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

function drawOpeningHand() {
  if (!currentDeck?.decklist) return;
  handSimState.deckPool = shuffleDeck(currentDeck.decklist);
  handSimState.hand = handSimState.deckPool.splice(0, 7);
  handSimState.mulliganCount = 0;
  handSimState.bottomCards = [];
  handSimState.phase = 'drawn';
  renderHandSimulator();
}

function mulliganHand() {
  if (!currentDeck?.decklist) return;
  handSimState.mulliganCount++;
  // Commander mulligan: first redraw is free, then London bottoming starts.
  handSimState.deckPool = shuffleDeck(currentDeck.decklist);
  handSimState.hand = handSimState.deckPool.splice(0, 7);
  handSimState.bottomCards = [];
  const numToBottom = getBottomCountForMulliganCount(handSimState.mulliganCount);
  if (numToBottom > 0 && numToBottom < 7) {
    handSimState.phase = 'bottoming';
  } else if (numToBottom >= 7) {
    // Mulliganed to 0 — auto-keep
    handSimState.hand = [];
    handSimState.phase = 'kept';
  } else {
    handSimState.phase = 'drawn';
  }
  renderHandSimulator();
}

function bottomCard(index) {
  if (handSimState.phase !== 'bottoming') return;
  const card = handSimState.hand.splice(index, 1)[0];
  handSimState.bottomCards.push(card);
  const numToBottom = getBottomCountForMulliganCount(handSimState.mulliganCount);
  if (handSimState.bottomCards.length >= numToBottom) {
    handSimState.phase = 'kept';
  }
  renderHandSimulator();
}

function keepHand() {
  handSimState.phase = 'kept';
  renderHandSimulator();
}

function assessHand(hand, simData) {
  if (!hand.length) return null;

  const assessment = {};
  let lands = 0;
  let ramp = 0;
  const castable = { byTurn: {} };
  const colors = new Set();
  const commanderCmc = simData?.commanderTiming?.cmc ?? 0;

  hand.forEach(card => {
    const meta = cardMetadataCache.get(card.name);
    if (!meta) return;
    const typeLower = (meta.type_line || '').toLowerCase();
    if (typeLower.includes('land')) {
      lands++;
    }
    if (meta.cmc <= 2 && (typeLower.includes('artifact') || typeLower.includes('creature')) &&
        (meta.oracle_text || '').toLowerCase().includes('add')) {
      ramp++;
    }
    (meta.colors || []).forEach(c => colors.add(c));
  });

  // Land count assessment
  if (lands >= 2 && lands <= 4) {
    assessment.lands = { rating: 'good', label: `${lands} lands` };
  } else if (lands === 1 || lands === 5) {
    assessment.lands = { rating: 'fair', label: `${lands} land${lands !== 1 ? 's' : ''}` };
  } else {
    assessment.lands = { rating: 'poor', label: `${lands} lands` };
  }

  // Mana curve castability — how many non-land cards can be cast by turn 3?
  let castableByT3 = 0;
  const nonLandCards = hand.filter(c => {
    const meta = cardMetadataCache.get(c.name);
    return meta && !(meta.type_line || '').toLowerCase().includes('land');
  });
  nonLandCards.forEach(c => {
    const meta = cardMetadataCache.get(c.name);
    if (meta && meta.cmc <= 3) castableByT3++;
  });
  const totalNonLand = nonLandCards.length;
  assessment.curve = {
    label: `${castableByT3}/${totalNonLand} castable by T3`,
    rating: castableByT3 >= 2 ? 'good' : castableByT3 >= 1 ? 'fair' : 'poor'
  };

  // Commander timing from simulation baselines
  if (simData?.commanderTiming?.byTurn && commanderCmc > 0) {
    // Estimate: does this hand have enough lands + ramp to cast commander on curve?
    const manaByT = lands + ramp; // rough T1 mana projection for lands+ramp in hand
    const cmdCastTurn = Math.max(1, commanderCmc - ramp);
    const simPct = simData.commanderTiming.byTurn[String(cmdCastTurn)] ?? 0;
    assessment.commander = {
      label: `~T${cmdCastTurn} commander`,
      detail: `${simPct.toFixed(0)}% of sims cast by T${cmdCastTurn}`,
      rating: cmdCastTurn <= commanderCmc ? 'good' : cmdCastTurn <= commanderCmc + 1 ? 'fair' : 'poor'
    };
  }

  // Ramp
  if (ramp > 0) {
    assessment.ramp = { label: `${ramp} ramp piece${ramp > 1 ? 's' : ''}`, rating: ramp >= 2 ? 'good' : 'fair' };
  }

  // Land distribution context from simulation
  if (simData?.openingHand?.landDistribution) {
    const pct = simData.openingHand.landDistribution[String(lands)];
    if (pct != null) {
      assessment.landOdds = { label: `${pct.toFixed(1)}% of hands have ${lands} lands`, rating: 'info' };
    }
  }

  return assessment;
}

function renderHandSimulator() {
  const container = document.getElementById('hand-simulator');
  if (!container) return;
  const existingTooltip = document.getElementById('hand-sim-card-tooltip');
  if (existingTooltip) existingTooltip.classList.remove('visible');

  if (!currentDeckId || !currentDeck) {
    container.innerHTML = '';
    container.style.display = 'none';
    return;
  }

  container.style.display = '';
  const { hand, mulliganCount, phase, bottomCards } = handSimState;
  const simData = simulationCache[currentDeckId];

  let html = `<div class="hand-sim">
    <div class="hand-sim-header">
      <h2>Opening Hand</h2>
      <div class="hand-sim-controls">`;

  if (phase === 'empty') {
    html += `<button class="hand-sim-btn hand-sim-btn-primary" onclick="drawOpeningHand()">Draw 7</button>`;
  } else if (phase === 'drawn') {
    html += `<button class="hand-sim-btn hand-sim-btn-primary" onclick="keepHand()">Keep</button>`;
    html += `<button class="hand-sim-btn hand-sim-btn-secondary" onclick="mulliganHand()">Mulligan</button>`;
  } else if (phase === 'bottoming') {
    const remaining = getBottomCountForMulliganCount(mulliganCount) - bottomCards.length;
    html += `<span class="hand-sim-instruction">Put ${remaining} card${remaining !== 1 ? 's' : ''} on bottom</span>`;
  } else if (phase === 'kept') {
    html += `<button class="hand-sim-btn hand-sim-btn-primary" onclick="drawOpeningHand()">New Hand</button>`;
    if (mulliganCount > 0) {
      const keptHandSize = getKeptHandSize(mulliganCount);
      const badgeLabel = mulliganCount === 1
        ? `Kept ${keptHandSize} after free mulligan`
        : `Kept ${keptHandSize} after ${mulliganCount} mulligans`;
      html += `<span class="hand-sim-mulligan-badge">${escapeHtml(badgeLabel)}</span>`;
    }
  }

  html += `</div></div>`;

  if (phase !== 'empty' && hand.length > 0) {
    html += `<div class="hand-sim-cards" role="list">`;
    hand.forEach((card, i) => {
      const meta = cardMetadataCache.get(card.name);
      const typeLine = meta?.type_line || card.type || '';
      const cmc = meta?.cmc != null ? Math.floor(meta.cmc) : '';
      const isBottomable = phase === 'bottoming';
      const imgSrc = scryfallImageUrl(card.name, null);
      const cached = imageCache.get(card.name);
      const imgAttr = cached ? `src="${cached}"` : `src="" data-scryfall-src="${imgSrc}"`;

      html += `<div class="hand-sim-card ${isBottomable ? 'hand-sim-card-selectable' : ''}"
                    role="listitem"
                    ${isBottomable ? `onclick="bottomCard(${i})" tabindex="0" aria-label="Put ${escapeHtml(card.name)} on bottom"` : ''}
                    data-card-name="${escapeHtml(card.name)}">
        <div class="hand-sim-card-img">
          <img ${imgAttr} alt="${escapeHtml(card.name)}" loading="eager">
        </div>
        <div class="hand-sim-card-info">
          <span class="hand-sim-card-name">${escapeHtml(card.name)}</span>
          <span class="hand-sim-card-type">${escapeHtml(typeLine)}${cmc !== '' ? ` (${cmc})` : ''}</span>
        </div>
      </div>`;
    });
    html += `</div>`;

    // Assessment panel (only when kept or on first draw)
    if (phase === 'kept' || phase === 'drawn') {
      const assessment = assessHand(hand, simData);
      if (assessment) {
        html += `<div class="hand-sim-assessment">`;
        for (const [key, val] of Object.entries(assessment)) {
          html += `<div class="hand-sim-badge hand-sim-badge-${val.rating}">
            <span class="hand-sim-badge-label">${escapeHtml(val.label)}</span>
            ${val.detail ? `<span class="hand-sim-badge-detail">${escapeHtml(val.detail)}</span>` : ''}
          </div>`;
        }
        html += `</div>`;
      }
    }
  } else if (phase === 'empty') {
    html += `<div class="hand-sim-empty">
      <p>Draw an opening hand to simulate London mulligans and assess hand quality.</p>
    </div>`;
  } else if (phase === 'kept' && hand.length === 0) {
    html += `<div class="hand-sim-empty"><p>Mulliganed to 0. Try a new hand!</p></div>`;
  }

  html += `</div>`;
  container.innerHTML = html;
  observeScryfallImages(container);
}

// === WHAT-IF SWAP ANALYZER ===
let gameChangersList = null;

async function loadGameChangers() {
  if (gameChangersList) return gameChangersList;
  try {
    const resp = await fetch('data/game-changers.json');
    if (!resp.ok) return null;
    const data = await resp.json();
    gameChangersList = new Set(data.cards || []);
    return gameChangersList;
  } catch { return null; }
}

let swapState = {
  cutCard: null,    // { name, type } from decklist
  addCard: null,    // { name, cmc, colors, mana_cost, type_line, oracle_text } from metadata
  searchQuery: '',
  searchResults: [],
};

function resetSwapState() {
  swapState.cutCard = null;
  swapState.addCard = null;
  swapState.searchQuery = '';
  swapState.searchResults = [];
}

function computeSwapDelta() {
  const { cutCard, addCard } = swapState;
  if (!cutCard || !addCard) return null;

  const cutMeta = cardMetadataCache.get(cutCard.name) || {};
  const addMeta = addCard;

  const delta = {};

  // CMC delta
  const cutCmc = cutMeta.cmc ?? 0;
  const addCmc = addMeta.cmc ?? 0;
  delta.cmcChange = addCmc - cutCmc;

  // Color pip delta
  const cutColors = cutMeta.colors || [];
  const addColors = addMeta.colors || [];
  const colorDelta = {};
  cutColors.forEach(c => { colorDelta[c] = (colorDelta[c] || 0) - 1; });
  addColors.forEach(c => { colorDelta[c] = (colorDelta[c] || 0) + 1; });
  // Remove zero entries
  Object.keys(colorDelta).forEach(k => { if (colorDelta[k] === 0) delete colorDelta[k]; });
  delta.colorDelta = colorDelta;

  // Type change
  const cutType = cutMeta.type_line || cutCard.type || '';
  const addType = addMeta.type_line || '';
  delta.cutType = cutType;
  delta.addType = addType;
  delta.typeChanged = cutType !== addType;

  // Mana cost strings
  delta.cutManaCost = cutMeta.mana_cost || '';
  delta.addManaCost = addMeta.mana_cost || '';

  // Deck CMC impact
  if (currentDeck?.decklist) {
    const deckCards = currentDeck.decklist;
    let totalCmc = 0;
    let nonLandCount = 0;
    deckCards.forEach(card => {
      const qty = card.quantity || 1;
      const meta = cardMetadataCache.get(card.name);
      const typeLine = (meta?.type_line || card.type || '').toLowerCase();
      if (!typeLine.includes('land')) {
        totalCmc += (meta?.cmc ?? 0) * qty;
        nonLandCount += qty;
      }
    });
    const oldAvg = nonLandCount > 0 ? totalCmc / nonLandCount : 0;

    // Adjust for swap
    const cutIsLand = cutType.toLowerCase().includes('land');
    const addIsLand = addType.toLowerCase().includes('land');
    let newTotal = totalCmc;
    let newCount = nonLandCount;
    if (!cutIsLand) { newTotal -= cutCmc; newCount -= 1; }
    if (!addIsLand) { newTotal += addCmc; newCount += 1; }
    const newAvg = newCount > 0 ? newTotal / newCount : 0;
    delta.avgCmcBefore = oldAvg;
    delta.avgCmcAfter = newAvg;
    delta.avgCmcChange = newAvg - oldAvg;

    // Land count impact
    let landCount = 0;
    deckCards.forEach(card => {
      const qty = card.quantity || 1;
      const meta = cardMetadataCache.get(card.name);
      const typeLine = (meta?.type_line || card.type || '').toLowerCase();
      if (typeLine.includes('land')) landCount += qty;
    });
    delta.landsBefore = landCount;
    delta.landsAfter = landCount + (addIsLand ? 1 : 0) - (cutIsLand ? 1 : 0);
  }

  // Game Changer impact
  if (gameChangersList) {
    const cutIsGC = gameChangersList.has(cutCard.name);
    const addIsGC = gameChangersList.has(addCard.name);
    delta.gcCutting = cutIsGC;
    delta.gcAdding = addIsGC;
    delta.gcNetChange = (addIsGC ? 1 : 0) - (cutIsGC ? 1 : 0);
    delta.gcCountBefore = currentDeck?.gameChangers ?? 0;
    delta.gcCountAfter = delta.gcCountBefore + delta.gcNetChange;
  }

  // Combo impact — check if cut card is in any known synergies
  if (currentDeck?.synergies) {
    const cutSynergies = currentDeck.synergies.filter(s =>
      s.cards?.some(c => c.toLowerCase() === cutCard.name.toLowerCase())
    );
    const addSynergies = currentDeck.synergies.filter(s =>
      s.cards?.some(c => c.toLowerCase() === addCard.name.toLowerCase())
    );
    delta.synergiesBroken = cutSynergies;
    delta.synergiesKept = addSynergies;
  }

  return delta;
}

function swapSearchCards(query) {
  if (!query || query.length < 2) {
    swapState.searchResults = [];
    return;
  }
  const q = query.toLowerCase();
  const results = [];
  const inDeck = new Set((currentDeck?.decklist || []).map(c => c.name.toLowerCase()));

  for (const [name, meta] of cardMetadataCache) {
    if (results.length >= 20) break;
    if (inDeck.has(name.toLowerCase())) continue;
    if (name.toLowerCase().includes(q)) {
      results.push({ name, ...meta });
    }
  }
  swapState.searchResults = results;
}

function selectSwapCut(cardName) {
  const card = currentDeck?.decklist?.find(c => c.name === cardName);
  if (card) {
    swapState.cutCard = card;
    renderSwapAnalyzer();
  }
}

function selectSwapAdd(cardName) {
  const meta = cardMetadataCache.get(cardName);
  if (meta) {
    swapState.addCard = { name: cardName, ...meta };
    swapState.searchQuery = '';
    swapState.searchResults = [];
    renderSwapAnalyzer();
  }
}

function clearSwapCut() {
  swapState.cutCard = null;
  renderSwapAnalyzer();
}

function clearSwapAdd() {
  swapState.addCard = null;
  renderSwapAnalyzer();
}

function formatManaCost(manaCost) {
  if (!manaCost) return '';
  return manaCost.replace(/\{([^}]+)\}/g, (_, s) => {
    const sym = s.replace('/', '').toUpperCase();
    return `<span class="swap-mana-symbol swap-mana-${sym}">${sym}</span>`;
  });
}

const COLOR_NAMES = { W: 'White', U: 'Blue', B: 'Black', R: 'Red', G: 'Green' };

function renderSwapAnalyzer() {
  const container = document.getElementById('swap-analyzer');
  if (!container) return;

  if (!currentDeckId || !currentDeck) {
    container.innerHTML = '';
    container.style.display = 'none';
    return;
  }
  container.style.display = '';

  const { cutCard, addCard, searchQuery, searchResults } = swapState;
  const delta = computeSwapDelta();

  let html = `<div class="swap-analyzer">
    <div class="swap-analyzer-header">
      <h2>What-If Swap</h2>
    </div>
    <div class="swap-slots">`;

  // CUT slot
  html += `<div class="swap-slot swap-slot-cut">
    <div class="swap-slot-label">Cut</div>`;
  if (cutCard) {
    const cutMeta = cardMetadataCache.get(cutCard.name) || {};
    const imgSrc = scryfallImageUrl(cutCard.name, null);
    const cached = imageCache.get(cutCard.name);
    const imgAttr = cached ? `src="${cached}"` : `src="" data-scryfall-src="${imgSrc}"`;
    html += `<div class="swap-card swap-card-selected">
      <div class="swap-card-img"><img ${imgAttr} alt="${escapeHtml(cutCard.name)}" loading="eager"></div>
      <div class="swap-card-details">
        <span class="swap-card-name">${escapeHtml(cutCard.name)}</span>
        <span class="swap-card-type">${escapeHtml(cutMeta.type_line || cutCard.type || '')}</span>
        ${cutMeta.mana_cost ? `<span class="swap-card-mana">${formatManaCost(cutMeta.mana_cost)}</span>` : ''}
      </div>
      <button class="swap-card-clear" onclick="clearSwapCut()" aria-label="Clear cut card">&times;</button>
    </div>`;
  } else {
    html += `<div class="swap-card-picker">
      <select class="swap-cut-select" onchange="selectSwapCut(this.value); this.value='';">
        <option value="">Select a card to cut...</option>`;
    // Group decklist by type
    const byType = {};
    (currentDeck.decklist || []).forEach(card => {
      const t = card.type || 'Other';
      if (!byType[t]) byType[t] = [];
      byType[t].push(card.name);
    });
    Object.keys(byType).sort().forEach(type => {
      html += `<optgroup label="${escapeHtml(type)}">`;
      byType[type].sort().forEach(name => {
        html += `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`;
      });
      html += `</optgroup>`;
    });
    html += `</select></div>`;
  }
  html += `</div>`;

  // Swap icon
  html += `<div class="swap-icon-container">
    <svg class="swap-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="28" height="28">
      <path d="M7 16l-4-4 4-4"></path><path d="M17 8l4 4-4 4"></path>
      <line x1="3" y1="12" x2="21" y2="12"></line>
    </svg>
  </div>`;

  // ADD slot
  html += `<div class="swap-slot swap-slot-add">
    <div class="swap-slot-label">Add</div>`;
  if (addCard) {
    const imgSrc = scryfallImageUrl(addCard.name, null);
    const cached = imageCache.get(addCard.name);
    const imgAttr = cached ? `src="${cached}"` : `src="" data-scryfall-src="${imgSrc}"`;
    html += `<div class="swap-card swap-card-selected">
      <div class="swap-card-img"><img ${imgAttr} alt="${escapeHtml(addCard.name)}" loading="eager"></div>
      <div class="swap-card-details">
        <span class="swap-card-name">${escapeHtml(addCard.name)}</span>
        <span class="swap-card-type">${escapeHtml(addCard.type_line || '')}</span>
        ${addCard.mana_cost ? `<span class="swap-card-mana">${formatManaCost(addCard.mana_cost)}</span>` : ''}
      </div>
      <button class="swap-card-clear" onclick="clearSwapAdd()" aria-label="Clear add card">&times;</button>
    </div>`;
  } else {
    html += `<div class="swap-card-picker">
      <input type="text" class="swap-add-search" placeholder="Search cards to add..."
        value="${escapeHtml(searchQuery)}"
        oninput="swapState.searchQuery=this.value; swapSearchCards(this.value); renderSwapSearchResults();">
      <span class="swap-search-hint">Searches cards from loaded deck recommendations</span>`;
    if (searchResults.length > 0) {
      html += `<div class="swap-search-results" onclick="if(event.target.closest('.swap-search-result')){selectSwapAdd(event.target.closest('.swap-search-result').dataset.cardName)}">`;
      searchResults.forEach(card => {
        const cmcStr = card.cmc != null ? ` (${Math.floor(card.cmc)})` : '';
        html += `<button class="swap-search-result" data-card-name="${escapeHtml(card.name)}">
          <span class="swap-result-name">${escapeHtml(card.name)}</span>
          <span class="swap-result-type">${escapeHtml(card.type_line || '')}${cmcStr}</span>
        </button>`;
      });
      html += `</div>`;
    } else if (searchQuery && searchQuery.length >= 2) {
      html += `<div class="swap-search-no-results">No matching cards found in the recommendation pool</div>`;
    }
    html += `</div>`;
  }
  html += `</div>`;

  html += `</div>`; // close swap-slots

  // Delta results
  if (delta) {
    html += renderSwapDelta(delta);
  } else {
    html += `<div class="swap-empty-state">
      <p>Select a card to cut and a card to add to see the impact on your deck.</p>
    </div>`;
  }

  html += `</div>`;
  container.innerHTML = html;
  observeScryfallImages(container);

  // Refocus search input if it was active
  if (!addCard && searchQuery) {
    const input = container.querySelector('.swap-add-search');
    if (input) { input.focus(); input.setSelectionRange(input.value.length, input.value.length); }
  }
}

function renderSwapSearchResults() {
  const container = document.getElementById('swap-analyzer');
  if (!container) return;
  const picker = container.querySelector('.swap-slot-add .swap-card-picker');
  if (!picker) return;

  let existing = picker.querySelector('.swap-search-results');
  if (existing) existing.remove();
  let existingEmpty = picker.querySelector('.swap-search-no-results');
  if (existingEmpty) existingEmpty.remove();

  if (swapState.searchResults.length > 0) {
    let html = `<div class="swap-search-results" onclick="if(event.target.closest('.swap-search-result')){selectSwapAdd(event.target.closest('.swap-search-result').dataset.cardName)}">`;
    swapState.searchResults.forEach(card => {
      const cmcStr = card.cmc != null ? ` (${Math.floor(card.cmc)})` : '';
      html += `<button class="swap-search-result" data-card-name="${escapeHtml(card.name)}">
        <span class="swap-result-name">${escapeHtml(card.name)}</span>
        <span class="swap-result-type">${escapeHtml(card.type_line || '')}${cmcStr}</span>
      </button>`;
    });
    html += `</div>`;
    picker.insertAdjacentHTML('beforeend', html);
  } else if (swapState.searchQuery && swapState.searchQuery.length >= 2) {
    picker.insertAdjacentHTML('beforeend', `<div class="swap-search-no-results">No matching cards found in the recommendation pool</div>`);
  }
}

function renderSwapDelta(delta) {
  let html = `<div class="swap-delta">`;

  // CMC change
  const cmcSign = delta.cmcChange > 0 ? '+' : '';
  const cmcClass = delta.cmcChange === 0 ? 'neutral' : delta.cmcChange > 0 ? 'increase' : 'decrease';
  html += `<div class="swap-delta-row">
    <span class="swap-delta-label">Mana Value</span>
    <div class="swap-delta-values">
      <span class="swap-delta-change swap-delta-${cmcClass}">${cmcSign}${delta.cmcChange}</span>
    </div>
  </div>`;

  // Avg CMC change
  if (delta.avgCmcChange != null) {
    const avgSign = delta.avgCmcChange > 0 ? '+' : '';
    const avgClass = Math.abs(delta.avgCmcChange) < 0.01 ? 'neutral' : delta.avgCmcChange > 0 ? 'increase' : 'decrease';
    html += `<div class="swap-delta-row">
      <span class="swap-delta-label">Avg Mana Value</span>
      <div class="swap-delta-values">
        <span class="swap-delta-detail">${delta.avgCmcBefore.toFixed(2)} → ${delta.avgCmcAfter.toFixed(2)}</span>
        <span class="swap-delta-change swap-delta-${avgClass}">${avgSign}${delta.avgCmcChange.toFixed(2)}</span>
      </div>
    </div>`;
  }

  // Land count change
  if (delta.landsBefore != null && delta.landsBefore !== delta.landsAfter) {
    const landSign = delta.landsAfter > delta.landsBefore ? '+' : '';
    const landDiff = delta.landsAfter - delta.landsBefore;
    const landClass = landDiff === 0 ? 'neutral' : landDiff > 0 ? 'info' : 'warning';
    html += `<div class="swap-delta-row">
      <span class="swap-delta-label">Land Count</span>
      <div class="swap-delta-values">
        <span class="swap-delta-detail">${delta.landsBefore} → ${delta.landsAfter}</span>
        <span class="swap-delta-change swap-delta-${landClass}">${landSign}${landDiff}</span>
      </div>
    </div>`;
  }

  // Color balance
  if (Object.keys(delta.colorDelta).length > 0) {
    const colorParts = Object.entries(delta.colorDelta).map(([c, n]) => {
      const sign = n > 0 ? '+' : '';
      return `<span class="swap-color-pip swap-color-${c}">${sign}${n} ${COLOR_NAMES[c] || c}</span>`;
    });
    html += `<div class="swap-delta-row">
      <span class="swap-delta-label">Color Balance</span>
      <div class="swap-delta-values swap-delta-colors">${colorParts.join(' ')}</div>
    </div>`;
  }

  // Type change
  if (delta.typeChanged) {
    html += `<div class="swap-delta-row">
      <span class="swap-delta-label">Card Type</span>
      <div class="swap-delta-values">
        <span class="swap-delta-detail">${escapeHtml(delta.cutType)} → ${escapeHtml(delta.addType)}</span>
      </div>
    </div>`;
  }

  // Game Changer impact
  if (delta.gcCutting || delta.gcAdding) {
    let gcHtml = '';
    if (delta.gcCutting && delta.gcAdding) {
      gcHtml = `<span class="swap-gc-badge swap-gc-neutral">Swapping Game Changers (${delta.gcCountBefore} → ${delta.gcCountAfter})</span>`;
    } else if (delta.gcCutting) {
      gcHtml = `<span class="swap-gc-badge swap-gc-removing">Removing a Game Changer (${delta.gcCountBefore} → ${delta.gcCountAfter})</span>`;
    } else {
      gcHtml = `<span class="swap-gc-badge swap-gc-adding">Adding a Game Changer (${delta.gcCountBefore} → ${delta.gcCountAfter})</span>`;
    }
    html += `<div class="swap-delta-row swap-delta-gc">
      <span class="swap-delta-label">Bracket Impact</span>
      <div class="swap-delta-values">${gcHtml}</div>
    </div>`;
  }

  // Synergy impact
  if (delta.synergiesBroken?.length > 0) {
    html += `<div class="swap-delta-row swap-delta-synergy">
      <span class="swap-delta-label">Synergies Affected</span>
      <div class="swap-delta-values swap-delta-synergy-list">`;
    delta.synergiesBroken.forEach(s => {
      html += `<div class="swap-synergy-item swap-synergy-broken">
        <span class="swap-synergy-icon">&#x26A0;</span>
        <span class="swap-synergy-title">${escapeHtml(s.title)}</span>
        <span class="swap-synergy-cards">${s.cards.map(c => escapeHtml(c)).join(', ')}</span>
      </div>`;
    });
    html += `</div></div>`;
  }

  html += `</div>`;
  return html;
}

// === ANALYTICS / SIMULATION ===
async function loadSimulationData(deckId) {
  if (simulationCache[deckId]) return simulationCache[deckId];
  if (simulationCache[deckId] === null) return null; // cached 404

  try {
    const response = await fetch(`data/commanders/${deckId}/simulation.json`);
    if (!response.ok) {
      simulationCache[deckId] = null;
      return null;
    }
    const data = await response.json();
    simulationCache[deckId] = data;
    return data;
  } catch (err) {
    console.error('Failed to load simulation data:', err);
    simulationCache[deckId] = null;
    return null;
  }
}

async function renderAnalyticsView() {
  const renderVersion = ++analyticsRenderVersion;

  // Reset hand sim on deck change, render it
  handSimState.phase = 'empty';
  handSimState.hand = [];
  handSimState.mulliganCount = 0;
  handSimState.bottomCards = [];
  renderHandSimulator();

  // Reset swap analyzer on deck change
  resetSwapState();
  loadGameChangers();
  renderSwapAnalyzer();

  const contentEl = document.getElementById('analytics-content');
  const noDeckEl = document.getElementById('analytics-no-deck');
  const noDataEl = document.getElementById('analytics-no-data');

  contentEl.style.display = 'none';
  noDeckEl.style.display = 'none';
  noDataEl.style.display = 'none';
  contentEl.innerHTML = '';

  if (!currentDeckId || !currentDeck) {
    noDeckEl.style.display = '';
    return;
  }

  const simData = await loadSimulationData(currentDeckId);

  // Stale-response guard
  if (renderVersion !== analyticsRenderVersion) return;

  if (!simData) {
    noDataEl.style.display = '';
    return;
  }

  let html = '';

  // Header — B design: "Scrying Pool" + green sim badge + deck name right
  const numGames = simData.metadata?.numGames || 0;
  const numTurns = simData.metadata?.numTurns || 10;
  const deckLabel = currentDeck ? `${escapeHtml(currentDeck.name)} — ${escapeHtml(currentDeck.commander)}` : '';
  html += `<div class="analytics-header">
    <h2>Scrying Pool</h2>
    <span class="sim-badge">${numGames.toLocaleString()} simulations</span>
    <span class="deck-name">${deckLabel}</span>
  </div>`;

  // KPI Cards — 3 donut ring cards
  html += renderKpiCards(simData);

  // Mana chart
  html += `<div class="sim-chart-container">
    <div class="sim-chart-panel" id="sim-mana-chart-panel">
      <h3 class="stats-panel-title">Mana Available by Turn</h3>
      <div id="sim-mana-chart"></div>
      <div class="sim-chart-legend">
        <span><span class="legend-band"></span> P25 - P75 range</span>
        <span><span class="legend-line"></span> Median</span>
      </div>
    </div>
  </div>`;

  // Assessment Cards — B design: 3 cards with colored badges
  html += renderAssessmentCards(simData);

  // Detailed panels (metrics + breakdowns)
  html += `<div class="sim-metrics-grid" id="sim-metrics-grid"></div>`;
  html += `<div class="sim-details"><div class="sim-details-grid" id="sim-details-grid"></div></div>`;

  contentEl.innerHTML = html;
  contentEl.style.display = '';

  // Render sub-components
  renderManaRampChart(simData.manaByTurn, numTurns);
  renderSimMetrics(simData);
  renderDetailedBreakdown(simData);
  setupSimAnimations();
}

function renderKpiCards(simData) {
  const circ = 2 * Math.PI * 32;

  // KPI 1: Avg Available Mana T3
  const manaT3 = simData.manaByTurn?.['3']?.median ?? 0;
  const manaT3Pct = Math.min(1, manaT3 / 6);
  const manaT3Offset = circ * (1 - manaT3Pct);

  // KPI 2: Ramp by Turn 3 (% of games with 4+ mana by T3)
  const rampT3 = simData.manaByTurn?.['3'] ? Math.round((simData.manaByTurn['3'].p75 / (simData.manaByTurn['3'].p75 + 1)) * 100) : 0;
  const rampPct = simData.curveEfficiency?.castableByTurn?.['3'] || rampT3;
  const rampOffset = circ * (1 - Math.min(1, rampPct / 100));

  // KPI 3: Commander Timing
  const cmdTurn = simData.commanderTiming?.medianTurn || 0;
  const cmdPct = cmdTurn > 0 ? Math.min(1, 1 - (cmdTurn - 1) / 9) : 0;
  const cmdOffset = circ * (1 - cmdPct);

  return `<div class="sim-kpi-cards">
    <div class="sim-kpi-card">
      <svg class="sim-kpi-ring" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r="32" class="sim-kpi-ring-bg"/>
        <circle cx="40" cy="40" r="32" class="sim-kpi-ring-fill purple" stroke-dasharray="${circ.toFixed(1)}" stroke-dashoffset="${manaT3Offset.toFixed(1)}"/>
      </svg>
      <span class="sim-kpi-value">${manaT3.toFixed(1)}</span>
      <span class="sim-kpi-label">Avg Available Mana T3</span>
    </div>
    <div class="sim-kpi-card">
      <svg class="sim-kpi-ring" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r="32" class="sim-kpi-ring-bg"/>
        <circle cx="40" cy="40" r="32" class="sim-kpi-ring-fill green" stroke-dasharray="${circ.toFixed(1)}" stroke-dashoffset="${rampOffset.toFixed(1)}"/>
      </svg>
      <span class="sim-kpi-value">${Math.round(rampPct)}%</span>
      <span class="sim-kpi-label">Ramp by Turn 3</span>
    </div>
    <div class="sim-kpi-card">
      <svg class="sim-kpi-ring" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r="32" class="sim-kpi-ring-bg"/>
        <circle cx="40" cy="40" r="32" class="sim-kpi-ring-fill amber" stroke-dasharray="${circ.toFixed(1)}" stroke-dashoffset="${cmdOffset.toFixed(1)}"/>
      </svg>
      <span class="sim-kpi-value">T${cmdTurn}</span>
      <span class="sim-kpi-label">Commander Timing</span>
    </div>
  </div>`;
}

function renderAssessmentCards(simData) {
  const a = simData.assessment;
  if (!a) return '';

  function badgeColor(verdict) {
    const v = (verdict || '').toLowerCase();
    if (['strong', 'adequate', 'excellent', 'acceptable', 'on curve', 'ahead of curve'].includes(v)) return 'green';
    if (['light', 'behind curve'].includes(v)) return 'amber';
    if (['concerning', 'unreliable'].includes(v)) return 'red';
    return 'amber';
  }

  function badgeLabel(verdict) {
    if (!verdict) return '';
    return verdict.charAt(0).toUpperCase() + verdict.slice(1);
  }

  let cards = '';

  if (a.manaAdequacy) {
    const desc = a.manaAdequacyDetail || 'Fast mana + consistent color fixing';
    cards += `<div class="sim-assessment-card">
      <span class="assessment-title">Mana Base</span>
      <div class="assessment-row">
        <span class="sim-assessment-badge ${badgeColor(a.manaAdequacy)}">${escapeHtml(badgeLabel(a.manaAdequacy))}</span>
        <span class="assessment-desc">${escapeHtml(desc)}</span>
      </div>
    </div>`;
  }

  if (a.commanderTiming) {
    const cmdCmc = simData.commanderTiming?.cmc || '';
    const cmdTurn = simData.commanderTiming?.medianTurn || '';
    const desc = cmdCmc ? `Castable on T${cmdTurn} (CMC ${cmdCmc})` : '';
    cards += `<div class="sim-assessment-card">
      <span class="assessment-title">Commander Timing</span>
      <div class="assessment-row">
        <span class="sim-assessment-badge ${badgeColor(a.commanderTiming)}">${escapeHtml(badgeLabel(a.commanderTiming))}</span>
        <span class="assessment-desc">${escapeHtml(desc)}</span>
      </div>
    </div>`;
  }

  if (a.mulliganVerdict) {
    const keepRate = simData.mulliganStats?.keptFirst;
    const desc = keepRate != null ? `${keepRate.toFixed(0)}% keep rate` : '';
    cards += `<div class="sim-assessment-card">
      <span class="assessment-title">Ramp Density</span>
      <div class="assessment-row">
        <span class="sim-assessment-badge ${badgeColor(a.mulliganVerdict)}">${escapeHtml(badgeLabel(a.mulliganVerdict))}</span>
        <span class="assessment-desc">${escapeHtml(desc)}</span>
      </div>
    </div>`;
  }

  if (!cards) return '';
  return `<div class="sim-assessment-cards">${cards}</div>`;
}

function renderManaRampChart(manaByTurn, numTurns) {
  const container = document.getElementById('sim-mana-chart');
  if (!container || !manaByTurn) return;

  const turns = [];
  for (let t = 1; t <= numTurns; t++) {
    const data = manaByTurn[String(t)];
    if (data) turns.push({ turn: t, ...data });
  }
  if (turns.length === 0) return;

  const width = 600;
  const height = 250;
  const padL = 45;
  const padR = 15;
  const padT = 15;
  const padB = 35;
  const chartW = width - padL - padR;
  const chartH = height - padT - padB;

  const maxMana = Math.max(...turns.map(t => t.p75)) * 1.15;
  const xScale = (i) => padL + (i / (turns.length - 1)) * chartW;
  const yScale = (v) => padT + chartH - (v / maxMana) * chartH;

  // Build band path (P25 -> P75)
  let bandTop = turns.map((t, i) => `${i === 0 ? 'M' : 'L'}${xScale(i).toFixed(1)},${yScale(t.p75).toFixed(1)}`).join(' ');
  let bandBot = turns.slice().reverse().map((t, i) => `L${xScale(turns.length - 1 - i).toFixed(1)},${yScale(t.p25).toFixed(1)}`).join(' ');
  let bandPath = `${bandTop} ${bandBot} Z`;

  // Median line
  let medianPath = turns.map((t, i) => `${i === 0 ? 'M' : 'L'}${xScale(i).toFixed(1)},${yScale(t.median).toFixed(1)}`).join(' ');

  // Grid lines
  let gridLines = '';
  const gridSteps = Math.ceil(maxMana);
  for (let g = 0; g <= gridSteps; g += 3) {
    const y = yScale(g);
    if (y >= padT && y <= padT + chartH) {
      gridLines += `<line x1="${padL}" y1="${y.toFixed(1)}" x2="${padL + chartW}" y2="${y.toFixed(1)}" class="sim-chart-grid"/>`;
      gridLines += `<text x="${padL - 8}" y="${(y + 4).toFixed(1)}" class="sim-chart-axis-label" text-anchor="end">${g}</text>`;
    }
  }

  // X axis labels
  let xLabels = turns.map((t, i) => `<text x="${xScale(i).toFixed(1)}" y="${(padT + chartH + 20).toFixed(1)}" class="sim-chart-axis-label" text-anchor="middle">T${t.turn}</text>`).join('');

  // Dots for hover
  let dots = turns.map((t, i) => `<circle cx="${xScale(i).toFixed(1)}" cy="${yScale(t.median).toFixed(1)}" r="4" class="sim-chart-dot" data-turn="${t.turn}" data-median="${t.median}" data-p25="${t.p25}" data-p75="${t.p75}" data-mean="${t.mean}"/>`).join('');

  container.innerHTML = `<div style="position:relative;">
    <svg class="sim-chart-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet">
      ${gridLines}
      <path d="${bandPath}" class="sim-chart-band"/>
      <path d="${medianPath}" class="sim-chart-median"/>
      ${xLabels}
      ${dots}
    </svg>
    <div class="sim-chart-tooltip" id="sim-chart-tooltip" style="display:none;"></div>
  </div>`;

  // Tooltip events
  const tooltip = document.getElementById('sim-chart-tooltip');
  const svg = container.querySelector('svg');
  container.querySelectorAll('.sim-chart-dot').forEach(dot => {
    dot.addEventListener('mouseenter', (e) => {
      const turn = dot.dataset.turn;
      const median = parseFloat(dot.dataset.median).toFixed(1);
      const p25 = parseFloat(dot.dataset.p25).toFixed(1);
      const p75 = parseFloat(dot.dataset.p75).toFixed(1);
      const mean = parseFloat(dot.dataset.mean).toFixed(1);
      tooltip.innerHTML = `<span class="tt-turn">Turn ${turn}</span><br>Median: ${median}<br>P25-P75: ${p25} - ${p75}<br>Mean: ${mean}`;
      tooltip.style.display = '';
      const rect = svg.getBoundingClientRect();
      const dotRect = dot.getBoundingClientRect();
      tooltip.style.left = (dotRect.left - rect.left + dotRect.width / 2) + 'px';
      tooltip.style.top = (dotRect.top - rect.top - tooltip.offsetHeight - 8) + 'px';
    });
    dot.addEventListener('mouseleave', () => {
      tooltip.style.display = 'none';
    });
  });
}

function renderSimMetrics(simData) {
  const grid = document.getElementById('sim-metrics-grid');
  if (!grid) return;

  let html = '';

  // Commander timing ring
  if (simData.commanderTiming) {
    const ct = simData.commanderTiming;
    const medTurn = ct.medianTurn || 0;
    const maxTurn = 10;
    const pct = Math.min(1, 1 - (medTurn - 1) / (maxTurn - 1));
    const circ = 2 * Math.PI * 35;
    const offset = circ * (1 - pct);
    html += `<div class="sim-metric-card">
      <div class="metric-label">Commander Timing</div>
      <div class="metric-ring">
        <svg viewBox="0 0 80 80" class="sim-chart-svg">
          <circle cx="40" cy="40" r="35" class="sim-metric-ring-bg"/>
          <circle cx="40" cy="40" r="35" class="sim-metric-ring-fill" stroke-dasharray="${circ.toFixed(1)}" stroke-dashoffset="${offset.toFixed(1)}"/>
          <text x="40" y="40" class="sim-metric-ring-text">T${medTurn}</text>
        </svg>
      </div>
      <div class="metric-sub">${escapeHtml(ct.name)} (${ct.cmc} CMC)</div>
    </div>`;
  }

  // Mulligan donut
  if (simData.mulliganStats) {
    const ms = simData.mulliganStats;
    const kept = ms.keptFirst || 0;
    const circ = 2 * Math.PI * 35;
    const offset = circ * (1 - kept / 100);
    html += `<div class="sim-metric-card">
      <div class="metric-label">Keep Rate</div>
      <div class="metric-ring">
        <svg viewBox="0 0 80 80" class="sim-chart-svg">
          <circle cx="40" cy="40" r="35" class="sim-metric-ring-bg"/>
          <circle cx="40" cy="40" r="35" class="sim-metric-ring-fill" style="stroke: var(--accent-green);" stroke-dasharray="${circ.toFixed(1)}" stroke-dashoffset="${offset.toFixed(1)}"/>
          <text x="40" y="40" class="sim-metric-ring-text">${kept.toFixed(0)}%</text>
        </svg>
      </div>
      <div class="metric-sub">Free mull: ${(ms.freeMulligan || 0).toFixed(1)}% | Paid: ${(ms.paidMulligan || 0).toFixed(1)}%</div>
    </div>`;
  }

  // Curve-out rate
  if (simData.curveEfficiency) {
    const rate = simData.curveEfficiency.curveOutRate || 0;
    html += `<div class="sim-metric-card">
      <div class="metric-label">Curve-Out Rate</div>
      <div class="metric-value" data-target="${rate.toFixed(1)}">${rate.toFixed(1)}%</div>
      <div class="metric-sub">Cast a spell every turn T1-T4</div>
    </div>`;
  }

  // Deck composition
  if (simData.deckComposition) {
    const dc = simData.deckComposition;
    html += `<div class="sim-metric-card">
      <div class="metric-label">Avg Mana Value</div>
      <div class="metric-value">${(dc.avgCmc || 0).toFixed(2)}</div>
      <div class="metric-sub">${dc.lands} lands | ${dc.rocks} rocks | ${dc.spells} spells</div>
    </div>`;
  }

  // Color balance (only shown when not null)
  if (simData.colorBalance) {
    const cb = simData.colorBalance;
    const colors = cb.colors || [];
    const colorLabels = { W: 'White', U: 'Blue', B: 'Black', R: 'Red', G: 'Green' };
    const t4Data = cb.byTurn?.['4'] || {};
    html += `<div class="sim-metric-card">
      <div class="metric-label">Color Mana (T4 Median)</div>
      <div style="display:flex;gap:12px;justify-content:center;margin-top:8px;">`;
    colors.forEach(c => {
      const median = t4Data[c]?.median ?? 0;
      html += `<div style="text-align:center;"><div style="font-size:1.2rem;font-weight:700;font-family:'Fira Code',monospace;">${median}</div><div class="metric-sub">${colorLabels[c] || c}</div></div>`;
    });
    html += `</div></div>`;
  }

  grid.innerHTML = html;
}

function renderDetailedBreakdown(simData) {
  const grid = document.getElementById('sim-details-grid');
  if (!grid) return;

  let html = '';

  // Opening hand land distribution
  if (simData.openingHand?.landDistribution) {
    const dist = simData.openingHand.landDistribution;
    html += `<div class="sim-detail-panel"><h4>Opening Hand Lands</h4>`;
    for (let i = 0; i <= 7; i++) {
      const pct = dist[String(i)] || 0;
      const barColor = (i >= 2 && i <= 4) ? 'green' : (i === 1 || i === 5) ? 'gold' : 'red';
      html += `<div class="sim-bar-row">
        <span class="sim-bar-label">${i} lands</span>
        <div class="sim-bar-track"><div class="sim-bar-fill ${barColor}" style="width:${Math.min(pct, 100)}%"></div></div>
        <span class="sim-bar-pct">${pct.toFixed(1)}%</span>
      </div>`;
    }
    html += `</div>`;
  }

  // Commander by-turn %
  if (simData.commanderTiming?.byTurn) {
    const bt = simData.commanderTiming.byTurn;
    html += `<div class="sim-detail-panel"><h4>Commander Castable by Turn</h4>`;
    const turnKeys = Object.keys(bt).sort((a, b) => Number(a) - Number(b));
    turnKeys.forEach(t => {
      const pct = bt[t] || 0;
      html += `<div class="sim-bar-row">
        <span class="sim-bar-label">T${t}</span>
        <div class="sim-bar-track"><div class="sim-bar-fill" style="width:${Math.min(pct, 100)}%"></div></div>
        <span class="sim-bar-pct">${pct.toFixed(1)}%</span>
      </div>`;
    });
    html += `</div>`;
  }

  // Castable-by-turn %
  if (simData.curveEfficiency?.castableByTurn) {
    const cbt = simData.curveEfficiency.castableByTurn;
    html += `<div class="sim-detail-panel"><h4>Any Spell Castable by Turn</h4>`;
    const turnKeys = Object.keys(cbt).sort((a, b) => Number(a) - Number(b));
    turnKeys.forEach(t => {
      const pct = cbt[t] || 0;
      html += `<div class="sim-bar-row">
        <span class="sim-bar-label">T${t}</span>
        <div class="sim-bar-track"><div class="sim-bar-fill blue" style="width:${Math.min(pct, 100)}%"></div></div>
        <span class="sim-bar-pct">${pct.toFixed(1)}%</span>
      </div>`;
    });
    html += `</div>`;
  }

  // Color screw by turn (if multicolor)
  if (simData.colorBalance?.colorScrewByTurn) {
    const csbt = simData.colorBalance.colorScrewByTurn;
    const colors = simData.colorBalance.colors || [];
    const colorLabels = { W: 'White', U: 'Blue', B: 'Black', R: 'Red', G: 'Green' };
    colors.forEach(color => {
      html += `<div class="sim-detail-panel"><h4>${colorLabels[color] || color} Screw Rate by Turn</h4>`;
      const turnKeys = Object.keys(csbt).sort((a, b) => Number(a) - Number(b));
      turnKeys.forEach(t => {
        const pct = csbt[t]?.[color] || 0;
        html += `<div class="sim-bar-row">
          <span class="sim-bar-label">T${t}</span>
          <div class="sim-bar-track"><div class="sim-bar-fill red" style="width:${Math.min(pct, 100)}%"></div></div>
          <span class="sim-bar-pct">${pct.toFixed(1)}%</span>
        </div>`;
      });
      html += `</div>`;
    });
  }

  // Special metrics panels
  if (simData.specialMetrics) {
    if (simData.specialMetrics.cascadeReadiness?.byTurn) {
      const crByTurn = simData.specialMetrics.cascadeReadiness.byTurn;
      const medTurn = simData.specialMetrics.cascadeReadiness.medianTurn;
      html += `<div class="sim-detail-panel"><h4>Cascade Readiness${medTurn != null ? ` (median T${medTurn})` : ''}</h4>`;
      const turnKeys = Object.keys(crByTurn).sort((a, b) => Number(a) - Number(b));
      turnKeys.forEach(t => {
        const pct = crByTurn[t] || 0;
        html += `<div class="sim-bar-row">
          <span class="sim-bar-label">T${t}</span>
          <div class="sim-bar-track"><div class="sim-bar-fill gold" style="width:${Math.min(pct, 100)}%"></div></div>
          <span class="sim-bar-pct">${pct.toFixed(1)}%</span>
        </div>`;
      });
      html += `</div>`;
    }

    if (simData.specialMetrics.etbTapped) {
      const etb = simData.specialMetrics.etbTapped;
      html += `<div class="sim-detail-panel"><h4>ETB Tapped Land Rate by Turn</h4>`;
      const turnKeys = Object.keys(etb).sort((a, b) => Number(a) - Number(b));
      turnKeys.forEach(t => {
        const pct = etb[t] || 0;
        html += `<div class="sim-bar-row">
          <span class="sim-bar-label">T${t}</span>
          <div class="sim-bar-track"><div class="sim-bar-fill gold" style="width:${Math.min(pct, 100)}%"></div></div>
          <span class="sim-bar-pct">${pct.toFixed(1)}%</span>
        </div>`;
      });
      html += `</div>`;
    }
  }

  grid.innerHTML = html;
}

function setupSimAnimations() {
  if (!('IntersectionObserver' in window)) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.querySelectorAll('.sim-bar-fill').forEach(bar => {
          const width = bar.style.width;
          bar.style.width = '0%';
          requestAnimationFrame(() => {
            requestAnimationFrame(() => { bar.style.width = width; });
          });
        });
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll('.sim-detail-panel').forEach(panel => {
    observer.observe(panel);
  });
}

function updateTabStates() {
  const analyticsTab = document.getElementById('tab-analytics');
  if (analyticsTab) {
    analyticsTab.classList.toggle('disabled', !currentDeck);
  }
}

// === INITIALIZE ===
async function initializeApp() {
  // Update search hint for non-Mac platforms
  if (!/Mac|iPhone|iPad/.test(navigator.userAgent)) {
    const hint = document.getElementById('search-hint');
    if (hint) hint.innerHTML = '<kbd>Ctrl</kbd><kbd>K</kbd> Search';
  }

  // Subtle parallax on commander background art
  document.addEventListener('mousemove', throttle((e) => {
    const bg = document.getElementById('commander-bg');
    if (!bg) return;
    const x = (e.clientX / window.innerWidth - 0.5) * 2;
    const y = (e.clientY / window.innerHeight - 0.5) * 2;
    bg.style.transform = `translate(${x * -8}px, ${y * -8}px)`;
  }, 50));

  // Pre-load local card metadata (avoids Scryfall API calls for known cards)
  await loadLocalMetadata();

  // Set up delegated event listeners (once, before any content loads)
  setupDelegatedListeners();

  // Sticky nav — collapse header into compact bar when scrolled past
  const stickyNav = document.getElementById('sticky-nav');
  const headerEl = document.querySelector('header');
  if (stickyNav && headerEl) {
    const headerObserver = new IntersectionObserver(([entry]) => {
      stickyNav.classList.toggle('stuck', !entry.isIntersecting);
    }, { threshold: 0 });
    headerObserver.observe(headerEl);
  }

  // Tier sources toggle
  document.getElementById('tier-sources-toggle')?.addEventListener('click', () => {
    const section = document.getElementById('tier-sources-section');
    const toggle = document.getElementById('tier-sources-toggle');
    const expanded = section.classList.toggle('expanded');
    toggle.setAttribute('aria-expanded', String(expanded));
  });

  // Initialize view toggle
  initViewToggle();

  // Load preferences first
  const prefs = loadPreferences();
  const urlParams = parseUrlHash();

  // Load deck index
  await loadDeckIndex();

  // Determine which deck to load
  const deckToLoad = urlParams.deck || prefs?.lastDeck;
  const requestedView = urlParams.view;

  // Check if a non-guide view requested
  if (requestedView === 'shopping') {
    // Shopping view doesn't require a specific deck
    switchView('shopping');
    // Still load a deck if one was specified, for other tabs
    if (deckToLoad) {
      const allDecks = [...(deckIndex.commanders || [])];
      if (allDecks.some(d => d.id === deckToLoad)) {
        deckSelect.value = deckToLoad;
        await selectDeck(deckToLoad);
      }
    }
    return;
  }
  if (requestedView === 'analytics') {
    const viewDeck = urlParams.deck || deckToLoad;
    const allDecks = [...(deckIndex.commanders || [])];
    if (viewDeck && allDecks.some(d => d.id === viewDeck)) {
      deckSelect.value = viewDeck;
      await selectDeck(viewDeck);
      switchView(requestedView);
    }
    return;
  }

  // If we have a deck to load from URL or preferences
  const allDecks = [...(deckIndex.commanders || [])];
  if (deckToLoad && allDecks.some(d => d.id === deckToLoad)) {
    deckSelect.value = deckToLoad;
    await selectDeck(deckToLoad);
    updateUrlHash();
  }

  // Load filter preferences
  if (prefs?.filters) {
    filterState = { ...filterState, ...prefs.filters };
    document.getElementById('filter-cmc').value = filterState.cmc;
    document.getElementById('filter-sort').value = filterState.sort;

    document.querySelectorAll('.filter-chip').forEach(chip => {
      chip.classList.toggle('active', chip.dataset.type === filterState.type);
      chip.setAttribute('aria-pressed', chip.dataset.type === filterState.type);
    });
  }
}

initializeApp();
