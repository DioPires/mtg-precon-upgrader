const LOCAL_CARD_IMAGE_BASE = '/data/images/cards';

export function sanitizeCardName(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

export function localCardImageUrl(name: string, variant: 'normal' | 'art_crop' = 'normal'): string {
  return `${LOCAL_CARD_IMAGE_BASE}/${sanitizeCardName(name)}-${variant}.jpg`;
}
