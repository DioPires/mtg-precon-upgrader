# YouTube Data Fetching for MTG Precon Upgrader

This document describes the YouTube video analysis capability that allows Claude to research MTG content creator videos when building upgrade guides.

## Overview

When creating or updating deck upgrade guides, Claude can now:
1. Search curated YouTube channels for relevant videos about a commander/precon
2. Fetch and analyze video transcripts
3. Extract card recommendations with reasoning from content creators
4. Incorporate findings into upgrade recommendations

**Key Design**: Claude does the card extraction natively - the MCP server only provides YouTube data access. No external LLM costs.

## Architecture

```
┌─────────────────────┐
│  User asks Claude   │
│  to research deck   │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐     ┌──────────────────────────┐
│      Claude         │────▶│  YouTube MCP Server      │
│  (analyzes content, │     │  (Python + FastMCP 3.0)  │
│   extracts cards)   │◀────│                          │
└─────────────────────┘     │  Tools:                  │
          │                 │  - search_youtube_videos │
          ▼                 │  - get_video_transcript  │
┌─────────────────────┐     │  - get_video_metadata    │
│  Claude incorporates│     └──────────────────────────┘
│  findings into      │              │
│  deck.json          │              ▼
└─────────────────────┘     ┌──────────────────────────┐
                            │  yt-dlp (backend)        │
                            │  No API quotas           │
                            └──────────────────────────┘
```

## Available Tools

### 1. `search_youtube_videos`

Search YouTube for videos matching a query, optionally filtered to specific channels.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | required | Search terms (commander name, precon, strategy) |
| `channel_handles` | list[str] | null | Optional channel handles to filter (e.g., `["@commandzone"]`) |
| `max_results` | int | 10 | Maximum videos to return |
| `years_back` | int | 5 | How far back to search |

**Returns:**
```json
[
  {
    "video_id": "abc123xyz",
    "title": "Eldrazi Unbound Upgrade Guide",
    "channel_name": "The Command Zone",
    "channel_handle": "@commandzone",
    "publish_date": "2024-03-15",
    "view_count": 150000,
    "duration_seconds": 1500
  }
]
```

### 2. `get_video_transcript`

Fetch the transcript/captions of a YouTube video.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `video_id` | string | required | YouTube video ID (e.g., "dQw4w9WgXcQ") |
| `include_timestamps` | bool | false | Whether to include timestamps |

**Returns:**
```json
{
  "video_id": "abc123xyz",
  "title": "Eldrazi Unbound Upgrade Guide",
  "transcript": "Full transcript text here...",
  "duration_seconds": 1500,
  "has_manual_captions": false,
  "language": "en"
}
```

### 3. `get_video_metadata`

Get detailed metadata about a YouTube video.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `video_id` | string | required | YouTube video ID |

**Returns:**
```json
{
  "video_id": "abc123xyz",
  "title": "Eldrazi Unbound Upgrade Guide",
  "channel_name": "The Command Zone",
  "channel_id": "UCHvYPT11GQYhfN9qP-r5uDg",
  "publish_date": "2024-03-15",
  "view_count": 150000,
  "like_count": 5000,
  "description": "In this video...",
  "tags": ["mtg", "commander", "edh", "eldrazi"],
  "duration_seconds": 1500
}
```

## Curated Channels

The following MTG content creator channels are configured for searching:

| Channel | Handle | Specialty |
|---------|--------|-----------|
| The Command Zone | @commandzone | Deck techs, upgrade guides, gameplay |
| EDHREC | @edlodc | Data-driven recommendations |
| Nitpicking Nerds | @nitpickingnerds | Upgrade guides, budget builds |
| Tolarian Community College | @taboranmtg | Product reviews, deck building |
| MTG Goldfish | @mtggoldfish | Budget builds, meta analysis |

You can add or remove channels by editing the configuration file:
`mcp-servers/youtube-research/src/youtube_research/config/channels.py`

## Usage Examples

