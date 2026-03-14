#!/usr/bin/env python3
"""
AIDE Sem2 Module 1: RSS Data Collection Pipeline (Production v2.0)
Parallel feeds + P0-P3 production hardening
VIT Pune GD Prep Platform
"""

import json
import logging
import os
import re
import html
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime, timezone, timedelta
import feedparser
from concurrent.futures import ThreadPoolExecutor
from hashlib import md5

# Setup professional logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────
DEFAULT_FEEDS = [
    {"url": "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms", "source": "TOI"},
    {"url": "https://www.thehindu.com/feeder/default.rss", "source": "The Hindu"},
    {"url": "http://feeds.bbci.co.uk/news/world/rss.xml", "source": "BBC World"},
    {"url": "https://indianexpress.com/section/opinion/feed/", "source": "Indian Express - Opinion"},
    {"url": "https://www.livemint.com/rss/news", "source": "Mint"},
    {"url": "https://www.bing.com/news/search?q=Artificial+Intelligence+Tech+India&format=rss", "source": "Bing - Technology & AI"},
    {"url": "https://www.bing.com/news/search?q=Indian+Economy+Startups&format=rss", "source": "Bing - Economy & Business"},
    {"url": "https://www.bing.com/news/search?q=Climate+Change+ESG+India&format=rss", "source": "Bing - Environment & ESG"},
]

FEEDS = json.loads(os.getenv("RSS_FEEDS", json.dumps(DEFAULT_FEEDS)))
DAYS_BACK = int(os.getenv("DAYS_BACK", "7"))
MAX_PER_SOURCE = int(os.getenv("MAX_PER_SOURCE", "7"))
MIN_SUMMARY_LENGTH = int(os.getenv("MIN_SUMMARY_LENGTH", "30"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
PARALLEL_FEEDS = min(5, len(FEEDS))

CUTOFF = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)

# ─────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────
def create_http_session():
    """Create requests session with robust retries for failing APIs."""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def clean_text(text):
    """Strip HTML tags, decode entities, and normalize whitespace."""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', str(text))
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def is_recent(entry):
    """Check if the article is within the required timeframe."""
    published = entry.get("published_parsed")
    if not published:
        return True
    pub_date = datetime(*published[:6], tzinfo=timezone.utc)
    return pub_date >= CUTOFF

def article_id(title, source):
    """Generate a unique ID for idempotency checks."""
    return md5(f"{title}:{source}".encode()).hexdigest()

def parse_single_feed(feed_info):
    """Worker function for parallel feed fetching using requests for timeout."""
    source = feed_info["source"]
    try:
        session = create_http_session()
        # Use requests to fetch the feed with a proper timeout
        response = session.get(
            feed_info["url"], 
            headers={'User-Agent': 'AIDE-GD-Prep/2.0'},
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status() # Raise an error for bad status codes (404, 500, etc)
        
        # Pass the downloaded raw string content to feedparser
        feed = feedparser.parse(response.content)
        
        if not hasattr(feed, 'entries') or not feed.entries:
            return {"source": source, "status": "empty", "count": 0, "articles": []}
        
        articles = []
        seen_titles = set()
        count = 0
        
        for entry in feed.entries:
            raw_summary = entry.get("summary", "").strip()
            if not raw_summary:
                continue
            
            summary = clean_text(raw_summary)
            title = clean_text(entry.get("title", ""))
            
            if len(summary) < MIN_SUMMARY_LENGTH:
                continue
                
            if title in seen_titles:
                continue
            seen_titles.add(title)
            
            if not is_recent(entry):
                continue
            
            article = {
                "id": article_id(title, source),
                "title": title,
                "summary": summary,
                "content": summary,
                "link": entry.get("link", ""),
                "source": source,
                "published": str(entry.get("published", "unknown")),
                "possibly_truncated": len(summary) < 100
            }
            articles.append(article)
            count += 1
            
            if count >= MAX_PER_SOURCE:
                break
                
        logger.info(f"{source}: Fetched {count} valid articles.")
        return {"source": source, "status": "ok", "count": count, "articles": articles}
        
    except requests.exceptions.RequestException as e:
        logger.error(f"{source}: NETWORK FAILED - {str(e)}")
        return {"source": source, "status": "error", "error": str(e), "count": 0, "articles": []}
    except Exception as e:
        logger.error(f"{source}: PARSE FAILED - {str(e)}")
        return {"source": source, "status": "error", "error": str(e), "count": 0, "articles": []}


# ─────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────
def collect_rss():
    """Executes parallel feed processing and merges results."""
    logger.info("Starting Parallel RSS Collection...")
    
    with ThreadPoolExecutor(max_workers=PARALLEL_FEEDS) as executor:
        feed_results = list(executor.map(parse_single_feed, FEEDS))
    
    all_articles = []
    seen_titles = set()
    
    for result in feed_results:
        for article in result.get("articles", []):
            title_hash = md5(article["title"].encode()).hexdigest()
            if title_hash not in seen_titles:
                seen_titles.add(title_hash)
                all_articles.append(article)
    
    if not all_articles:
        logger.error("Pipeline failure: Zero total articles collected.")
        return {
            "status": "failed",
            "articles": []
        }
        
    output = {
        "platform": "AIDE-GD-Prep",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_articles": len(all_articles),
        "articles": all_articles
    }
    
    return output

def main():
    """CLI entrypoint."""
    output = collect_rss()
    
    if output.get("status") == "failed":
        exit(1)
        
    with open("rss_output.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
        
    logger.info(f"Success: {output['total_articles']} articles saved to rss_output.json")

if __name__ == "__main__":
    main()
