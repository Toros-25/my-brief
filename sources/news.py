"""
M2 — News via RSS feeds (feedparser, no key required).

Sources:
  - NPR, BBC, The Guardian: general news feeds; keyword filter surfaces relevant pieces.
  - Inside Higher Ed: higher-ed news; catches international-student articles when they run.
  - Immigration Impact: immigration-advocacy publication; high hit rate against the keyword list.
  - Google News search feeds (4 targeted queries): pre-filtered by Google's index across
    thousands of publishers. Already topically relevant, but the keyword filter still runs
    as a second pass to catch any off-topic articles Google's algorithm includes.

Dead feeds tested and dropped:
  - Migration Policy Institute: all URL patterns return 404.
  - NAFSA: all URL patterns return 404.
  - American Immigration Council: identical content to Immigration Impact (same feed).
  - Chronicle of Higher Education: all URL patterns return 404.
  - Federal Register / DHS: entries have no titles and empty summaries — feed is broken.
  - Federal Register / USCIS: only 2 entries, both administrative paperwork notices
    (collection activity extensions), not policy or news.

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

Deduplication: Google News search feeds can return the same article across multiple
queries. A seen-URLs set is used to drop duplicates before returning results.
"""

import feedparser
import re
import requests
from datetime import datetime, timezone

# General feeds scan fewer entries since most won't match; Google News feeds
# are already query-filtered so we pull more to maximise coverage.
_DEFAULT_LIMIT = 10
_GNEWS_LIMIT = 25

FEEDS = [
    {"source": "NPR",               "url": "https://feeds.npr.org/1001/rss.xml"},
    {"source": "BBC",               "url": "https://feeds.bbci.co.uk/news/rss.xml"},
    {"source": "The Guardian",      "url": "https://www.theguardian.com/world/rss"},
    {"source": "Inside Higher Ed",  "url": "https://www.insidehighered.com/rss.xml"},
    {"source": "Immigration Impact","url": "https://immigrationimpact.com/feed/"},
    # Google News search feeds — one per targeted query.
    # %22 is URL-encoded double-quote, forcing Google to treat the phrase as an
    # exact match rather than individual keywords.
    {
        "source": "Google News",
        "url": "https://news.google.com/rss/search?q=%22F-1+visa%22&hl=en-US&gl=US&ceid=US:en",
        "limit": _GNEWS_LIMIT,
    },
    {
        "source": "Google News",
        "url": "https://news.google.com/rss/search?q=%22H-1B+visa%22&hl=en-US&gl=US&ceid=US:en",
        "limit": _GNEWS_LIMIT,
    },
    {
        "source": "Google News",
        "url": "https://news.google.com/rss/search?q=%22international+students%22+visa&hl=en-US&gl=US&ceid=US:en",
        "limit": _GNEWS_LIMIT,
    },
    {
        "source": "Google News",
        "url": "https://news.google.com/rss/search?q=SEVIS+OR+%22STEM+OPT%22+OR+%22cap-gap%22&hl=en-US&gl=US&ceid=US:en",
        "limit": _GNEWS_LIMIT,
    },
]

# All patterns use word boundaries (\b...\b) so short acronyms like OPT and CPT
# are not triggered by common English substrings (e.g. "option", "script").
# Do NOT add bare "visa" — matches the Visa credit card company.
# Do NOT add "immigration" or "deportation" — too broad; pulls in ICE enforcement,
# border policy, and deportation of public figures with no F-1/H-1B relevance.
# Plural forms ("student visas", "work visas") are listed explicitly because
# \bstudent visa\b does not match "student visas" — the trailing \b requires a
# word boundary, which fails when the next character is still a word char ("s").
_RAW_KEYWORDS = [
    "F-1", "F-1 visa", "F-1 visas", "F1 visa",
    "international student", "international students", "student visa", "student visas",
    "OPT", "CPT", "STEM OPT", "cap-gap",
    "SEVP", "SEVIS",
    "H-1B", "H1B", "H-1B cap", "H-1B lottery",
    "work visa", "work visas", "employment-based visa", "employment-based visas",
    "high-skilled worker", "high-skilled workers",
]
_PATTERNS = [re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE) for kw in _RAW_KEYWORDS]

HEADERS = {"User-Agent": "WildcatBrief/1.0 (personal digest bot)"}


def _parse_published(entry) -> tuple[datetime | None, str]:
    # Returns both a sortable datetime and a display string from the same parse.
    # Keeping them together avoids parsing the timestamp twice.
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                dt = datetime(*t[:6], tzinfo=timezone.utc)
                return dt, dt.strftime("%b %d, %I:%M %p UTC")
            except Exception:
                pass
    return None, ""


def _is_relevant(entry) -> bool:
    text = entry.get("title", "") + " " + entry.get("summary", "")
    return any(p.search(text) for p in _PATTERNS)


MAX_ARTICLES = 10


def fetch_news() -> list[dict]:
    results = []
    seen_urls: set[str] = set()

    for feed_cfg in FEEDS:
        limit = feed_cfg.get("limit", _DEFAULT_LIMIT)
        try:
            resp = requests.get(feed_cfg["url"], headers=HEADERS, timeout=10)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except Exception as exc:
            print(f"[news] Could not fetch {feed_cfg['source']} ({feed_cfg['url'][:50]}...): {exc}")
            continue

        for entry in feed.entries[:limit]:
            if not _is_relevant(entry):
                continue
            link = entry.get("link", "")
            if link in seen_urls:
                continue
            seen_urls.add(link)
            dt, pub_str = _parse_published(entry)
            results.append({
                "source": feed_cfg["source"],
                "title": entry.get("title", "").strip(),
                "link": link,
                "published": pub_str,
                "summary": entry.get("summary", "").strip(),
                "_dt": dt,  # used for sorting; stripped before returning
            })

    # Sort all matched articles newest-first, then take the top 10.
    # Articles with no parseable date sort to the bottom (None < any datetime
    # would error, so we use a sentinel: datetime.min for missing timestamps).
    results.sort(key=lambda a: a["_dt"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    results = results[:MAX_ARTICLES]

    # Remove the internal sort key before returning — callers and the template
    # don't need it and it would clutter the dict.
    for a in results:
        del a["_dt"]

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
