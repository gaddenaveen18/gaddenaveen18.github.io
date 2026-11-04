"""
Builds the website into the _site folder.

You normally never run this yourself: GitHub runs it automatically every
time you add or change a file (see .github/workflows/deploy.yml).

To preview on your own computer (optional):
    pip install -r requirements.txt
    python build.py --serve        then open http://127.0.0.1:8000

Content lives in plain text files:
    posts/        one Markdown file per post   (2026-11-03-my-title.md)
    frameworks/   one Markdown file per framework
    books/        one Markdown file per book (cover and PDF go in static/books/)
    pages/        other pages (about.md)
    site.json     your name, links and settings
"""

from __future__ import annotations

import html
import json
import math
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "_site"


# ------------------------------------------------------------- content files

@dataclass
class Item:
    kind: str                 # "post", "framework", "book" or "page"
    slug: str
    title: str
    body_html: str
    meta: dict
    date: date | None = None
    tags: list[str] = field(default_factory=list)
    excerpt: str = ""

    @property
    def url(self) -> str:
        if self.kind == "post":
            return f"/posts/{self.slug}/"
        if self.kind == "framework":
            return f"/frameworks/{self.slug}/"
        if self.kind == "book":
            return f"/books/{self.slug}/"
        return f"/{self.slug}/"


class ContentError(Exception):
    pass


def parse_front_matter(text: str, path: Path) -> tuple[dict, str]:
    """Read the 'key: value' block between --- lines at the top of a file."""
    text = text.lstrip("﻿")
    if not text.startswith("---"):
        return {}, text
    parts = text.split("\n---", 1)
    if len(parts) < 2:
        raise ContentError(f"{path.name}: the --- block at the top isn't closed with another --- line.")
    meta = {}
    for line in parts[0].splitlines()[1:]:
        if not line.strip() or line.strip().startswith("#"):
            continue
        if ":" not in line:
            raise ContentError(f"{path.name}: this line in the --- block needs a colon: {line!r}")
        key, value = line.split(":", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        meta[key.strip().lower()] = value
    return meta, parts[1].lstrip("\n")


def render_markdown(body: str) -> str:
    # nl2br keeps LinkedIn-style single line breaks; sane_lists keeps numbered lists tidy
    return markdown.markdown(body, extensions=["nl2br", "sane_lists", "smarty"], output_format="html5")


def plain_excerpt(body_html: str, limit: int = 220) -> str:
    text = re.sub(r"<[^>]+>", " ", body_html)
    text = html.unescape(re.sub(r"\s+", " ", text)).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(",.;:") + "…"


def slugify(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text.lower(), flags=re.UNICODE)
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    s = re.sub(r"[^a-z0-9-]", "", s)  # keep URLs plain ASCII
    return s[:70].strip("-") or "post"


FILENAME_DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)$")


def load_folder(folder: Path, kind: str, today: date | None = None) -> list[Item]:
    """Read every .md file in a folder. Posts dated after `today` stay hidden
    until their day comes (scheduled posts)."""
    items = []
    if not folder.exists():
        return items
    for path in sorted(folder.glob("*.md")):
        if path.name.startswith(("_", ".")):
            continue  # files starting with _ are templates/drafts
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"), path)
        if meta.get("draft", "").lower() in {"true", "yes"}:
            continue
        stem = path.stem
        item_date = None
        m = FILENAME_DATE.match(stem)
        if m:
            stem = m.group(2)
            item_date = date.fromisoformat(m.group(1))
        if meta.get("date"):
            try:
                item_date = date.fromisoformat(meta["date"][:10])
            except ValueError:
                raise ContentError(f"{path.name}: date must look like 2026-11-03")
        if kind == "post" and not item_date:
            raise ContentError(f"{path.name}: posts need a date, either in the file name (2026-11-03-title.md) or as 'date:'")
        if today and item_date and kind in ("post", "framework", "book") and item_date > today:
            continue  # scheduled for later
        title = meta.get("title") or stem.replace("-", " ").capitalize()
        body_html = render_markdown(body)
        tags = [t.strip().lstrip("#") for t in meta.get("tags", "").split(",") if t.strip()]
        items.append(Item(kind, meta.get("slug") or slugify(stem), title, body_html, meta,
                          item_date, tags, meta.get("summary") or plain_excerpt(body_html)))
    slugs = [i.slug for i in items]
    dupes = {s for s in slugs if slugs.count(s) > 1}
    if dupes:
        raise ContentError(f"Two {kind}s would share the same address: {', '.join(sorted(dupes))}. Rename one file.")
    return items


# ------------------------------------------------------------- building

def format_date(d: date | None) -> str:
    return f"{d.day} {d.strftime('%B %Y')}" if d else ""


def site_today(cfg: dict) -> date:
    """Today's date in your time zone, so scheduled posts appear on the right day."""
    try:
        return datetime.now(ZoneInfo(cfg.get("timezone") or "UTC")).date()
    except Exception:
        return datetime.now(timezone.utc).date()


