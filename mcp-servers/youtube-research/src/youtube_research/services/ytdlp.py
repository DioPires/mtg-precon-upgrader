"""yt-dlp wrapper service for YouTube data extraction."""

import asyncio
import json
import re
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yt_dlp


class YtDlpService:
    """Service for extracting YouTube video data using yt-dlp."""

    def __init__(self, cache_dir: Path | None = None):
        """Initialize the yt-dlp service.

        Args:
            cache_dir: Optional directory for caching transcripts.
        """
        self.cache_dir = cache_dir or Path(tempfile.gettempdir()) / "youtube_research_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Base yt-dlp options
        self._base_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }

    async def get_video_metadata(self, video_id: str) -> dict[str, Any]:
        """Get metadata for a YouTube video.

        Args:
            video_id: YouTube video ID.

        Returns:
            Dictionary containing video metadata.
        """
        url = f"https://www.youtube.com/watch?v={video_id}"

        opts = {
            **self._base_opts,
            "skip_download": True,
        }

        def extract():
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False)

        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, extract)

        if not info:
            raise ValueError(f"Could not extract metadata for video {video_id}")

        return {
            "video_id": video_id,
            "title": info.get("title", ""),
            "channel_name": info.get("channel", info.get("uploader", "")),
            "channel_id": info.get("channel_id", ""),
            "channel_handle": info.get("uploader_id", ""),
            "publish_date": self._format_date(info.get("upload_date")),
            "view_count": info.get("view_count", 0),
            "like_count": info.get("like_count", 0),
            "description": info.get("description", ""),
            "tags": info.get("tags", []),
            "duration_seconds": info.get("duration", 0),
            "thumbnail_url": info.get("thumbnail", ""),
        }

    async def get_video_transcript(
        self,
        video_id: str,
        include_timestamps: bool = False
    ) -> dict[str, Any]:
        """Get transcript/captions for a YouTube video.

        Args:
            video_id: YouTube video ID.
            include_timestamps: Whether to include timestamps in output.

        Returns:
            Dictionary containing transcript data.
        """
        url = f"https://www.youtube.com/watch?v={video_id}"

        # Check cache first
        cache_file = self.cache_dir / f"{video_id}_transcript.json"
        if cache_file.exists():
            with open(cache_file) as f:
                cached = json.load(f)
                # Check if cache is still valid (7 days)
                cached_time = datetime.fromisoformat(cached.get("cached_at", "2000-01-01"))
                if datetime.now() - cached_time < timedelta(days=7):
                    if include_timestamps:
                        return cached
                    else:
                        # Strip timestamps from cached data
                        result = cached.copy()
                        result["transcript"] = self._strip_timestamps(result.get("transcript_with_timestamps", result.get("transcript", "")))
                        return result

        # Create temp directory for subtitle files
        with tempfile.TemporaryDirectory() as tmpdir:
            opts = {
                **self._base_opts,
                "skip_download": True,
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": ["en", "en-US", "en-GB"],
                "subtitlesformat": "json3",
                "outtmpl": f"{tmpdir}/%(id)s.%(ext)s",
            }

            def extract():
                with yt_dlp.YoutubeDL(opts) as ydl:
                    return ydl.extract_info(url, download=False)

            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, extract)

            if not info:
                raise ValueError(f"Could not extract info for video {video_id}")

            # Find the subtitle file
            transcript_text = ""
            transcript_with_timestamps = ""
            has_manual_captions = False
            language = "en"

            # Check for subtitles in the info
            subtitles = info.get("subtitles", {})
            automatic_captions = info.get("automatic_captions", {})

            # Prefer manual subtitles over automatic
            sub_data = None
            for lang in ["en", "en-US", "en-GB"]:
                if lang in subtitles:
                    has_manual_captions = True
                    sub_data = subtitles[lang]
                    language = lang
                    break
                elif lang in automatic_captions:
                    sub_data = automatic_captions[lang]
                    language = lang
                    break

            if sub_data:
                # Find json3 format
                json3_url = None
                for fmt in sub_data:
                    if fmt.get("ext") == "json3":
                        json3_url = fmt.get("url")
                        break

                if json3_url:
                    # Download and parse the subtitles
                    transcript_text, transcript_with_timestamps = await self._download_and_parse_subtitles(
                        json3_url
                    )

            if not transcript_text:
                raise ValueError(f"No transcript available for video {video_id}")

            result = {
                "video_id": video_id,
                "title": info.get("title", ""),
                "transcript": transcript_text if not include_timestamps else transcript_with_timestamps,
                "transcript_with_timestamps": transcript_with_timestamps,
                "duration_seconds": info.get("duration", 0),
                "has_manual_captions": has_manual_captions,
                "language": language,
                "cached_at": datetime.now().isoformat(),
            }

            # Cache the result
            with open(cache_file, "w") as f:
                json.dump(result, f)

            return result

    async def search_videos(
        self,
        query: str,
        channel_handle: str | None = None,
        max_results: int = 10,
        years_back: int = 5,
    ) -> list[dict[str, Any]]:
        """Search for YouTube videos.

        Args:
            query: Search query.
            channel_handle: Optional channel handle to search within.
            max_results: Maximum number of results.
            years_back: How many years back to search.

        Returns:
            List of video metadata dictionaries.
        """
        # Build search URL
        if channel_handle:
            # Search within a specific channel
            handle = channel_handle.lstrip("@")
            search_url = f"https://www.youtube.com/@{handle}/search?query={query}"
        else:
            # General YouTube search
            search_url = f"ytsearch{max_results}:{query}"

        opts = {
            **self._base_opts,
            "extract_flat": True,
            "playlistend": max_results,
        }

        def extract():
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(search_url, download=False)

        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, extract)

        if not info:
            return []

        # Handle both playlist (channel search) and search results
        entries = info.get("entries", [])
        if not entries and info.get("id"):
            # Single video result
            entries = [info]

        results = []
        cutoff_date = datetime.now() - timedelta(days=years_back * 365)

        for entry in entries[:max_results]:
            if not entry:
                continue

            # Parse upload date
            upload_date = entry.get("upload_date")
            if upload_date:
                try:
                    video_date = datetime.strptime(upload_date, "%Y%m%d")
                    if video_date < cutoff_date:
                        continue
                except ValueError:
                    pass

            results.append({
                "video_id": entry.get("id", ""),
                "title": entry.get("title", ""),
                "channel_name": entry.get("channel", entry.get("uploader", "")),
                "channel_handle": entry.get("uploader_id", ""),
                "publish_date": self._format_date(upload_date),
                "view_count": entry.get("view_count", 0),
                "duration_seconds": entry.get("duration", 0),
            })

        return results

    async def _download_and_parse_subtitles(self, url: str) -> tuple[str, str]:
        """Download and parse JSON3 subtitle data.

        Args:
            url: URL to the JSON3 subtitle file.

        Returns:
            Tuple of (plain_text, text_with_timestamps).
        """
        import urllib.request

        def download():
            with urllib.request.urlopen(url) as response:
                return json.loads(response.read().decode("utf-8"))

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, download)

        events = data.get("events", [])

        plain_segments = []
        timestamped_segments = []

        for event in events:
            segs = event.get("segs", [])
            if not segs:
                continue

            text = "".join(seg.get("utf8", "") for seg in segs).strip()
            if not text:
                continue

            # Get timestamp
            start_ms = event.get("tStartMs", 0)
            timestamp = self._format_timestamp(start_ms)

            plain_segments.append(text)
            timestamped_segments.append(f"[{timestamp}] {text}")

        plain_text = " ".join(plain_segments)
        # Clean up repeated spaces and newlines
        plain_text = re.sub(r"\s+", " ", plain_text).strip()

        timestamped_text = "\n".join(timestamped_segments)

        return plain_text, timestamped_text

    def _format_timestamp(self, ms: int) -> str:
        """Format milliseconds as HH:MM:SS or MM:SS."""
        seconds = ms // 1000
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    def _format_date(self, date_str: str | None) -> str:
        """Format date string from YYYYMMDD to YYYY-MM-DD."""
        if not date_str:
            return ""
        try:
            dt = datetime.strptime(date_str, "%Y%m%d")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return date_str

    def _strip_timestamps(self, text: str) -> str:
        """Remove timestamps from text."""
        # Remove [HH:MM:SS] or [MM:SS] patterns
        return re.sub(r"\[\d+:\d{2}(:\d{2})?\]\s*", "", text)
