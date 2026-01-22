# Claude Context - YouTube Research MCP Server

**Last Updated:** 2025-01-22
**Status:** Implementation Complete, Ready for Testing

## What Was Just Built

A YouTube video analysis MCP server that allows Claude to research MTG content creator videos when building upgrade guides.

### Architecture
```
User asks Claude to research a deck
         ↓
Claude calls youtube_* MCP tools
         ↓
MCP server uses yt-dlp (no API quotas)
         ↓
Claude analyzes transcripts and extracts cards
         ↓
Claude incorporates findings into upgrade guides
```

### Available MCP Tools

After restarting Claude Code, these tools should be available:

1. **`youtube_search_videos`** - Search YouTube for MTG videos
   ```
   youtube_search_videos(
     query="Eldrazi Unbound commander upgrade",
     channel_handles=["@commandzone"],  # optional
     max_results=10,
     years_back=5
   )
   ```

2. **`youtube_get_transcript`** - Fetch video transcript
   ```
   youtube_get_transcript(
     video_id="abc123",
     include_timestamps=False
   )
   ```

3. **`youtube_get_metadata`** - Get video details
   ```
   youtube_get_metadata(video_id="abc123")
   ```

4. **`youtube_list_channels`** - List curated MTG channels

### Curated Channels Configured

- @commandzone (The Command Zone)
- @EDHRECast (EDHRECast)
- @NitpickingNerds (Nitpicking Nerds)
- @TolarianCommunityCollege
- @MTGGoldfish
- @PlayingWithPowerMTG
- @MTGMuddstah
- @IHateYourDeck

## Files Created

```
mcp-servers/youtube-research/
├── pyproject.toml
├── README.md
├── .venv/                    # Python virtual environment
└── src/youtube_research/
    ├── __init__.py
    ├── server.py             # FastMCP server entry point
    ├── tools/
    │   ├── __init__.py
    │   ├── search.py
    │   ├── transcript.py
    │   └── metadata.py
    ├── services/
    │   ├── __init__.py
    │   └── ytdlp.py          # yt-dlp wrapper with caching
    └── config/
        ├── __init__.py
        └── channels.py

Other files:
- YOUTUBE_DATA_FETCHING.md    # Full documentation
- .mcp.json                   # MCP server configuration
- .claude/settings.local.json # Updated to enable MCP servers
```

## What To Do Next

### 1. Verify MCP Server Connection
After restart, check if the tools are available by asking:
"List the YouTube research tools available"

### 2. Test with Real MTG Video
Try searching and fetching a real Command Zone video:
```
1. Search: "Eldrazi Unbound commander upgrade"
2. Get transcript from the Command Zone result
3. Extract card recommendations from the transcript
```

### 3. Full Integration Test
Ask Claude to research upgrades for a precon:
"Research YouTube videos for Eldrazi Unbound upgrades and tell me what cards content creators recommend"

## Pending Enhancements (Optional)

These were identified but not implemented:

1. **Persistent cache** - Save transcripts to project directory instead of temp
2. **Timestamp deep-links** - Link to specific video moments where cards are mentioned
3. **Price lookup** - Cross-reference Scryfall prices with recommendations
4. **Diff against guide** - Highlight cards from YouTube not in current deck.json
5. **More channels** - User can add more channels to config/channels.py

## Troubleshooting

### MCP Server Not Available
If tools aren't available after restart:
1. Check `.mcp.json` exists in project root
2. Check `enableAllProjectMcpServers: true` in `.claude/settings.local.json`
3. Try running manually: `cd mcp-servers/youtube-research && source .venv/bin/activate && python -m youtube_research.server`

### Transcript Fetch Fails
- Some videos have captions disabled
- Try a different video from the search results
- Check if video is age-restricted or private

## Key Design Decisions

1. **yt-dlp over YouTube API** - No quota limits, no API key needed
2. **Python + FastMCP** - Better YouTube libraries than Node.js
3. **Claude does extraction** - No external LLM costs, uses conversation context
4. **Curated channels** - Quality control over which content to analyze
