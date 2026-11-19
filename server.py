
import os
import json
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
    """Check the current status of the YouTube Clipping Agent."""
    return {
        "name": "YouTube Clipping Agent",
        "status": "Online",
        "message": "MCP server is running."
    }

@mcp.tool()
def inspect_video_url(url: str):
    """Check public YouTube video information using its URL."""
    parsed = urllib.parse.urlparse(url)
    allowed_hosts = {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "youtu.be"
    }

    if parsed.scheme != "https" or parsed.hostname not in allowed_hosts:
        return {"error": "Please provide a valid HTTPS YouTube URL."}

    endpoint = "https://www.youtube.com/oembed?url=" + urllib.parse.quote(url, safe="") + "&format=json"

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
        return {
            "error": "Could not read video information. Check the URL or video availability."
        }

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
    
