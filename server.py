
@mcp.tool()
def detect_highlights(transcript: str):
    """Select up to five highlight clips from Hindi or English SRT."""

    if not transcript.strip():
        return {"error": "Transcript is empty."}

    timestamp_pattern = (
        r"(\d{1,2}):(\d{2}):(\d{2})(?:[,.]\d+)?"
        r"\s*-->\s*"
        r"(\d{1,2}):(\d{2}):(\d{2})(?:[,.]\d+)?"
    )

    def to_seconds(h, m, s):
        return int(h) * 3600 + int(m) * 60 + int(s)

    segments = []

    for block in re.split(r"\n\s*\n", transcript.strip()):
        lines = block.strip().splitlines()

        for index, line in enumerate(lines):
            match = re.search(timestamp_pattern, line.strip())

            if not match:
                continue

            groups = match.groups()
            start = to_seconds(*groups[:3])
            end = to_seconds(*groups[3:6])

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

    keyword_groups = {
        "hook": [
            "secret", "amazing", "surprise", "incredible",
            "you won't believe", "आज", "हैरान", "अविश्वसनीय"
        ],
        "suspense": [
            "mystery", "mysterious", "shocking", "unexpected",
            "रहस्य", "चौंकाने", "अचानक", "लेकिन", "क्योंकि"
        ],
        "story": [
            "finally", "discovered", "revealed", "first time",
            "खुलासा", "पता चला", "पहली बार", "आखिरकार"
        ]
    }

    for segment in segments:
        text = segment["text"].lower()
        reasons = []
        score = 0

        for category, words in keyword_groups.items():
            if any(word in text for word in words):
                score += 2
                reasons.append(category)

        if len(text.split()) >= 8:
            score += 1
            reasons.append("context")

        segment["score"] = score
        segment["reasons"] = reasons or ["Needs manual review"]

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

    selected.sort(key=lambda item: item["start_seconds"])

    return {
        "total_segments": len(segments),
        "clips_found": len(selected),
        "highlights": selected,
        "max_clips": 5,
        "language_support": ["Hindi", "English"],
        "note": "Keyword-based suggestions. Review clips before publishing."
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
    
