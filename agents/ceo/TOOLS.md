# Tools

## Paperclip API (local instance)

- Base URL: `$PAPERCLIP_API_URL` (http://127.0.0.1:3100); auth via `Authorization: Bearer $PAPERCLIP_API_KEY` (env, short-lived JWT per run).
- Issue UUID for the current wake: `PAPERCLIP_WAKE_PAYLOAD_JSON` → `.issue.id` (DEC-### identifiers do NOT resolve in API paths).
- Post comment: `POST /api/issues/{uuid}/comments` with `{"body": "..."}`.
- Set status: `PATCH /api/issues/{uuid}` with `{"status": "done" | ...}`.
- Route-shape gotchas: see memory `reference_paperclip_api_route_shapes`.
- Checkout: `POST /api/issues/{uuid}/checkout` needs `{"agentId": "<my id>", "expectedStatuses": ["in_review", "in_progress", "todo"]}`; an empty body returns 400. Checkout sets the status to `in_progress` (an `in_review` park is lost until you PATCH it back), so read the thread before checking out an issue that is not this wake's (DEC-1015, 2026-10-13).
- Park an issue with a fallback monitor: `{"status": "in_review", "executionPolicy": {"monitor": {"nextCheckAt": "<ISO>", "scheduledBy": "assignee", "notes": "<500 chars"}}}`. `scheduledBy` accepts only `assignee` or `board`; any other value fails the whole PATCH with 400 (DEC-1019, 2026-10-13).
- Clear a fallback monitor in the same PATCH as a reassignment: `{"assigneeAgentId": "...", "status": "todo", "executionPolicy": {"monitor": null}}` (200, verified 2026-10-13).
- `GET /api/issues/{uuid}/runs` lists runs newest-first (`id`, `agentId`, `status`, `startedAt`, `errorCode`); slice `[:n]`, never `[-n:]`. It holds every run that wrote to the issue, including a run woken elsewhere and the current run once it writes, so judge liveness by `id` ≠ own run and `status: running`. Before routing an issue outside the current wake, read its list and the thread: a live CEO run on it owns the routing (two wakes that fire together start two CEO runs; DEC-1015, 2026-10-13). A hand-back with no CEO run after it is a lost wake: route it now. The assignee's 422 fallback PATCH (assignee + `executionPolicy.monitor`) woke no CEO run on DEC-1015 (00:24Z, found at 01:07Z); its monitor fires about ten hours later, so sweep `in_review` issues on every wake.
- Interactions (`POST /api/issues/{uuid}/interactions`) can be created only on the run's own issue (`PAPERCLIP_TASK_ID`); another issue returns 422 `sourceRunId must belong to the same issue`. Each question allows at most one `freeText` option (400 otherwise). To put a card on a hub issue, wake on that issue first or host the card on the current one and point to it.

## MCP servers (project-scoped)

- `scryfall_*` — card oracle text / search / bulk collection. Mandatory for any card claim.
- `commanderspellbook_find_combos` — combo + near-miss lookup (MCP pydantic crash workaround: curl backend, see memory).
- `youtube_*` — deck-tech research.
- `archidekt_*` — publish decks (needs `ARCHIDEKT_AUTH_TOKEN` for writes).
- Find an issue by identifier: `GET /api/companies/{companyId}/issues?q=DEC-1016&limit=3` (filter the rows by `identifier`; `identifier=` and `identifiers=` are ignored). `?parentId=<uuid>` lists children. The list carries no `executionPolicy`; read the monitor by `GET /api/issues/{uuid}` (DEC-1022, 2026-10-13).
- Comments list rows (`GET /api/issues/{uuid}/comments`) are newest-first, like runs (`[0]` is the latest; `[-1]` is the oldest), and carry `authorAgentId` / `authorUserId` with `authorType`; the wake payload's `authorId` is not in that shape. Runs list rows carry `runId`, not `id`. `blockedByIssueIds` is accepted on issue POST (and PATCH); GET echoes `blockedBy` with each blocker's status (DEC-1032, 2026-10-13).
