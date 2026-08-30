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
Applied uniformly to every entry from every feed — no source is exempt, including
immigration-focused feeds that cover many topics outside F-1/student/work-visa scope.

Rationale for substring matching vs. an NLP classifier:
  - These keywords are exact legal terms and acronyms (SEVIS, OPT, CPT, H-1B, F-1),
    where substring matching is both precise and recall-complete — a classifier adds
    complexity without meaningful accuracy gain for this vocabulary.
  - It is deterministic, auditable, and dependency-free.
Trade-offs:
  - Miss: an article discussing F-1 or H-1B policy without using any listed phrase.
  - False positive: rare, since all remaining terms are highly domain-specific.
  - "immigration" and "deportation" are intentionally excluded — they are broad enough
    to match general enforcement stories (ICE operations, border policy, public figures
    being deported) that have nothing to do with F-1/student/work visas.
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

# All patterns use word boundaries (\b...\b) so short acronyms like OPT and CPT
# are not triggered by common English substrings (e.g. "option", "script").
# Do NOT add bare "visa" — matches the Visa credit card company.
# Do NOT add "immigration" or "deportation" — too broad; pulls in ICE enforcement,
# border policy, and deportation of public figures with no F-1/H-1B relevance.
_RAW_KEYWORDS = [
    "F-1", "F-1 visa", "F1 visa",
    "international student", "international students", "student visa",
    "OPT", "CPT", "STEM OPT", "cap-gap",
    "SEVP", "SEVIS",
    "H-1B", "H1B", "H-1B cap", "H-1B lottery",
    "work visa", "employment-based visa",
    "high-skilled worker", "high-skilled workers",
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
