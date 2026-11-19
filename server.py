
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("YouTube Clipping Agent")

@mcp.tool()
def agent_status():
    """Returns the current status of the YouTube Clipping Agent."""
    return {
        "name": "YouTube Clipping Agent",
        "status": "Ready",
        "features": [
            "Video highlight detection",
            "Live stream recording highlights",
            "Vertical 9:16 Shorts editing",
            "Automatic subtitles",
            "YouTube uploading"
        ],
        "message": "Initial MCP server is ready."
    }

if __name__ == "__main__":
    mcp.run(transport="stdio")
  
