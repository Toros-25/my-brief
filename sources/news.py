"""
M2 — News via RSS feeds (feedparser, no key required).

Sources:
  - NPR, BBC, The Guardian: general news feeds; keyword filter surfaces relevant pieces.
  - Inside Higher Ed: higher-ed news; catches international-student articles when they run.
  - Immigration Impact: immigration-advocacy publication; high hit rate against the keyword list.

Dead feeds tested and dropped:
  - Migration Policy Institute (migrationpolicy.org): user-provided URL and all alternative
    path patterns return 404 — no working RSS endpoint exists.
  - NAFSA (nafsa.org): all URL patterns return 404.
  - American Immigration Council: identical content to Immigration Impact (same feed, different
    domain); dropped as duplicate.

Keyword filter: keeps only entries whose title or summary contains at least one target phrase.
Rationale for substring matching vs. an NLP classifier:
  - These keywords are domain-specific acronyms and exact legal terms (SEVIS, OPT, CPT, H-1B),
    where substring matching is both precise and recall-complete — a classifier adds complexity
    without meaningful accuracy gain for this vocabulary.
  - It is deterministic, auditable, and dependency-free.
Trade-offs:
  - Miss: an article that discusses F-1 visa policy without using any listed phrase.
  - False positive: "immigration" in an unrelated context (e.g., European migration crisis).
"""

import feedparser
import re
import requests
from datetime import datetime, timezone

FEEDS = [
    {"source": "NPR",              "url": "https://feeds.npr.org/1001/rss.xml"},
    {"source": "BBC",              "url": "https://feeds.bbci.co.uk/news/rss.xml"},
    {"source": "The Guardian",     "url": "https://www.theguardian.com/world/rss"},
    {"source": "Inside Higher Ed", "url": "https://www.insidehighered.com/rss.xml"},
    {"source": "Immigration Impact","url": "https://immigrationimpact.com/feed/"},
]

HEADLINES_PER_FEED = 10  # cast a wider net pre-filter; digest picks top N after

# Match full phrases only — do NOT add bare "visa" here, because it would match
# unrelated results about the Visa credit card company.
# All patterns use word boundaries (\b...\b) so short acronyms like OPT and CPT
# are not accidentally triggered by common English substrings (e.g. "option",
# "opted", "script") — bare substring matching on 3-letter tokens produces too
# many false positives.
_RAW_KEYWORDS = [
    "f-1 visa", "f1 visa", "student visa",
    "international student", "international students",
    "OPT", "CPT", "STEM OPT",
    "H-1B", "H1B",
    "SEVP", "SEVIS", "USCIS",
    "immigration", "deportation",
]
_PATTERNS = [re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE) for kw in _RAW_KEYWORDS]

HEADERS = {"User-Agent": "WildcatBrief/1.0 (personal digest bot)"}


def _parse_published(entry) -> str:
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                dt = datetime(*t[:6], tzinfo=timezone.utc)
                return dt.strftime("%b %d, %I:%M %p UTC")
            except Exception:
                pass
    return ""


def _is_relevant(entry) -> bool:
    text = entry.get("title", "") + " " + entry.get("summary", "")
    return any(p.search(text) for p in _PATTERNS)


def fetch_news(headlines_per_feed: int = HEADLINES_PER_FEED) -> list[dict]:
    results = []
    for feed_cfg in FEEDS:
        try:
            resp = requests.get(feed_cfg["url"], headers=HEADERS, timeout=10)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except Exception as exc:
            print(f"[news] Could not fetch {feed_cfg['source']}: {exc}")
            continue

        for entry in feed.entries[:headlines_per_feed]:
            if not _is_relevant(entry):
                continue
            results.append({
                "source": feed_cfg["source"],
                "title": entry.get("title", "").strip(),
                "link": entry.get("link", ""),
                "published": _parse_published(entry),
                "summary": entry.get("summary", "").strip(),
            })
    return results


if __name__ == "__main__":
    articles = fetch_news()
    if not articles:
        print("No matching articles found in this fetch window.")
    else:
        current_source = None
        for a in articles:
            if a["source"] != current_source:
                current_source = a["source"]
                print(f"\n── {current_source} ──")
            pub = f"  [{a['published']}]" if a["published"] else ""
            print(f"  • {a['title']}{pub}")
        print(f"\nTotal: {len(articles)} article(s) matched.")
