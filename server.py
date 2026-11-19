
import os
import json
import re
import urllib.parse
import urllib.request
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "YouTube Clipping Agent",
    host="0.0.0.0",
    port=int(os.environ.get("PORT", "10000"))
)

@mcp.tool()
def agent_status():
    """Check the agent status."""
    return {
        "name": "YouTube Clipping Agent",
        "status": "Online"
    }

@mcp.tool()
def inspect_video_url(url: str):
    """Get public YouTube video information."""
    parsed = urllib.parse.urlparse(url)
    allowed_hosts = {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "youtu.be"
    }

    if parsed.scheme != "https" or parsed.hostname not in allowed_hosts:
        return {"error": "Invalid YouTube URL."}

    endpoint = (
        "https://www.youtube.com/oembed?url="
        + urllib.parse.quote(url, safe="")
        + "&format=json"
    )

    try:
        request = urllib.request.Request(
            endpoint,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))

        return {
            "title": data.get("title"),
            "creator": data.get("author_name"),
            "thumbnail": data.get("thumbnail_url"),
            "status": "URL checked successfully"
        }

    except Exception:
        return {"error": "Video information unavailable."}


@mcp.tool()
def detect_highlights(transcript: str):
    """Find potentially interesting sections in a timestamped transcript."""

    if not transcript.strip():
        return {"error": "Transcript is empty."}

    pattern = r"(?:(\d{1,2}):)?(\d{1,2}):(\d{2})[,.]?\d*\s*[-–>]+\s*(?:(\d{1,2}):)?(\d{1,2}):(\d{2})[,.]?\d*\s*(.*)"

    segments = []

    for line in transcript.splitlines():
        match = re.search(pattern, line.strip())

        if match:
            h1, m1, s1, h2, m2, s2, text = match.groups()

            start = int(h1 or 0) * 3600 + int(m1) * 60 + int(s1)
            end = int(h2 or 0) * 3600 + int(m2) * 60 + int(s2)

            if end > start and text.strip():
                segments.append({
                    "start_seconds": start,
                    "end_seconds": end,
                    "text": text.strip()
                })

    if not segments:
        return {
            "error": "No timestamped transcript segments found.",
            "format": "Use SRT or timestamped text."
        }

    keywords = [
        "लेकिन", "क्योंकि", "रहस्य", "अविश्वसनीय",
        "लेकिन", "सच", "चौंकाने", "पहली बार",
        "secret", "amazing", "shocking", "surprising",
        "however", "finally", "impossible", "mystery",
        "why", "how", "secret"
    ]

    for segment in segments:
        text = segment["text"].lower()
        segment["score"] = sum(
            1 for word in keywords if word in text
        )

    segments.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    highlights = segments[:5]

    return {
        "total_segments": len(segments),
        "highlights": highlights,
        "note": "These are keyword-based suggestions. Review them before editing."
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
