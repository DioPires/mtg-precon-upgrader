"""Tool for searching YouTube videos."""

from pydantic import BaseModel, Field

from ..config.channels import CURATED_CHANNELS, get_channel_by_handle
from ..services.ytdlp import YtDlpService


class VideoResult(BaseModel):
    """A single video search result."""

    video_id: str = Field(description="YouTube video ID")
    title: str = Field(description="Video title")
    channel_name: str = Field(description="Channel name")
    channel_handle: str = Field(description="Channel handle")
    publish_date: str = Field(description="Publish date in YYYY-MM-DD format")
    view_count: int = Field(description="Number of views")
    duration_seconds: int = Field(description="Video duration in seconds")


class SearchResult(BaseModel):
    """Result from searching YouTube videos."""

    query: str = Field(description="The search query used")
    channel_filter: str | None = Field(description="Channel filter applied, if any")
    videos: list[VideoResult] = Field(description="List of matching videos")
    total_found: int = Field(description="Number of videos found")


_service = YtDlpService()


async def search_youtube_videos(
    query: str,
    channel_handles: list[str] | None = None,
    max_results: int = 10,
    years_back: int = 5,
) -> SearchResult:
    """Search YouTube for videos matching a query.

    Use this tool to find relevant MTG content creator videos about
    a specific commander, precon, or deck strategy. You can optionally
    filter to specific curated channels.

    Args:
        query: Search terms (e.g., "Kozilek commander upgrade", "Eldrazi Unbound deck tech")
        channel_handles: Optional list of channel handles to search within
                        (e.g., ["@commandzone", "@nitpickingnerds"]).
                        If not provided, searches all of YouTube.
        max_results: Maximum number of videos to return (default: 10)
        years_back: Only include videos from the last N years (default: 5)

    Returns:
        SearchResult containing matching videos.

    Available curated channels:
    - @commandzone (The Command Zone) - deck techs, upgrade guides
    - @EDHRECast (EDHRECast) - data analysis, recommendations
    - @NitpickingNerds (Nitpicking Nerds) - upgrade guides, budget
    - @TolarianCommunityCollege - reviews, tutorials
    - @MTGGoldfish - budget builds, meta analysis
    - @PlayingWithPowerMTG - cEDH, competitive
    - @MTGMuddstah - gameplay
    - @IHateYourDeck - high power gameplay
    """
    all_videos: list[VideoResult] = []

    if channel_handles:
        # Search within specified channels
        for handle in channel_handles:
            channel = get_channel_by_handle(handle)
            if not channel:
                continue

            results = await _service.search_videos(
                query=query,
                channel_handle=channel["handle"],
                max_results=max_results,
                years_back=years_back,
            )

            for video in results:
                all_videos.append(VideoResult(
                    video_id=video["video_id"],
                    title=video["title"],
                    channel_name=video["channel_name"],
                    channel_handle=video["channel_handle"],
                    publish_date=video["publish_date"],
                    view_count=video["view_count"],
                    duration_seconds=video["duration_seconds"],
                ))
    else:
        # General YouTube search
        results = await _service.search_videos(
            query=query,
            channel_handle=None,
            max_results=max_results,
            years_back=years_back,
        )

        for video in results:
            all_videos.append(VideoResult(
                video_id=video["video_id"],
                title=video["title"],
                channel_name=video["channel_name"],
                channel_handle=video["channel_handle"],
                publish_date=video["publish_date"],
                view_count=video["view_count"],
                duration_seconds=video["duration_seconds"],
            ))

    # Sort by view count (most popular first)
    all_videos.sort(key=lambda v: v.view_count, reverse=True)

    # Limit to max_results
    all_videos = all_videos[:max_results]

    return SearchResult(
        query=query,
        channel_filter=", ".join(channel_handles) if channel_handles else None,
        videos=all_videos,
        total_found=len(all_videos),
    )


def list_curated_channels() -> list[dict]:
    """List all curated MTG channels available for searching.

    Returns:
        List of channel information dictionaries.
    """
    return [
        {
            "handle": ch["handle"],
            "name": ch["name"],
            "specialty": ch["specialty"],
        }
        for ch in CURATED_CHANNELS
    ]
