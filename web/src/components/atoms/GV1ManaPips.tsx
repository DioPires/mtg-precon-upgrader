import { colorWords } from './colorWords';

interface PipConfig {
  fill: string;
  stroke: string;
  letter: 'W' | 'U' | 'B' | 'R' | 'G' | 'C';
}

const COLOR_MAP: Record<string, PipConfig> = {
  '⚪': { fill: '#f5efd8', stroke: '#d4cea8', letter: 'W' },
  '🔵': { fill: '#a8c8e8', stroke: '#6a98c0', letter: 'U' },
  '⚫': { fill: '#3a3028', stroke: '#1a1410', letter: 'B' },
  '🔴': { fill: '#e8a898', stroke: '#c06848', letter: 'R' },
  '🟢': { fill: '#98c8a8', stroke: '#487a58', letter: 'G' },
  '◇': { fill: '#b8b0a0', stroke: '#807868', letter: 'C' },
};

interface GV1ManaPipsProps {
  colors?: string;
}

export function GV1ManaPips({ colors }: GV1ManaPipsProps) {
  const chars = Array.from(colors || '');
  return (
    <span className="gv1-pips" role="img" aria-label={`Color identity: ${colorWords(colors || '')}`}>
      {chars.map((c, i) => {
        const cfg = COLOR_MAP[c] || COLOR_MAP['◇'];
        return (
          <span
            key={i}
            className="gv1-pip"
            aria-hidden="true"
            style={{
              background: cfg.fill,
              borderColor: cfg.stroke,
              color: cfg.letter === 'B' ? '#d8d0c0' : '#1a1410',
            }}
          >
            {cfg.letter}
          </span>
        );
      })}
    </span>
  );
}
