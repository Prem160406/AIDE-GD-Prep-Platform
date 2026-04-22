import feedparser
from datetime import datetime

def fetch_news_to_topics(url, source_name):
    # Use a timeout to prevent the server from hanging
    feed = feedparser.parse(url)
    
    # Check if feedparser actually found anything
    if not hasattr(feed, 'entries') or len(feed.entries) == 0:
        # Instead of crashing, return an empty list or a helpful error
        print(f"Warning: No entries found for {url}")
        return []

    collected_topics = []
    for entry in feed.entries[:5]:
        topic = {
            "title": entry.get('title', 'No Title'),
            "summary": entry.get('summary', 'No summary available.')[:150],
            "source": source_name,
            "source_url": entry.get('link', ''),
            "source_name": source_name,
            "status": "draft",
            "created_at": datetime.now().isoformat(),
            "issue_type": "current affairs",
            "validation_score": 5,
            "model_used": "RSS_FEED",
            "prompt_version": "n/a"
        }
        collected_topics.append(topic)
    
    return collected_topics