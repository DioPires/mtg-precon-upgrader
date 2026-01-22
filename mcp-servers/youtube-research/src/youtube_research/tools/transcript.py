"""Tool for fetching YouTube video transcripts."""

from pydantic import BaseModel, Field

from ..services.ytdlp import YtDlpService


class TranscriptResult(BaseModel):
    """Result from fetching a video transcript."""

    video_id: str = Field(description="YouTube video ID")
    title: str = Field(description="Video title")
    transcript: str = Field(description="Full transcript text")
    duration_seconds: int = Field(description="Video duration in seconds")
    has_manual_captions: bool = Field(description="Whether video has manual (not auto-generated) captions")
    language: str = Field(description="Caption language code")


_service = YtDlpService()


async def get_video_transcript(
    video_id: str,
    include_timestamps: bool = False,
) -> TranscriptResult:
    """Fetch the transcript/captions of a YouTube video.

    Use this tool to get the full text transcript of a YouTube video.
    This is useful for analyzing what content creators say about
    specific cards, commanders, or deck strategies.

    Args:
        video_id: YouTube video ID (e.g., "dQw4w9WgXcQ" from youtube.com/watch?v=dQw4w9WgXcQ)
        include_timestamps: Whether to include timestamps in the transcript (default: False)

    Returns:
        TranscriptResult containing the video transcript and metadata.

    Raises:
        ValueError: If no transcript is available for the video.
    """
    result = await _service.get_video_transcript(video_id, include_timestamps)

    return TranscriptResult(
        video_id=result["video_id"],
        title=result["title"],
        transcript=result["transcript"],
        duration_seconds=result["duration_seconds"],
        has_manual_captions=result["has_manual_captions"],
        language=result["language"],
    )
