"""Tool for fetching YouTube video metadata."""

from pydantic import BaseModel, Field

from ..services.ytdlp import YtDlpService


class MetadataResult(BaseModel):
    """Result from fetching video metadata."""

    video_id: str = Field(description="YouTube video ID")
    title: str = Field(description="Video title")
    channel_name: str = Field(description="Channel name")
    channel_id: str = Field(description="Channel ID")
    channel_handle: str = Field(description="Channel handle (e.g., @commandzone)")
    publish_date: str = Field(description="Publish date in YYYY-MM-DD format")
    view_count: int = Field(description="Number of views")
    like_count: int = Field(description="Number of likes")
    description: str = Field(description="Video description")
    tags: list[str] = Field(description="Video tags")
    duration_seconds: int = Field(description="Video duration in seconds")
    thumbnail_url: str = Field(description="URL to video thumbnail")


_service = YtDlpService()


async def get_video_metadata(video_id: str) -> MetadataResult:
    """Get detailed metadata about a YouTube video.

    Use this tool to get information about a video before deciding
    whether to fetch its transcript. Useful for checking video date,
    view count, and relevance.

    Args:
        video_id: YouTube video ID (e.g., "dQw4w9WgXcQ" from youtube.com/watch?v=dQw4w9WgXcQ)

    Returns:
        MetadataResult containing detailed video information.

    Raises:
        ValueError: If the video cannot be found or accessed.
    """
    result = await _service.get_video_metadata(video_id)

    return MetadataResult(
        video_id=result["video_id"],
        title=result["title"],
        channel_name=result["channel_name"],
        channel_id=result["channel_id"],
        channel_handle=result["channel_handle"],
        publish_date=result["publish_date"],
        view_count=result["view_count"],
        like_count=result["like_count"],
        description=result["description"],
        tags=result["tags"],
        duration_seconds=result["duration_seconds"],
        thumbnail_url=result["thumbnail_url"],
    )
