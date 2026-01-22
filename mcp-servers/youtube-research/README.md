# YouTube Research MCP Server

An MCP (Model Context Protocol) server that provides tools for fetching YouTube video transcripts and metadata. Built for researching MTG content creator videos to inform deck upgrade guides.

## Features

- **Search Videos**: Find relevant MTG videos by commander, precon, or strategy
- **Fetch Transcripts**: Get full video transcripts for analysis
- **Get Metadata**: Access video details (views, date, description)
- **Curated Channels**: Pre-configured list of trusted MTG content creators

## Installation

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Install with uv

```bash
cd mcp-servers/youtube-research
uv sync
```

### Install with pip

```bash
cd mcp-servers/youtube-research
pip install -e .
```

## Usage

### Run the server

```bash
# With uv
uv run youtube-research

# With pip installation
youtube-research
```

### Configure in Claude Code

Add to your Claude Code MCP settings (`~/.claude/settings.json` or project `.claude/settings.local.json`):

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

## Available Tools

### `youtube_search_videos`

Search YouTube for videos matching a query.

```python
youtube_search_videos(
    query="Kozilek commander upgrade",
    channel_handles=["@commandzone", "@nitpickingnerds"],  # optional
    max_results=10,
    years_back=5
)
```

### `youtube_get_transcript`

Fetch the transcript of a video.

```python
youtube_get_transcript(
    video_id="abc123xyz",
    include_timestamps=False
)
```

### `youtube_get_metadata`

Get video metadata.

```python
youtube_get_metadata(video_id="abc123xyz")
```

### `youtube_list_channels`

List all curated MTG channels.

```python
youtube_list_channels()
```

## Curated Channels

The following MTG content creator channels are pre-configured:

| Channel | Handle | Specialty |
|---------|--------|-----------|
| The Command Zone | @commandzone | Deck techs, upgrade guides |
| EDHRECast | @EDHRECast | Data analysis, recommendations |
| Nitpicking Nerds | @NitpickingNerds | Upgrade guides, budget |
| Tolarian Community College | @TolarianCommunityCollege | Reviews, tutorials |
| MTGGoldfish | @MTGGoldfish | Budget builds, meta |
| Playing With Power MTG | @PlayingWithPowerMTG | cEDH, competitive |
| MTGMuddstah | @MTGMuddstah | Gameplay |
| I Hate Your Deck | @IHateYourDeck | High power gameplay |

## Technical Details

### Backend

Uses **yt-dlp** for YouTube data extraction:
- No YouTube API key required
- No quota limits
- Supports auto-generated and manual captions
- Caches transcripts for 7 days

### Caching

Transcripts are cached in the system temp directory to avoid re-fetching:
- Cache location: `$TMPDIR/youtube_research_cache/`
- Cache duration: 7 days

## Development

### Project Structure

```
youtube-research/
├── pyproject.toml
├── README.md
└── src/
    └── youtube_research/
        ├── __init__.py
        ├── server.py          # MCP server entry point
        ├── tools/
        │   ├── search.py      # Video search
        │   ├── transcript.py  # Transcript fetching
        │   └── metadata.py    # Video metadata
        ├── services/
        │   └── ytdlp.py       # yt-dlp wrapper
        └── config/
            └── channels.py    # Curated channels
```

### Running Tests

```bash
uv run pytest
```

## License

MIT
