"""
Turns your LinkedIn data export into post files for this site.

1. On LinkedIn: Me > Settings & Privacy > Data privacy > Get a copy of your data.
   Request the archive, then download it when LinkedIn emails you.
2. Find Shares.csv inside the downloaded archive.
3. Run:   python scripts/import_linkedin.py path/to/Shares.csv

Creates one file per post in posts/. Existing files are never overwritten,
so it's safe to run again with a newer export: only new posts are added.
Posts that were visible to connections only are skipped unless you add
--include-connections-only.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from build import slugify  # noqa: E402

SERIES_MARKER = "a thought experiment"
HASHTAG_LINK = re.compile(r"\{hashtag\|\\?#\|([^}]+)\}")
MENTION = re.compile(r"@?\[([^\]]+)\]\(urn:li:[^)]+\)")
HASHTAG = re.compile(r"(?<![\w&])#(\w[\w-]*)", re.UNICODE)
LEADING_EMOJI = re.compile(r"^[^\w\"'“(]+", re.UNICODE)


def plain_letters(text: str) -> str:
    """LinkedIn 'bold' text uses special maths characters (𝗕𝗼𝗹𝗱). Turn them into
    normal letters so they read correctly and work with search and screen readers."""
    return "".join(unicodedata.normalize("NFKC", ch) if 0x1D400 <= ord(ch) <= 0x1D7FF else ch for ch in text)


def is_fancy_bold(line: str) -> bool:
    letters = [ch for ch in line if ch.isalpha()]
    return bool(letters) and sum(0x1D400 <= ord(ch) <= 0x1D7FF for ch in letters) / len(letters) > 0.8


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = HASHTAG_LINK.sub(r"#\1", text)
    text = MENTION.sub(r"\1", text)
    text = text.replace('""', '"')  # some exports double the quotes
    return text.strip().strip('"').strip()


def escape_markdown(line: str) -> str:
    """Stop LinkedIn text being read as Markdown headings or rules by accident."""
    if re.match(r"^\s*(#{1,6}\s|[-*_]{3,}\s*$)", line):
        return "\\" + line.lstrip()
    return line


def split_post(text: str) -> tuple[str, str, bool, list[str]]:
    """Return (title, body, is_series, tags)."""
    lines = [l.rstrip() for l in text.split("\n")]
    while lines and not lines[0].strip():
        lines.pop(0)
    first = plain_letters(lines[0]).lower() if lines else ""
    is_series = "thought experiment" in first
    inline_title = None
    if is_series:
        header = plain_letters(lines.pop(0))
        # "🧠 Thought Experiment: Right Questions vs. Right Answers" puts the title on the same line
        if ":" in header:
            inline_title = header.split(":", 1)[1].strip()
        while lines and not lines[0].strip():
            lines.pop(0)
    title_line = inline_title or (plain_letters(lines.pop(0)) if lines else "Untitled")
    title = LEADING_EMOJI.sub("", title_line).strip() or title_line.strip()
    if len(title) > 110:
        title = title[:107].rsplit(" ", 1)[0] + "…"
        lines.insert(0, title_line)  # first line was a sentence, keep it in the body

    # trailing lines made only of hashtags become tags
    tags: list[str] = []
    while lines and (not lines[-1].strip() or re.fullmatch(r"(\s*#\w[\w-]*\s*)+", lines[-1])):
        tags = HASHTAG.findall(lines.pop()) + tags
    out = []
    for l in lines:
        if is_fancy_bold(l):
            out.append(f"**{plain_letters(l).strip()}**")  # LinkedIn bold becomes real bold
        else:
            out.append(escape_markdown(plain_letters(l)))
    body = "\n".join(out).strip()
    return title, body, is_series, list(dict.fromkeys(tags))


def parse_date(value: str) -> datetime:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%m/%d/%Y %H:%M", "%m/%d/%y, %I:%M %p"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised date: {value!r}")


def front_matter_value(v: str) -> str:
    return '"' + v.replace('"', "'") + '"' if (":" in v or v.startswith(("'", '"', "#"))) else v


def import_shares(csv_path: Path, out_dir: Path, include_connections_only=False) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {"created": 0, "existing": 0, "skipped_empty": 0, "skipped_private": 0, "errors": 0}
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        cols = {c.lower().strip(): c for c in (reader.fieldnames or [])}
        need = {"date", "sharecommentary"}
        if not need <= set(cols):
            raise SystemExit(f"{csv_path.name} doesn't look like LinkedIn's Shares.csv (expected columns Date and ShareCommentary).")
        for row in reader:
            text = clean_text(row.get(cols["sharecommentary"], "") or "")
            if len(text) < 20:
                counts["skipped_empty"] += 1  # reposts without your own text
                continue
            visibility = (row.get(cols.get("visibility", ""), "") or "").upper()
            if "CONNECTIONS" in visibility and not include_connections_only:
                counts["skipped_private"] += 1
                continue
            try:
                when = parse_date(row[cols["date"]])
            except ValueError:
                counts["errors"] += 1
                continue
            title, body, is_series, tags = split_post(text)
            path = out_dir / f"{when:%Y-%m-%d}-{slugify(title)}.md"
            if path.exists():
                counts["existing"] += 1
                continue
            meta = [f"title: {front_matter_value(title)}"]
            if is_series:
                meta.append("series: thought-experiment")
            if tags:
                meta.append("tags: " + ", ".join(tags))
            link = row.get(cols.get("sharelink", ""), "") if "sharelink" in cols else ""
            if link:
                meta.append(f"linkedin_url: {link.strip()}")
            path.write_text("---\n" + "\n".join(meta) + "\n---\n\n" + body + "\n", encoding="utf-8")
            counts["created"] += 1
    return counts


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("shares_csv", type=Path)
    ap.add_argument("--include-connections-only", action="store_true")
    args = ap.parse_args()
    if not args.shares_csv.exists():
        raise SystemExit(f"File not found: {args.shares_csv}")
    c = import_shares(args.shares_csv, ROOT / "posts", args.include_connections_only)
    print(f"Created {c['created']} new post files in posts/.")
    print(f"Already there: {c['existing']}. Skipped: {c['skipped_empty']} without your own text, "
          f"{c['skipped_private']} connections-only, {c['errors']} with unreadable dates.")


if __name__ == "__main__":
    main()
