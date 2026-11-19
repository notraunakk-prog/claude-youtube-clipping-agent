
@mcp.tool()
def detect_highlights(transcript: str):
    """Find interesting sections in SRT or timestamped transcripts."""

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

        timestamp_line = None
        timestamp_index = -1

        for index, line in enumerate(lines):
            match = re.search(timestamp_pattern, line.strip())
            if match:
                timestamp_line = match
                timestamp_index = index
                break

        if timestamp_line:
            groups = timestamp_line.groups()

            start = to_seconds(*groups[:3])
            end = to_seconds(*groups[3:6])

            text = " ".join(
                line.strip()
                for line in lines[timestamp_index + 1:]
                if line.strip()
            )

            if not text:
                text = lines[timestamp_index][timestamp_line.end():].strip()

            if end > start and text:
                segments.append({
                    "start_seconds": start,
                    "end_seconds": end,
                    "text": text
                })

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
    
