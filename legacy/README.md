# Legacy Grimoire (pre-DEC-149)

The original vanilla-JS app. Frozen and archived as part of DEC-149 Phase 6
big-bang cutover (2026-05-05). Kept here for one release as a rollback safety
net; will be deleted in a follow-up release.

- `index.html` — single-page shell
- `app.js` — all view logic (~6.3k lines, no build step)
- `styles.css` — global stylesheet (~5.9k lines)

The new app lives in [`web/`](../web) (Vite + React + TS, see
[`DEC-149-plan.md`](../DEC-149-plan.md)). Deck data in `data/commanders/{id}/`
is shared by both apps and remains canonical.

Do not edit. If you need to revive any of this, restore from git history
rather than reanimating the archive in place.
