import feedparser
from datetime import datetime

def fetch_hr_trends(url, source_name):
    """
    Fetches job market trends or interview tips from a career RSS feed.
    """
    feed = feedparser.parse(url)
    
    # Safety Check: If the feed is empty or broken
    if not hasattr(feed, 'entries') or len(feed.entries) == 0:
        print(f"Warning: No HR entries found for {url}")
        return []

    collected_topics = []
    
    # We only take the top 5 to keep the "Drafts" list manageable
    for entry in feed.entries[:5]:
        topic = {
            "title": entry.get('title', 'Upcoming Job Trend'),
            "summary": entry.get('summary', 'Read more about this career insight.')[:150],
            "source": source_name,
            "source_url": entry.get('link', ''),
            "source_name": source_name,
            "status": "draft", # New items are always drafts for Gopal to approve
            "created_at": datetime.now().isoformat(),
            "issue_type": "Career Trend", # Specifically labeled for your HR project
            "validation_score": 7, 
            "model_used": "RSS_FEED_PARSER",
            "prompt_version": "n/a"
        }
        collected_topics.append(topic)
    
    return collected_topics