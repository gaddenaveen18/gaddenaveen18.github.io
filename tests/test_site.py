"""Checks the build and the LinkedIn importer. Run: python -m pytest -q"""

import json
import re
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = Path(__file__).parent / "fixtures" / "Shares_test_fixture.csv"


@pytest.fixture
def site(tmp_path, monkeypatch):
    """A throwaway copy of the site so tests never touch your real posts."""
    copy = tmp_path / "site"
    shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("_site", ".git", "__pycache__", "tests"))
    monkeypatch.syspath_prepend(str(copy))
    for mod in ("build", "scripts.import_linkedin", "import_linkedin"):
        sys.modules.pop(mod, None)
    import build
    monkeypatch.setattr(build, "ROOT", copy)
    sys.path.insert(0, str(copy / "scripts"))
    import import_linkedin
    return copy, build, import_linkedin


def test_builds_with_no_posts(site):
    copy, build, _ = site
    for f in list((copy / "posts").glob("2026-*.md")) + list((copy / "books").glob("*.md")):
        f.unlink()  # start from an empty site
    for f in (copy / "frameworks").glob("*.md"):
        f.write_text(f.read_text().replace("date: 2026-11-05\n", ""))
    counts = build.build(copy / "_site")
    assert counts == {"posts": 0, "frameworks": 1, "books": 0, "pages": 1, "scheduled": []}
    home = (copy / "_site" / "index.html").read_text()
    assert "No posts yet." in home and "The Question Loop" in home
    for f in ["about/index.html", "posts/index.html", "frameworks/the-question-loop/index.html",
              "404.html", "feed.xml", "sitemap.xml", "robots.txt", ".nojekyll", "assets/css/site.css"]:
        assert (copy / "_site" / f).exists(), f


def test_import_and_build(site):
    copy, build, imp = site
    counts = imp.import_shares(FIXTURE, copy / "posts")
    assert counts["created"] == 4 and counts["skipped_private"] == 1 and counts["skipped_empty"] == 1
    again = imp.import_shares(FIXTURE, copy / "posts")
    assert again["created"] == 0 and again["existing"] == 4  # never overwrites

    post = next((copy / "posts").glob("2026-10-27-*.md")).read_text()
    assert "series: thought-experiment" in post and "tags: Leadership, SRE" in post
    assert "urn:li:person" not in post and "Test Person" in post
    assert "A Thought Experiment" not in post.split("---")[2]  # header line removed from body

    build.build(copy / "_site")
    out = copy / "_site"
    page = (out / "posts" / "sample-series-post-one" / "index.html").read_text()
    assert "<h1>Sample Series Post One</h1>" in page
    assert "Join the discussion on LinkedIn" in page
    assert "<br" in page  # LinkedIn line breaks kept
    two = (out / "posts" / "sample-series-post-two-a-longer-title-for-wrapping" / "index.html").read_text()
    assert "<h1>" in two and "<h1>not a heading" not in two
    home = (out / "index.html").read_text()
    assert "Sample Series Post One" in home and "latest" in home
    feed = (out / "feed.xml").read_text()
    assert feed.count("<entry>") == 4
    assert "/posts/sample-from-last-year/" in (out / "sitemap.xml").read_text()


def test_internal_links_resolve(site):
    copy, build, imp = site
    imp.import_shares(FIXTURE, copy / "posts")
    build.build(copy / "_site")
    out = copy / "_site"
    broken = []
    for page in out.rglob("*.html"):
        for href in re.findall(r'(?:href|src)="(/[^"#?]*)', page.read_text()):
            target = out / href.lstrip("/")
            if not (target.is_file() or (target / "index.html").is_file()):
                broken.append((page.relative_to(out), href))
    assert not broken


def test_custom_domain_and_base_path(site):
    copy, build, _ = site
    cfg = json.loads((copy / "site.json").read_text())
    cfg.update(custom_domain="example.com", base_path="/blog")
    (copy / "site.json").write_text(json.dumps(cfg))
    build.build(copy / "_site")
    assert (copy / "_site" / "CNAME").read_text().strip() == "example.com"
    assert 'href="/blog/assets/css/site.css"' in (copy / "_site" / "index.html").read_text()


@pytest.mark.parametrize("content, message", [
    ("---\ntitle: x\n", "isn't closed"),
    ("---\nno colon here\n---\nbody", "needs a colon"),
    ("---\ntitle: x\ndate: soon\n---\nbody", "date must look like"),
])
def test_clear_errors_for_broken_files(site, content, message):
    copy, build, _ = site
    (copy / "posts" / "2026-01-01-bad.md").write_text(content)
    with pytest.raises(build.ContentError, match=message):
        build.build(copy / "_site")


def test_drafts_and_templates_are_skipped(site):
    copy, build, _ = site
    (copy / "posts" / "2026-01-02-hidden.md").write_text("---\ntitle: Hidden\ndraft: true\n---\nbody")
    assert build.build(copy / "_site")["posts"] == 0  # _TEMPLATE.md and the draft are ignored


def test_rejects_wrong_csv(site, tmp_path):
    _, _, imp = site
    bad = tmp_path / "x.csv"
    bad.write_text("a,b\n1,2\n")
    with pytest.raises(SystemExit, match="Shares.csv"):
        imp.import_shares(bad, tmp_path / "out")


