"""Standard-library subtitle parser shared by cleaning and diagnostic checks."""
import html
import re

TIME = r"(?:\d+:)?\d{2}:\d{2}[,.]\d{3}"
TIMING = re.compile(rf"({TIME})\s*-->\s*({TIME})")


def seconds(value):
    parts = value.replace(",", ".").split(":")
    total = 0.0
    for part in parts:
        total = total * 60 + float(part)
    return total


def read_cues(path):
    raw = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    cues = []
    for block in re.split(r"\n\s*\n", raw):
        lines = block.strip().splitlines()
        for index, line in enumerate(lines):
            match = TIMING.search(line)
            if not match:
                continue
            start, end = map(seconds, match.groups())
            if start < 0 or end <= start:
                raise ValueError(f"Invalid cue timing: {line}")
            text = html.unescape(re.sub(r"<[^>]+>", "", " ".join(lines[index + 1:])))
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                cues.append((start, end, text))
            break
    return cues
