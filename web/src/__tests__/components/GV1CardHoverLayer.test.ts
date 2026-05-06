import { describe, expect, it } from 'vitest';
import {
  computeHoverPosition,
  HOVER_GAP,
  POPOVER_H,
  POPOVER_W,
} from '../../components/global/GV1CardHoverLayer';

const VW = 1440;
const VH = 900;

function rectAt(left: number, top = 200, width = 220) {
  return { left, top, right: left + width };
}

describe('computeHoverPosition', () => {
  it('renders to the right for a card mid-screen (fits right preserved)', () => {
    const rect = rectAt(600);
    const { side, x } = computeHoverPosition({ rect, vw: VW, vh: VH });
    expect(side).toBe('right');
    expect(x).toBe(rect.right + HOVER_GAP);
  });

  it('flips to the left when the card sits near the right edge', () => {
    const rect = rectAt(VW - 240); // right ≈ 1420, no room on right
    const { side, x } = computeHoverPosition({ rect, vw: VW, vh: VH });
    expect(side).toBe('left');
    // x is the popover's right anchor; popover-left = x - POPOVER_W
    expect(x - POPOVER_W).toBeGreaterThanOrEqual(0);
  });

  it('keeps right side and clamps x for a card near the left edge (DEC-179)', () => {
    // Pre-fix bug: side flipped to 'left' and x = rect.left - 12 → clipped.
    const rect = rectAt(20);
    const { side, x } = computeHoverPosition({ rect, vw: VW, vh: VH });
    expect(side).toBe('right');
    // popover-right = x + POPOVER_W must stay inside vw
    expect(x + POPOVER_W).toBeLessThanOrEqual(VW);
    // popover-left stays >= 0
    expect(x).toBeGreaterThanOrEqual(0);
  });

  it('picks the side with more room when neither side fits (narrow viewport)', () => {
    // When vw < POPOVER_W the popover can't fully fit on either side; the
    // spec's tiebreak is "pick the side with more room."
    const narrowVw = POPOVER_W; // 396 — neither side fits
    const rect = rectAt(50, 100, 100);
    const { side, y } = computeHoverPosition({ rect, vw: narrowVw, vh: VH });
    // Right of card (vw - rect.right = 246) > left of card (50).
    expect(side).toBe('right');
    expect(y).toBeGreaterThanOrEqual(HOVER_GAP);
  });

  it('clamps y so the popover never overflows the bottom of the viewport', () => {
    const rect = rectAt(600, VH - 50);
    const { y } = computeHoverPosition({ rect, vw: VW, vh: VH });
    expect(y).toBeLessThanOrEqual(VH - POPOVER_H - HOVER_GAP);
    expect(y).toBeGreaterThanOrEqual(HOVER_GAP);
  });

  it('clamps y to GAP when the card is at the top of the viewport', () => {
    const rect = rectAt(600, -100); // negative top (scrolled past)
    const { y } = computeHoverPosition({ rect, vw: VW, vh: VH });
    expect(y).toBe(HOVER_GAP);
  });

  it('flips to left when right does not fit but left does', () => {
    // Card near right edge with plenty of room on the left.
    const rect = rectAt(VW - 250, 200, 200);
    const { side } = computeHoverPosition({ rect, vw: VW, vh: VH });
    expect(side).toBe('left');
  });
});
