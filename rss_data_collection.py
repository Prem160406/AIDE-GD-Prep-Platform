#!/usr/bin/env python3
"""
AIDE Sem2 Module 1: RSS Data Collection Pipeline
v1.5 — FINAL LOCKED. No further changes expected.
Fixes from v1.4: article_id fallback bug, naive datetime crash.
"""

import json
import logging
import os
import re
import html
import time
import random
import threading
import requests
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import md5
import feedparser
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ─── Configuration ────────────────────────────────────────────────────────────

MODULE_VERSION = "1.5"

DEFAULT_FEEDS = [
    {"url": "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms",   "source": "TOI"},
    {"url": "https://www.thehindu.com/feeder/default.rss",                     "source": "The Hindu"},
    {"url": "https://feeds.bbci.co.uk/news/world/rss.xml",                     "source": "BBC World"},
    {"url": "https://indianexpress.com/feed/",                                  "source": "Indian Express"},
    {"url": "https://www.livemint.com/rss/news",                                "source": "Mint"},
    {"url": "https://feeds.feedburner.com/ndtvnews-top-stories",                "source": "NDTV"},
    {"url": "https://www.thehindu.com/business/Economy/feeder/default.rss",     "source": "The Hindu - Economy"},
    {"url": "https://www.thehindu.com/sci-tech/technology/feeder/default.rss",  "source": "The Hindu - Tech"},
]

