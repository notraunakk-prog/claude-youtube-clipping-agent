
import os
import re
import json
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
        "youtube.com", "www.youtube.com",
        "m.youtube.com", "youtu.be"
    }

    if parsed.scheme != "https" or parsed.hostname not in allowed_hosts:
        return {"error": "Invalid HTTPS YouTube URL."}

    endpoint = (
        "https://www.youtube.com/oembed?url="
        + urllib.parse.quote(url, safe="")
        + "&format=json"
    )

    try:
        req = urllib.request.Request(
            endpoint,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        with urllib.request.urlopen(req, timeout=15) as response:
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
        item["score"] = sum(
            2 for word in keywords if word in text
        )

        if len(text.split()) >= 8:
            item["score"] += 1

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
  font-family: Arial;
  background: #111827;
  color: white;
  padding: 20px;
}
.box {
  max-width: 450px;
  margin: 40px auto;
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
<h2>YouTube Video Upload</h2>
<p>Upload an MP4 video (maximum 50 MB).</p>

<form id="uploadForm">
<label>Private Upload Token</label>
<input type="password" name="token" required>

<label>Select MP4 Video</label>
<input type="file" name="video" accept=".mp4,video/mp4" required>

<button id="uploadButton" type="submit">Upload Video</button>
</form>

<p id="result">Ready to upload.</p>
</div>

<script>
const form = document.getElementById("uploadForm");
const result = document.getElementById("result");
const button = document.getElementById("uploadButton");

form.addEventListener("submit", function(event) {
  event.preventDefault();

  const file = form.querySelector('input[type="file"]').files[0];

  if (!file) {
    result.textContent = "Please select a video.";
    return;
  }

  if (file.size > 50 * 1024 * 1024) {
    result.textContent = "Maximum file size is 50 MB.";
    return;
  }

  const xhr = new XMLHttpRequest();

  button.disabled = true;
  button.textContent = "Uploading...";
  result.textContent = "Starting upload...";

  xhr.open("POST", "/upload", true);
  xhr.timeout = 180000;

  xhr.upload.onprogress = function(event) {
    if (event.lengthComputable) {
      const percent = Math.round(
        event.loaded / event.total * 100
      );
      result.textContent = "Uploading: " + percent + "%";
    }
  };

  xhr.onload = function() {
    button.disabled = false;
    button.textContent = "Upload Video";

    try {
      const data = JSON.parse(xhr.responseText);
      result.textContent = JSON.stringify(data, null, 2);

      if (xhr.status >= 200 && xhr.status < 300) {
        form.reset();
      }
    } catch (error) {
      result.textContent =
        "Server response error. HTTP " + xhr.status;
    }
  };

  xhr.onerror = function() {
    button.disabled = false;
    button.textContent = "Upload Video";
    result.textContent = "Network error.";
  };

  xhr.ontimeout = function() {
    button.disabled = false;
    button.textContent = "Upload Video";
    result.textContent = "Upload timed out.";
  };

  xhr.send(new FormData(form));
});
</script>
</body>
</html>
""")


@mcp.custom_route("/upload", methods=["POST"])
async def upload_video(request: Request):
    print("UPLOAD ROUTE HIT", flush=True)

    expected_token = os.environ.get("UPLOAD_TOKEN")

    if not expected_token:
        print("UPLOAD_TOKEN is missing", flush=True)
        return JSONResponse(
            {"error": "Upload security is not configured."},
            status_code=503
        )

    try:
        form = await request.form()
        supplied_token = str(form.get("token", ""))

        if not secrets.compare_digest(supplied_token, expected_token):
            print("Invalid upload token", flush=True)
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
        destination = UPLOAD_DIR / (video_id + ".mp4")
        total_size = 0

        try:
            with destination.open("wb") as output:
                while True:
                    chunk = await video.read(1024 * 1024)

                    if not chunk:
                        break

                    total_size += len(chunk)

                    if total_size > MAX_UPLOAD_SIZE:
                        destination.unlink(missing_ok=True)
                        return JSONResponse(
                            {"error": "Maximum upload size is 50 MB."},
                            status_code=413
                        )

                    output.write(chunk)

            if total_size == 0:
                destination.unlink(missing_ok=True)
                return JSONResponse(
                    {"error": "Uploaded file is empty."},
                    status_code=400
                )

            safe_name = Path(video.filename).name[:100]

            uploaded_videos[video_id] = {
                "filename": safe_name,
                "path": str(destination),
                "size_bytes": total_size
            }

            print("UPLOAD SUCCESS:", video_id, flush=True)

            return JSONResponse({
                "status": "Upload successful",
                "video_id": video_id,
                "filename": safe_name,
                "size_bytes": total_size,
                "next_step": "Upload complete. Editing is not enabled yet."
            })

        finally:
            await video.close()

    except Exception as error:
        print("UPLOAD ERROR:", repr(error), flush=True)
        return JSONResponse(
            {"error": "Upload failed. Check Render logs."},
            status_code=500
        )


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
            
