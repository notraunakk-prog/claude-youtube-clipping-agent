
import os
import re
import json
import html
import uuid
import secrets
import urllib.parse
import urllib.request

from pathlib import Path
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse

mcp = FastMCP(
    "YouTube Clipping Agent",
    host="0.0.0.0",
    port=int(os.environ.get("PORT", "10000"))
)

UPLOAD_DIR = Path("/tmp/youtube-agent-uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_SIZE = 50 * 1024 * 1024
uploaded_videos = {}


@mcp.tool()
def agent_status():
    return {
        "name": "YouTube Clipping Agent",
        "status": "Online",
        "tools": [
            "agent_status",
            "inspect_video_url",
            "detect_highlights",
            "list_uploaded_videos"
        ]
    }


@mcp.tool()
def inspect_video_url(url: str):
    parsed = urllib.parse.urlparse(url)

    allowed_hosts = {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "youtu.be"
    }

    if parsed.scheme != "https" or parsed.hostname not in allowed_hosts:
        return {"error": "Invalid HTTPS YouTube URL."}

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

    except Exception as error:
        return {
            "error": "Video information unavailable.",
            "details": str(error)[:200]
        }


@mcp.tool()
def detect_highlights(transcript: str):
    if not transcript.strip():
        return {"error": "Transcript is empty."}

    pattern = (
        r"(\d{1,2}):(\d{2}):(\d{2})(?:[,.]\d+)?"
        r"\s*-->\s*"
        r"(\d{1,2}):(\d{2}):(\d{2})(?:[,.]\d+)?"
    )

    def seconds(h, m, s):
        return int(h) * 3600 + int(m) * 60 + int(s)

    segments = []

    for block in re.split(r"\n\s*\n", transcript.strip()):
        lines = block.splitlines()

        for index, line in enumerate(lines):
            match = re.search(pattern, line.strip())

            if match:
                groups = match.groups()
                start = seconds(*groups[:3])
                end = seconds(*groups[3:6])

                text = " ".join(
                    item.strip()
                    for item in lines[index + 1:]
                    if item.strip()
                )

                if end > start and text:
                    segments.append({
                        "start_seconds": start,
                        "end_seconds": end,
                        "text": text
                    })
                break

    if not segments:
        return {"error": "No timestamped SRT segments found."}

    keywords = [
        "secret", "amazing", "surprise", "incredible",
        "mystery", "shocking", "unexpected",
        "हैरान", "रहस्य", "चौंकाने", "खुलासा",
        "पहली बार", "आखिरकार", "लेकिन"
    ]

    for item in segments:
        text = item["text"].lower()
        score = sum(2 for word in keywords if word in text)

        if len(text.split()) >= 8:
            score += 1

        item["score"] = score

    ranked = sorted(
        segments,
        key=lambda item: item["score"],
        reverse=True
    )

    selected = []

    for candidate in ranked:
        overlaps = any(
            candidate["start_seconds"] < item["end_seconds"]
            and candidate["end_seconds"] > item["start_seconds"]
            for item in selected
        )

        if not overlaps:
            selected.append(candidate)

        if len(selected) == 5:
            break

    return {
        "total_segments": len(segments),
        "clips_found": len(selected),
        "highlights": sorted(
            selected,
            key=lambda item: item["start_seconds"]
        ),
        "note": "Keyword-based suggestions. Review before editing."
    }


@mcp.tool()
def list_uploaded_videos():
    return {
        "videos": [
            {
                "video_id": video_id,
                "filename": info["filename"],
                "size_bytes": info["size_bytes"]
            }
            for video_id, info in uploaded_videos.items()
        ]
    }


@mcp.custom_route("/", methods=["GET"])
async def upload_page(request: Request):
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>YouTube Shorts Agent</title>
      <style>
        body {
          font-family: Arial, sans-serif;
          background: #111827;
          color: white;
          padding: 25px;
        }
        .box {
          max-width: 450px;
          margin: 50px auto;
          background: #1f2937;
          padding: 25px;
          border-radius: 16px;
        }
        input, button {
          width: 100%;
          box-sizing: border-box;
          padding: 14px;
          margin-top: 15px;
          border-radius: 8px;
        }
        button {
          background: #2563eb;
          color: white;
          border: 0;
          font-weight: bold;
        }
        #result {
          white-space: pre-wrap;
          overflow-wrap: anywhere;
        }
      </style>
    </head>
    <body>
      <div class="box">
        <h2>Video Upload</h2>
        <p>Upload an MP4 video for Shorts processing.</p>

        <form id="uploadForm">
          <label>Private upload token</label>
          <input
            type="password"
            name="token"
            required
            autocomplete="off"
          >

          <label>Select MP4 video</label>
          <input
            type="file"
            name="video"
            accept=".mp4,video/mp4"
            required
          >

          <button type="submit">Upload Video</button>
        </form>

        <p id="result"></p>
      </div>

      <script>
        const form = document.getElementById("uploadForm");
        const result = document.getElementById("result");

        form.addEventListener("submit", async (event) => {
          event.preventDefault();
          result.textContent = "Uploading...";

          try {
            const response = await fetch("/upload", {
              method: "POST",
              body: new FormData(form)
            });

            const data = await response.json();
            result.textContent = JSON.stringify(data, null, 2);

            if (response.ok) form.reset();
          } catch (error) {
            result.textContent = "Upload failed. Please try again.";
          }
        });
      </script>
    </body>
    </html>
    """)


@mcp.custom_route("/upload", methods=["POST"])
async def upload_video(request: Request):
    expected_token = os.environ.get("UPLOAD_TOKEN")

    if not expected_token:
        return JSONResponse(
            {"error": "Upload security is not configured."},
            status_code=503
        )

    form = await request.form()
    supplied_token = str(form.get("token", ""))

    if not secrets.compare_digest(supplied_token, expected_token):
        return JSONResponse(
            {"error": "Invalid upload token."},
            status_code=401
        )

    video = form.get("video")

    if not video or not getattr(video, "filename", None):
        return JSONResponse(
            {"error": "Please select an MP4 video."},
            status_code=400
        )

    if Path(video.filename).suffix.lower() != ".mp4":
        return JSONResponse(
            {"error": "Only MP4 files are accepted."},
            status_code=400
        )

    video_id = uuid.uuid4().hex
    destination = UPLOAD_DIR / f"{video_id}.mp4"
    total_size = 0

    try:
        with destination.open("wb") as output:
            while True:
                chunk = await video.read(1024 * 1024)

                if not chunk:
                    break

                total_size += len(chunk)

                if total_size > MAX_UPLOAD_SIZE:
                    output.close()
                    destination.unlink(missing_ok=True)

                    return JSONResponse(
                        {"error": "Maximum upload size is 50 MB."},
                        status_code=413
                    )

                output.write(chunk)

        if total_size == 0:
            destination.unlink(missing_ok=True)
            return JSONResponse(
                {"error": "The uploaded file is empty."},
                status_code=400
            )

        safe_name = Path(video.filename).name[:100]

        uploaded_videos[video_id] = {
            "filename": safe_name,
            "path": str(destination),
            "size_bytes": total_size
        }

        return JSONResponse({
            "status": "Upload successful",
            "video_id": video_id,
            "filename": safe_name,
            "size_bytes": total_size,
            "next_step": "Video is uploaded. Editing is not enabled yet."
        })

    except Exception:
        destination.unlink(missing_ok=True)
        return JSONResponse(
            {"error": "Upload could not be completed."},
            status_code=500
        )

    finally:
        await video.close()


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
            