def build(out: Path = OUT, today: date | None = None) -> dict:
    cfg = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
    today = today or site_today(cfg)
    base = cfg.get("base_path", "").rstrip("/")
    site_url = (f"https://{cfg['custom_domain']}" if cfg.get("custom_domain") else cfg.get("url", "")).rstrip("/") + base

    posts = sorted(load_folder(ROOT / "posts", "post", today), key=lambda p: (p.date, p.slug), reverse=True)
    frameworks = load_folder(ROOT / "frameworks", "framework", today)
    books = sorted(load_folder(ROOT / "books", "book", today), key=lambda b: int(b.meta.get("volume", "0") or 0))
    pages = load_folder(ROOT / "pages", "page")
    series_label = cfg.get("series_label", "")
    series_posts = [p for p in posts if p.meta.get("series") == "thought-experiment"]

    for i, p in enumerate(posts):
        p.meta["newer"] = posts[i - 1] if i > 0 else None
        p.meta["older"] = posts[i + 1] if i + 1 < len(posts) else None
    by_title = {p.title.lower(): p for p in posts}
    for f in frameworks + books:
        src = f.meta.get("source_post", "").lower()
        f.meta["source"] = by_title.get(src)
    by_book_source = {b.meta.get("source_post", "").lower(): b for b in books if b.meta.get("source_post")}
    for p in posts:
        p.meta["book"] = by_book_source.get(p.title.lower())
    for b in books:
        b.meta["key_ideas"] = [k.strip() for k in b.meta.get("key_ideas", "").split("|") if k.strip()]

    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape(["html", "xml"]),
                      trim_blocks=True, lstrip_blocks=True)
    env.filters["date"] = format_date
    env.globals.update(cos=math.cos, sin=math.sin)
    env.globals.update(site=cfg, base=base, site_url=site_url, series_label=series_label,
                       nav_frameworks=frameworks, nav_books=bool(books), year=datetime.now().year)

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    def write(rel: str, template: str, **ctx):
        target = out / rel.strip("/") / "index.html" if not rel.endswith((".html", ".xml", ".txt")) else out / rel.strip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(env.get_template(template).render(path=rel, **ctx), encoding="utf-8")

    write("/", "home.html", posts=posts[: cfg.get("home_post_count", 6)], all_count=len(posts),
          latest_series=series_posts[0] if series_posts else None, frameworks=frameworks, books=books)
    write("/posts/", "archive.html", posts=posts, years=_group_by_year(posts))
    for p in posts:
        write(p.url, "post.html", item=p)
    for f in frameworks:
        write(f.url, "framework.html", item=f)
    if books:
        write("/books/", "books.html", books=books)
    for b in books:
        write(b.url, "book.html", item=b)
    for pg in pages:
        write(pg.url, "page.html", item=pg)
    write("404.html", "404.html")
    write("feed.xml", "feed.xml", posts=posts[:30],
          updated=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    write("sitemap.xml", "sitemap.xml", urls=["/", "/posts/"] + (["/books/"] if books else []) + [i.url for i in posts + frameworks + books + pages])
    (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {site_url}/sitemap.xml\n", encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    if cfg.get("custom_domain"):
        (out / "CNAME").write_text(cfg["custom_domain"].strip() + "\n", encoding="utf-8")
    shutil.copytree(ROOT / "static", out / "assets")
    scheduled = sorted(p.name[:10] for p in (ROOT / "posts").glob("[0-9]*.md") if p.name[:10] > today.isoformat())
    missing = [i.meta["image"] for i in posts + frameworks
               if i.meta.get("image") and not (ROOT / "static" / i.meta["image"]).is_file()]
    if missing:
        raise ContentError(f"Image not found in static/: {', '.join(missing)}")
    for b in load_folder(ROOT / "books", "book"):  # check files for scheduled books too
        for key in ("cover", "pdf", "audio"):
            if b.meta.get(key) and not (ROOT / "static" / b.meta[key]).is_file():
                raise ContentError(f"books: '{key}' file not found in static/: {b.meta[key]}")
    return {"posts": len(posts), "frameworks": len(frameworks), "books": len(books), "pages": len(pages), "scheduled": scheduled}


def _group_by_year(posts):
    years: dict[int, list] = {}
    for p in posts:
        years.setdefault(p.date.year, []).append(p)
    return sorted(years.items(), reverse=True)


def serve(port: int = 8000) -> None:
    import functools
    import http.server
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(OUT))
    print(f"Preview at http://127.0.0.1:{port}  (Ctrl+C to stop)")
    http.server.ThreadingHTTPServer(("127.0.0.1", port), handler).serve_forever()


if __name__ == "__main__":
    try:
        counts = build()
    except ContentError as exc:
        print(f"\nBuild stopped: {exc}\n")
        sys.exit(1)
    print(f"Built {counts['posts']} posts, {counts['frameworks']} frameworks, {counts['books']} books, {counts['pages']} pages into _site/")
    if counts["scheduled"]:
        print(f"Scheduled for later (hidden until their date): {', '.join(counts['scheduled'])}")
    if "--serve" in sys.argv:
        serve()
