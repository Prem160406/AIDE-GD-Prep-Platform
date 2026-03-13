# AIDE RSS Data Collection Pipeline
# pylint: disable=no-member
# VS Code: ignore linting warnings
import feedparser
import json

print("AIDE RSS Pipeline - Data Collection")

url = "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms"
feed = feedparser.parse(url)

articles = []
for entry in feed.entries[:5]:
    article = {
        "title": entry.title,
        "link": entry.link,
        "source": "TOI"
    }
    articles.append(article)

print(f"Collected {len(articles)} articles")

with open("rss_output.json", "w") as f:
    json.dump(articles, f, indent=2)

print("Saved rss_output.json")
print("Pipeline complete")
