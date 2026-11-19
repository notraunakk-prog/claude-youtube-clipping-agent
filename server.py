
import os
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
        "features": [
            "Video highlight detection",
            "Live stream recording highlights",
            "Vertical 9:16 Shorts editing",
            "Hindi subtitles",
            "YouTube uploading"
        ],
        "message": "MCP server is running."
    }

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
    
