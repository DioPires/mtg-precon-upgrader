interface ManaCostProps {
  mv?: string;
}

export function ManaCost({ mv }: ManaCostProps) {
  if (!mv || mv === 'LAND' || mv === '—') {
    return <span className="gv1-mv gv1-mv-land">{mv || '—'}</span>;
  }
  const parts = mv.match(/\{[^}]+\}/g) || [];
  return (
    <span className="gv1-mv">
      {parts.map((p, i) => {
        const sym = p.slice(1, -1);
        const isColorless = sym === 'C';
        const isNumeric = /^\d+$/.test(sym);
        const klass = isColorless ? 'gv1-mv-c' : isNumeric ? 'gv1-mv-n' : 'gv1-mv-g';
        return (
          <span key={i} className={`gv1-mv-pip ${klass}`}>
            {sym}
          </span>
        );
      })}
    </span>
  );
}