FEEDS           = json.loads(os.getenv("RSS_FEEDS", json.dumps(DEFAULT_FEEDS)))
DAYS_BACK       = int(os.getenv("DAYS_BACK", "7"))
MAX_PER_SOURCE  = int(os.getenv("MAX_PER_SOURCE", "7"))
MIN_SUMMARY_LEN = int(os.getenv("MIN_SUMMARY_LENGTH", "30"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
PARALLEL_FEEDS  = min(5, len(FEEDS))
MIN_ARTICLES    = int(os.getenv("MIN_ARTICLES", "20"))

# ─── Thread-local Session ─────────────────────────────────────────────────────

thread_local = threading.local()

def get_session():
    """One session per thread — connection reuse + thread safety."""
    if not hasattr(thread_local, "session"):
        thread_local.session = requests.Session()
    return thread_local.session

# ─── Helper Functions ─────────────────────────────────────────────────────────

def get_with_retry(url, headers, timeout, retries=3):
    """
    Smart retry — 5xx only, not 4xx.
    Thread-local session for connection reuse.
    Backoff: 1s → 2s → 4s.
    """
    session = get_session()
    for attempt in range(retries):
        try:
            response = session.get(url, headers=headers, timeout=timeout)
            if response.status_code >= 500:
                raise requests.exceptions.RequestException(
                    f"Server error {response.status_code}"
                )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                wait = 2 ** attempt
                logger.warning(f"Retry {attempt + 1}/{retries} — waiting {wait}s ({e})")
                time.sleep(wait)
                continue
            raise


def parse_published_date(entry):
    """
    Single unified date parser — called ONCE per entry, reused everywhere.
    Priority: published_parsed → parsedate_to_datetime → ISO 8601 → datetime.min
    FIX v1.5: Normalizes naive datetime to UTC to prevent TypeError on comparison.
    """
    if entry.get("published_parsed"):
        try:
            return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        except Exception:
            pass

    published_str = entry.get("published", "")

    if published_str:
        try:
            dt = parsedate_to_datetime(published_str)
            # FIX v1.5: normalize naive datetime → UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            pass

    if published_str:
        try:
            dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            pass

    return datetime.min.replace(tzinfo=timezone.utc)


def get_summary(entry):
    """
    Fallback chain — never silently drop articles.
    summary → description → content[0].value
    """
    raw = (
        entry.get("summary") or
        entry.get("description") or
        (entry.get("content", [{}])[0].get("value") if entry.get("content") else "")
    )
    return raw.strip() if raw else ""


def clean_text(text):
    """Strip HTML tags, decode entities, normalize whitespace."""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', str(text))
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def is_recent(pub_dt, cutoff):
    """Check if parsed datetime is within required timeframe."""
    if pub_dt == datetime.min.replace(tzinfo=timezone.utc):
        return True
    return pub_dt >= cutoff


def article_id(link, title, source):
    """
    FIX v1.5: Uses title+source as fallback when link is empty.
    Prevents all no-link articles getting the same ID.
    """
    key = link if link else f"{source}:{title}"
    return md5(key.encode()).hexdigest()


# ─── Feed Worker ──────────────────────────────────────────────────────────────

def parse_single_feed(feed_info, cutoff):
    """Worker function for parallel feed fetching."""
    source = feed_info["source"]

    # Per-worker jitter — politeness / rate limit protection
    time.sleep(random.uniform(0.5, 1.5))

    try:
        response = get_with_retry(
            feed_info["url"],
            headers={'User-Agent': 'AIDE-GD-Prep/2.0'},
            timeout=REQUEST_TIMEOUT
        )

        feed = feedparser.parse(response.content)

        if not hasattr(feed, 'entries') or not feed.entries:
            return {"source": source, "status": "empty", "count": 0, "articles": []}

        articles   = []
        seen_links = set()
        count      = 0

        for entry in feed.entries:
            raw_summary = get_summary(entry)
            if not raw_summary:
                continue

            summary = clean_text(raw_summary)
            title   = clean_text(entry.get("title", ""))
            link    = entry.get("link", "")

            if len(summary) < MIN_SUMMARY_LEN:
                continue

            link_key = link if link else title
            if link_key in seen_links:
                continue
            seen_links.add(link_key)

            pub_dt = parse_published_date(entry)

            if not is_recent(pub_dt, cutoff):
                continue

            articles.append({
                "id":           article_id(link, title, source),
                "title":        title,
                "summary":      summary,
                "link":         link,
                "source":       source,
                "published":    pub_dt.isoformat(),
                "published_dt": pub_dt,
            })
            count += 1

            if count >= MAX_PER_SOURCE:
                break

        logger.info(f"{source}: {count} valid articles")
        return {"source": source, "status": "ok", "count": count, "articles": articles}

    except requests.exceptions.RequestException as e:
        logger.error(f"{source}: NETWORK FAILED — {e}")
        return {"source": source, "status": "error", "error": str(e), "count": 0, "articles": []}
    except Exception as e:
        logger.error(f"{source}: PARSE FAILED — {e}")
        return {"source": source, "status": "error", "error": str(e), "count": 0, "articles": []}


# ─── Main Pipeline ────────────────────────────────────────────────────────────

def collect_rss():
    """Parallel feed processing and merge."""
    logger.info("=" * 60)
    logger.info(f"MODULE 1 — RSS Collection v{MODULE_VERSION}")
    logger.info("=" * 60)

    cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)

    feed_results = []
    with ThreadPoolExecutor(max_workers=PARALLEL_FEEDS) as executor:
        futures = {
            executor.submit(parse_single_feed, feed, cutoff): feed
            for feed in FEEDS
        }
        for future in as_completed(futures):
            feed = futures[future]
            try:
                feed_results.append(future.result())
            except Exception as e:
                logger.error(f"Unexpected thread error [{feed['source']}]: {e}")
                feed_results.append({
                    "source": feed["source"], "status": "error",
                    "error": str(e), "count": 0, "articles": []
                })

    successful_feeds = sum(1 for r in feed_results if r["status"] == "ok")
    logger.info(f"Feeds: {successful_feeds}/{len(FEEDS)} succeeded")

    # Merge + global deduplicate by link
    all_articles = []
    seen_links   = set()

    for result in feed_results:
        for article in result.get("articles", []):
            link_key = article["link"] if article["link"] else article["title"]
            if link_key not in seen_links:
                seen_links.add(link_key)
                all_articles.append(article)

    # Sort newest first using pre-parsed datetime
    all_articles.sort(
        key=lambda x: x.get("published_dt", datetime.min.replace(tzinfo=timezone.utc)),
        reverse=True
    )

    # Remove published_dt — not JSON serializable
    for article in all_articles:
        article.pop("published_dt", None)

    feed_summary = [
        {"source": r["source"], "status": r["status"], "count": r.get("count", 0)}
        for r in feed_results
    ]

    now = datetime.now(timezone.utc).isoformat()

    if not all_articles:
        logger.error("Pipeline failure: zero articles collected")
        return {
            "status":         "failed",
            "module_version": MODULE_VERSION,
            "generated_at":   now,
            "total_articles": 0,
            "feed_summary":   feed_summary,
            "articles":       [],
            "error":          "Zero articles collected across all feeds"
        }

    status = "low_yield" if len(all_articles) < MIN_ARTICLES else "ok"
    if status == "low_yield":
        logger.warning(f"Low yield: {len(all_articles)} articles (min: {MIN_ARTICLES})")

    return {
        "platform":       "AIDE-GD-Prep",
        "module_version": MODULE_VERSION,
        "generated_at":   now,
        "status":         status,
        "total_articles": len(all_articles),
        "feed_summary":   feed_summary,
        "articles":       all_articles
    }


# ─── CLI Entrypoint ───────────────────────────────────────────────────────────

def main():
    """All file I/O here only — single save point."""
    output = collect_rss()

    with open("rss_output.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    if output["status"] == "failed":
        logger.error("Pipeline failed — error state saved to rss_output.json")
        exit(1)

    if output["status"] == "low_yield":
        logger.warning(f"Low yield run: {output['total_articles']} articles. Check feed_summary.")

    logger.info(f"✅ {output['total_articles']} articles saved to rss_output.json")
    exit(0)


if __name__ == "__main__":
    main()