// Grimoire v1 — Decklist + Mobile artboard

function GV1Decklist({ list }) {
  const total = list.reduce((n, g) => n + g.cards.length, 0);
  return (
    <section className="gv1-section gv1-decklist">
      <div className="gv1-section-head">
        <span className="gv1-rune" aria-hidden="true">§ VII</span>
        <h2 className="gv1-section-title">The Manifest</h2>
        <span className="gv1-mono-xs gv1-dim">· {total} cards · {list.length} roles · sorted by function</span>
      </div>
      <div className="gv1-decklist-cols">
        {list.map((grp, i) => (
          <div key={i} className="gv1-dl-group">
            <div className="gv1-dl-group-head">
              <span className="gv1-serif-sm">{grp.name}</span>
              <span className="gv1-mono-xs gv1-dim">{grp.cards.length}</span>
            </div>
            <ul className="gv1-dl-list">
              {grp.cards.map((c, j) => (
                <li key={j} className={'gv1-dl-row' + (c.gc ? ' gv1-dl-gc' : '')} data-card-name={c.n}>
                  <span className="gv1-dl-name">
                    {c.gc && <span className="gv1-dl-star">★</span>}
                    {c.n}
                  </span>
                  <span className="gv1-dl-mv"><ManaCost mv={c.mv} /></span>
                  <span className="gv1-dl-price gv1-mono-xs gv1-rune">{c.price}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}

function GV1Mobile({ deck }) {
  if (!deck) {
    return <div className="gv1-mobile"><div className="gv1-empty">No deck.</div></div>;
  }
  const wincon = (deck.wincons && deck.wincons[0]) || null;
  const curve = (deck.curve && deck.curve.length) ? deck.curve : null;
  const maxN = curve ? Math.max(1, ...curve.map(c => c.n)) : 1;
  return (
    <div className="gv1-mobile">
      <div className="gv1-mobile-status">
        <span className="gv1-mono-xs">9:41</span>
        <span className="gv1-mono-xs gv1-rune">◈ grimoire</span>
        <span className="gv1-mono-xs" aria-hidden="true">◉ ◉ ◉</span>
      </div>
      <div className="gv1-mobile-head">
        <div className="gv1-mono-xs gv1-dim">№ {String(deck.idx).padStart(2,'0')} · BRACKET {deck.bracket}</div>
        <h1 className="gv1-serif-xl">
          {deck.deckName.includes(' ')
            ? <><span>{deck.deckName.split(' ').slice(0,-1).join(' ')} </span><em>{deck.deckName.split(' ').slice(-1)[0]}</em></>
            : <em>{deck.deckName}</em>}
        </h1>
        <div className="gv1-mono-xs gv1-rune" data-card-name={deck.commander}>{deck.commander} · ◇</div>
        <div className="gv1-mobile-tabs">
          <button className="gv1-active">Engine</button>
          <button>Wins</button>
          <button>Combos</button>
          <button>List</button>
        </div>
      </div>
      <div className="gv1-mobile-body">
        {wincon && (
          <div className="gv1-mobile-block">
            <div className="gv1-mono-xs gv1-dim">WIN · 01 / {String(deck.wincons.length).padStart(2,'0')}</div>
            <h3 className="gv1-serif-md">
              <span>{wincon.title[0]}</span><em>{wincon.title[1]}</em>
            </h3>
            <p className="gv1-wincon-desc gv1-mobile-desc">{wincon.desc}</p>
            {wincon.prob && (
              <div className="gv1-mobile-prob">
                <span className="gv1-mono-xs gv1-dim">EARLIEST WIN</span>
                <span className="gv1-serif-lg gv1-rune">{wincon.prob}</span>
              </div>
            )}
          </div>
        )}
        {wincon && wincon.cards && wincon.cards.length > 0 && (
          <div className="gv1-mobile-block">
            <div className="gv1-mono-xs gv1-dim">KEY CARDS</div>
            <div className="gv1-mobile-cards">
              {wincon.cards.slice(0,2).map((c, i) => <CardTile key={i} card={c} size="sm" />)}
            </div>
          </div>
        )}
        {curve && (
          <div className="gv1-mobile-block gv1-mobile-curve-block">
            <div className="gv1-mono-xs gv1-dim">ROLE DISTRIBUTION</div>
            <div className="gv1-curve gv1-curve-sm">
              {curve.map((c, i) => (
                <div key={i} className={'gv1-curve-col' + (c.peak ? ' gv1-peak' : '')}>
                  <div className="gv1-curve-bar-wrap">
                    <div className="gv1-curve-bar" style={{height: (c.n/maxN*100)+'%'}}/>
                  </div>
                  <div className="gv1-curve-l gv1-mono-xs gv1-dim">{c.cmc}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
      <div className="gv1-mobile-nav">
        <span className="gv1-rune" aria-hidden="true">◈</span>
        <span className="gv1-mono-xs">shelf</span>
        <span className="gv1-mono-xs"><span aria-hidden="true">⦿ </span>scry</span>
        <span className="gv1-mono-xs gv1-dim"><span aria-hidden="true">▦ </span>list</span>
        <span className="gv1-mono-xs gv1-dim" aria-label="Settings">⚙</span>
      </div>
    </div>
  );
}

Object.assign(window, { GV1Decklist, GV1Mobile });
