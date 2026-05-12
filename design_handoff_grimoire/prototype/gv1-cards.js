// Grimoire v1 — Shared Scryfall card cache
// Lazy-loads { image_small, image_normal, mana_cost, type_line, prices.usd }
// per card name. Designed to be replaced by a build-time prefetch in production.
//
// API:
//   GV1Cards.get(name) → cached entry or null
//   GV1Cards.fetch(name) → Promise<entry>  (deduped)
//   GV1Cards.subscribe(name, fn) → unsubscribe; fn called when entry updates
//
// Entry shape:
//   { status: 'loading' | 'loaded' | 'error',
//     name, mana_cost, cmc, type_line, image_small, image_normal, art_crop, price }

(function () {
  const cache = new Map(); // name.toLowerCase() → entry
  const subs = new Map();  // name.toLowerCase() → Set<fn>
  const inflight = new Map(); // name.toLowerCase() → Promise

  function notify(key) {
    const set = subs.get(key);
    if (!set) return;
    const entry = cache.get(key);
    set.forEach(fn => { try { fn(entry); } catch(e){} });
  }

  function get(name) {
    if (!name) return null;
    return cache.get(name.toLowerCase()) || null;
  }

  function subscribe(name, fn) {
    if (!name) return () => {};
    const key = name.toLowerCase();
    let set = subs.get(key);
    if (!set) { set = new Set(); subs.set(key, set); }
    set.add(fn);
    return () => set.delete(fn);
  }

  async function fetchOne(name) {
    if (!name) return null;
    const key = name.toLowerCase();
    if (cache.has(key) && cache.get(key).status !== 'error') return cache.get(key);
    if (inflight.has(key)) return inflight.get(key);

    cache.set(key, { status: 'loading', name });
    notify(key);

    const url = `https://api.scryfall.com/cards/named?fuzzy=${encodeURIComponent(name)}`;
    const p = fetch(url).then(r => {
      if (!r.ok) throw new Error('scryfall ' + r.status);
      return r.json();
    }).then(data => {
      // Some cards have card_faces (DFC, split). Use front face for image.
      const face = (data.card_faces && data.card_faces[0]) || data;
      const imgs = data.image_uris || face.image_uris || {};
      const entry = {
        status: 'loaded',
        name: data.name,
        mana_cost: face.mana_cost || data.mana_cost || '',
        cmc: data.cmc,
        type_line: data.type_line || face.type_line || '',
        image_small: imgs.small || '',
        image_normal: imgs.normal || '',
        art_crop: imgs.art_crop || '',
        price: data.prices?.usd ? `$${parseFloat(data.prices.usd).toFixed(2)}` : null,
      };
      cache.set(key, entry);
      notify(key);
      return entry;
    }).catch(err => {
      const entry = { status: 'error', name, error: err.message };
      cache.set(key, entry);
      notify(key);
      return entry;
    }).finally(() => {
      inflight.delete(key);
    });
    inflight.set(key, p);
    return p;
  }

  // Throttled queue: respect Scryfall ≥50ms request interval (we use 80ms)
  const queue = [];
  let pumping = false;
  function pump() {
    if (pumping) return;
    pumping = true;
    (async function tick() {
      while (queue.length) {
        const name = queue.shift();
        await fetchOne(name);
        await new Promise(r => setTimeout(r, 80));
      }
      pumping = false;
    })();
  }
  function enqueue(name) {
    if (!name) return;
    const key = name.toLowerCase();
    if (cache.has(key)) return; // already loaded/loading
    if (queue.includes(name)) return;
    queue.push(name);
    pump();
  }

  window.GV1Cards = { get, subscribe, fetch: fetchOne, enqueue };
})();