def test_scheduled_posts_appear_on_their_date(site):
    from datetime import date
    copy, build, _ = site
    for f in (copy / "posts").glob("2026-*.md"):
        f.unlink()
    (copy / "posts" / "2026-11-10-future.md").write_text("---\ntitle: Future Post\n---\nComing soon.")
    (copy / "posts" / "2026-11-01-today.md").write_text("---\ntitle: Today Post\n---\nOut now.")
    before = build.build(copy / "_site", today=date(2026, 11, 9))
    assert before["posts"] == 1 and before["scheduled"] == ["2026-11-10"]
    assert not (copy / "_site" / "posts" / "future").exists()
    assert "Future Post" not in (copy / "_site" / "feed.xml").read_text()
    on_day = build.build(copy / "_site", today=date(2026, 11, 10))
    assert on_day["posts"] == 2 and (copy / "_site" / "posts" / "future" / "index.html").exists()


def test_importer_handles_inline_title_and_fancy_bold(site):
    _, _, imp = site
    title, body, series, tags = imp.split_post("🧠 Thought Experiment: Right Questions vs. Right Answers\n\nBody text.\n\n#AI #Leadership")
    assert (title, series, tags) == ("Right Questions vs. Right Answers", True, ["AI", "Leadership"])
    title, body, series, _ = imp.split_post("🧠 A Thought Experiment\n\n𝗘𝗺𝗽𝗹𝗼𝘆𝗲𝗲 𝗯𝘆 𝗧𝗶𝘁𝗹𝗲.\n\n💡 𝗔 𝗷𝗼𝗯 𝗼𝗿 𝗮 𝘄𝗮𝘆?\nPlain line.")
    assert title == "Employee by Title." and series
    assert "**💡 A job or a way?**" in body and "Plain line." in body


def test_real_posts_build_with_images(site):
    from datetime import date
    copy, build, _ = site
    out = copy / "_site"
    early = build.build(out, today=date(2026, 11, 1))
    assert early["posts"] == 0 and early["frameworks"] == 0  # everything scheduled
    assert len(early["scheduled"]) == 6
    late = build.build(out, today=date(2026, 11, 20))
    assert late == {**late, "posts": 3, "frameworks": 1}
    page = (out / "posts" / "winning-over-winners" / "index.html").read_text()
    assert 'property="og:image"' in page and "winning-over-winners.jpg" in page and 'alt="Infographic' in page
    fw = (out / "frameworks" / "the-question-loop" / "index.html").read_text()
    assert 'href="/posts/right-questions-vs-right-answers/"' in fw  # links to its post once both are live
    assert (out / "assets" / "posts" / "right-questions-vs-right-answers.jpg").exists()


def test_missing_image_is_reported(site):
    copy, build, _ = site
    (copy / "posts" / "2020-01-01-x.md").write_text("---\ntitle: X\nimage: posts/nope.jpg\n---\nbody")
    with pytest.raises(build.ContentError, match="Image not found"):
        build.build(copy / "_site")


def test_books_appear_on_their_release_date(site):
    from datetime import date
    copy, build, _ = site
    out = copy / "_site"
    assert build.build(out, today=date(2026, 11, 4))["books"] == 0  # nothing before launch day
    early = build.build(out, today=date(2026, 11, 5))
    assert early["books"] == 1  # Vol. 1 launches first
    assert build.build(out, today=date(2026, 11, 9))["books"] == 2
    page = (out / "books" / "perfect-knowledge-vs-imperfect-brilliance" / "index.html").read_text()
    assert "Download the free PDF" in page and "Key ideas in one minute" in page
    assert 'href="/books/"' in (out / "index.html").read_text()  # nav + home strip
    assert not (out / "books" / "growth-through-giving").exists()
    late = build.build(out, today=date(2027, 3, 1))
    assert late["books"] == 7
    books = (out / "books" / "index.html").read_text()
    assert books.index("Vol. 1") < books.index("Vol. 7")
    rq = (out / "books" / "right-questions-vs-right-answers" / "index.html").read_text()
    assert 'href="/posts/right-questions-vs-right-answers/"' in rq  # links to its post
    for b in (copy / "books").glob("*.md"):
        stem = b.stem
        assert (out / "assets" / "books" / f"{stem}.pdf").exists() and (out / "assets" / "books" / f"{stem}.jpg").exists()


def test_missing_book_file_is_reported(site):
    copy, build, _ = site
    (copy / "books" / "vol9-x.md").write_text("---\ntitle: X\nvolume: 9\ncover: books/nope.jpg\npdf: books/nope.pdf\n---\nbody")
    with pytest.raises(build.ContentError, match="not found in static"):
        build.build(copy / "_site")


def test_post_links_to_its_book_once_released(site):
    from datetime import date
    copy, build, _ = site
    out = copy / "_site"
    build.build(out, today=date(2026, 11, 12))
    post = (out / "posts" / "winning-over-winners" / "index.html").read_text()
    assert "Go deeper" not in post  # Vol. 3 not released until Monday
    build.build(out, today=date(2026, 11, 5))
    post = (out / "posts" / "right-questions-vs-right-answers" / "index.html").read_text()
    assert "Go deeper" not in post  # Vol. 2 arrives on Monday
    build.build(out, today=date(2026, 11, 9))
    post = (out / "posts" / "right-questions-vs-right-answers" / "index.html").read_text()
    assert 'href="/books/right-questions-vs-right-answers/"' in post and "Go deeper" in post