### Example 1: Research a Precon

```
User: "Let's research YouTube videos for Eldrazi Unbound upgrades"

Claude will:
1. Search curated channels for "Eldrazi Unbound commander upgrade"
2. Fetch transcripts from relevant videos
3. Extract card recommendations mentioned
4. Present findings with sources
```

### Example 2: Research a Commander

```
User: "What do content creators recommend for Kozilek, the Great Distortion?"

Claude will:
1. Search for "Kozilek the Great Distortion EDH"
2. Analyze video transcripts
3. Identify frequently mentioned cards
4. Note synergies and strategies discussed
```

### Example 3: Budget Research

```
User: "Find budget upgrade ideas for Endless Punishment precon"

Claude will:
1. Search for "Endless Punishment budget upgrade"
2. Focus on videos mentioning budget considerations
3. Extract affordable card recommendations
```

## How Claude Extracts Cards

When Claude analyzes transcripts, it:

1. **Identifies card names** mentioned in context of recommendations
2. **Distinguishes add vs cut** recommendations
3. **Extracts reasoning** when creators explain their choices
4. **Notes synergies** when cards are mentioned together
5. **Validates names** using Scryfall fuzzy search

### Card Alias Handling

Content creators often use nicknames. Common aliases Claude recognizes:

| Alias | Full Card Name |
|-------|----------------|
| Bob | Dark Confidant |
| Steve | Sakura-Tribe Elder |
| Gary | Gray Merchant of Asphodel |
| Tim | Prodigal Sorcerer |
| Cyc Rift | Cyclonic Rift |
| Smothering | Smothering Tithe |
| Rhystic | Rhystic Study |

## Technical Details

### Backend: yt-dlp

The MCP server uses **yt-dlp** instead of the official YouTube Data API:

| Advantage | Details |
|-----------|---------|
| No quota limits | YouTube API limits to ~100 searches/day |
| No API key needed | Simpler setup |
| Better transcript support | Handles auto-generated and manual captions |
| Actively maintained | Regular updates for YouTube changes |

### Rate Limiting

To be respectful to YouTube:
- 1-2 second delay between requests
- Transcripts are cached to avoid re-fetching
- Search results are limited to relevant videos

### Error Handling

The server handles common issues:
- **No transcript available**: Some videos have captions disabled
- **Video unavailable**: Private or deleted videos
- **Rate limiting**: Automatic retry with backoff

## Configuration

### MCP Server Location

```
mcp-servers/youtube-research/
├── pyproject.toml
├── src/
│   └── youtube_research/
│       ├── server.py          # Main server
│       ├── tools/             # Tool implementations
│       ├── services/          # yt-dlp wrapper
│       └── config/
│           └── channels.py    # Curated channels
```

### Claude Code Settings

Add to your Claude Code MCP configuration:

```json
{
  "mcpServers": {
    "youtube-research": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/mcp-servers/youtube-research", "youtube-research"]
    }
  }
}
```

## Troubleshooting

### "No transcript available"

Some videos don't have captions:
- Creator disabled captions
- Very new video (auto-captions not generated yet)
- Non-English content without translation

**Solution**: Try a different video or manually watch the video.

### "Video unavailable"

The video may be:
- Private or unlisted
- Deleted
- Age-restricted

**Solution**: Verify the video ID is correct and the video is publicly accessible.

### "Search returned no results"

The query may be too specific or channels may not have relevant content.

**Solution**: Try broader search terms or different channels.

## Cost

| Component | Cost |
|-----------|------|
| yt-dlp | $0 (open source) |
| MCP Server | $0 (local) |
| LLM extraction | $0 (Claude does it natively) |
| **Total** | **$0** |

## Future Enhancements

Planned improvements:
- **Timestamp linking**: Deep-link to specific video moments
- **Diff view**: Highlight cards from YouTube not in current guide
- **Price lookup**: Cross-reference Scryfall prices
- **Caching**: Persist transcript cache across sessions
