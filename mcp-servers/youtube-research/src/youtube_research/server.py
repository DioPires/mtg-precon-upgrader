"""YouTube Research MCP Server.

This MCP server provides tools for fetching YouTube video data
to assist with MTG deck research and upgrade analysis.
"""

from fastmcp import FastMCP

from .tools.metadata import MetadataResult, get_video_metadata
from .tools.search import SearchResult, search_youtube_videos, list_curated_channels
from .tools.transcript import TranscriptResult, get_video_transcript
from .config.channels import CURATED_CHANNELS

# Create the MCP server
mcp = FastMCP(
    name="youtube-research",
    instructions="""YouTube Research MCP Server for MTG deck analysis.

This server provides tools to search and analyze YouTube videos from MTG content creators.
Use these tools when researching deck upgrades, commander strategies, or card recommendations.

Available tools:
- search_youtube_videos: Find relevant videos about commanders, precons, or strategies
- get_video_transcript: Fetch the full transcript of a video for analysis
- get_video_metadata: Get video details (views, date, description)

Curated MTG channels available:
- @commandzone (The Command Zone)
- @EDHRECast (EDHRECast)
- @NitpickingNerds (Nitpicking Nerds)
- @TolarianCommunityCollege
- @MTGGoldfish
- @PlayingWithPowerMTG
- @MTGMuddstah
- @IHateYourDeck

Workflow example:
1. Search for videos: search_youtube_videos("Kozilek commander upgrade")
2. Get transcript: get_video_transcript("video_id")
3. Analyze transcript for card recommendations
""",
)


@mcp.tool()
async def youtube_search_videos(
    query: str,
    channel_handles: list[str] | None = None,
    max_results: int = 10,
    years_back: int = 5,
) -> SearchResult:
    """Search YouTube for videos matching a query.

    Use this tool to find relevant MTG content creator videos about
    a specific commander, precon, or deck strategy.

    Args:
        query: Search terms (e.g., "Kozilek commander upgrade", "Eldrazi Unbound deck tech")
        channel_handles: Optional list of channel handles to filter by
                        (e.g., ["@commandzone", "@nitpickingnerds"])
        max_results: Maximum number of videos to return (default: 10)
        years_back: Only include videos from the last N years (default: 5)

    Returns:
        SearchResult with matching videos.
    """
    return await search_youtube_videos(
        query=query,
        channel_handles=channel_handles,
        max_results=max_results,
        years_back=years_back,
    )


@mcp.tool()
async def youtube_get_transcript(
    video_id: str,
    include_timestamps: bool = False,
) -> TranscriptResult:
    """Fetch the transcript of a YouTube video.

    Use this tool to get the full text of what was said in a video.
    Useful for extracting card recommendations and strategy advice.

    Args:
        video_id: YouTube video ID (the part after v= in the URL)
        include_timestamps: Include timestamps in the transcript (default: False)

    Returns:
        TranscriptResult with the full transcript text.
    """
    return await get_video_transcript(
        video_id=video_id,
        include_timestamps=include_timestamps,
    )


@mcp.tool()
async def youtube_get_metadata(video_id: str) -> MetadataResult:
    """Get metadata about a YouTube video.

    Use this tool to get details about a video before fetching its transcript.
    Helpful for checking video relevance, date, and view count.

    Args:
        video_id: YouTube video ID (the part after v= in the URL)

    Returns:
        MetadataResult with video details.
    """
    return await get_video_metadata(video_id=video_id)


@mcp.tool()
def youtube_list_channels() -> list[dict]:
    """List all curated MTG YouTube channels.

    Returns the list of MTG content creator channels that are
    configured for searching. Use these handles with search_youtube_videos.

    Returns:
        List of channel information with handle, name, and specialty.
    """
    return list_curated_channels()


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
