@AGENTS.md

## YouTube Research MCP Server

**Location**: `mcp-servers/youtube-research/`

An MCP server that allows Claude to research MTG content creator videos when building upgrade guides.

### Available Tools (after restart)
- `youtube_search_videos` - Search YouTube for MTG videos
- `youtube_get_transcript` - Fetch video transcripts
- `youtube_get_metadata` - Get video details
- `youtube_list_channels` - List curated channels

### Usage
Ask Claude to research YouTube videos for a precon:
```
"Research YouTube videos for Eldrazi Unbound upgrades"
```

### Context File
See `mcp-servers/youtube-research/CLAUDE_CONTEXT.md` for full implementation details and troubleshooting.
