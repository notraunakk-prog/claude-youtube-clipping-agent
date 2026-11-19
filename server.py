
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
    """Find interesting sections in Hindi or English SRT transcripts."""

    if not transcript.strip():
        return {"error": "Transcript is empty."}

    timestamp_pattern = (
        r"(\d{1,2}):(\d{2}):(\d{2})(?:[,.]\d+)?"
        r"\s*-->\s*"
        r"(\d{1,2}):(\d{2}):(\d{2})(?:[,.]\d+)?"
    )

    bracket_pattern = (
        r"\[(\d{1,2}):(\d{2}):(\d{2})\]\s*(.*)"
    )

    def to_seconds(h, m, s):
        return int(h) * 3600 + int(m) * 60 + int(s)

    segments = []

    for block in re.split(r"\n\s*\n", transcript.strip()):
        lines = block.strip().splitlines()

        if not lines:
            continue

        for index, line in enumerate(lines):
            match = re.search(timestamp_pattern, line.strip())

            if match:
                groups = match.groups()
                start = to_seconds(*groups[:3])
                end = to_seconds(*groups[3:6])

                text = " ".join(
                    item.strip()
                    for item in lines[index + 1:]
                    if item.strip()
                )

                if not text:
                    text = line[match.end():].strip()

                if end > start and text:
                    segments.append({
                        "start_seconds": start,
                        "end_seconds": end,
                        "text": text
                    })

                break

        else:
            for line in lines:
                match = re.search(bracket_pattern, line.strip())

                if match:
                    h, m, s, text = match.groups()
                    start = to_seconds(h, m, s)

                    if text.strip():
                        segments.append({
                            "start_seconds": start,
                            "end_seconds": start + 15,
                            "text": text.strip()
                        })

    if not segments:
        return {
            "error": "No timestamped transcript segments found."
        }

    keywords = [
        "लेकिन", "क्योंकि", "रहस्य", "अविश्वसनीय",
        "सच", "चौंकाने", "पहली बार",
        "secret", "amazing", "shocking",
        "surprising", "however", "finally",
        "impossible", "mystery", "why", "how"
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

    return {
        "total_segments": len(segments),
        "highlights": segments[:5],
        "note": "Keyword-based suggestions. Review before editing."
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
                
