#collector.py

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import datetime, timezone
from time import struct_time
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import feedparser

from config import (
    DEFAULT_FEED_LIMIT,
    MAX_ARTICLE_AGE_DAYS,
    RSS_FEEDS,
    RSSFeedEntry,
    SNIPPET_MIN_WORDS,
    USE_ARTICLE_AGE_FILTER,
)
from models import ArticleRecord, PipelineStats
from utils import (
    clean_html,
    clean_text,
    is_article_fresh,
    is_valid_http_url,
    parse_published_datetime,
    stable_article_id,
)

logger = logging.getLogger(__name__)

_TRACKING_QUERY_KEYS = frozenset(
    {
        "fbclid",
        "gclid",
        "igshid",
        "mc_cid",
        "mc_eid",
    }
)
_TRACKING_QUERY_PREFIXES = ("utm_",)


def collect_articles(
    feed_configs: Iterable[RSSFeedEntry] | None = None,
) -> tuple[list[ArticleRecord], PipelineStats]:
    raw_items: list[ArticleRecord] = []
    failed_count = 0

    feeds = list(feed_configs) if feed_configs is not None else list(RSS_FEEDS)

    for feed_config in feeds:
        try:
            feed_url, forced_source = resolve_feed_config(feed_config)
            raw_items.extend(collect_feed(feed_url, forced_source=forced_source))
        except Exception as exc:
            failed_count += 1
            logger.warning("Feed collection failed for %r: %s", feed_config, exc, exc_info=True)
            continue

    deduped_items = dedupe_articles(raw_items)
    prefiltered_items = prefilter_articles(deduped_items)

    stats = PipelineStats(
        raw_count=len(raw_items),
        deduped_count=len(deduped_items),
        prefiltered_count=len(prefiltered_items),
        fetched_count=0,
        scored_count=0,
        hard_filtered_count=0,
        final_count=0,
        failed_count=failed_count,
    )
    return prefiltered_items, stats


def collect_feed(feed_url: str, *, forced_source: str | None = None) -> list[ArticleRecord]:
    if not is_valid_http_url(feed_url):
        logger.warning("Skipping invalid feed URL: %s", feed_url)
        return []

    parsed = feedparser.parse(feed_url)
    entries = getattr(parsed, "entries", []) or []

    if getattr(parsed, "bozo", False):
        logger.warning(
            "Malformed feed detected for %s: %r",
            feed_url,
            getattr(parsed, "bozo_exception", None),
        )
        if not entries:
            return []

    status = getattr(parsed, "status", None)
    if isinstance(status, int) and status >= 400:
        logger.warning("Feed returned HTTP status %s for %s", status, feed_url)
        return []

    feed_title = forced_source or safe_clean_text(getattr(parsed.feed, "title", None), max_length=120)

    articles: list[ArticleRecord] = []
    for entry in entries[:DEFAULT_FEED_LIMIT]:
        article = normalize_entry(entry, source_hint=feed_title)
        if article is not None:
            articles.append(article)

    return articles


def normalize_entry(entry: Any, *, source_hint: str | None = None) -> ArticleRecord | None:
    try:
        title = safe_clean_text(first_present(entry, "title"), max_length=300)
        if not title:
            return None

        link = normalize_entry_link(first_present(entry, "link"))
        if not link:
            return None

        source = resolve_entry_source(entry, source_hint=source_hint) or "unknown"
        summary = select_entry_summary(entry)
        published_raw = select_entry_published_string(entry)
        topic = select_entry_category(entry)

        return ArticleRecord(
            article_id=stable_article_id(link, title),
            title=title,
            link=link,
            source=source,
            published=published_raw,
            summary=summary or None,
            body_text=None,
            topic=topic,
        )
    except Exception as exc:
        logger.debug("Failed to normalize feed entry: %s", exc, exc_info=True)
        return None


def dedupe_articles(items: list[ArticleRecord]) -> list[ArticleRecord]:
    seen_links: set[str] = set()
    seen_ids: set[str] = set()
    deduped: list[ArticleRecord] = []

    for item in items:
        normalized_link = canonicalize_url(item.link)

        if normalized_link in seen_links:
            continue
        if item.article_id in seen_ids:
            continue

        seen_links.add(normalized_link)
        seen_ids.add(item.article_id)
        deduped.append(item)

    return deduped


def prefilter_articles(items: list[ArticleRecord]) -> list[ArticleRecord]:
    filtered: list[ArticleRecord] = []

    for item in items:
        if get_prefilter_rejection_reason(item) is None:
            filtered.append(item)

    return filtered


def get_prefilter_rejection_reason(item: ArticleRecord) -> str | None:
    if not item.title:
        return "missing_title"

    if not is_valid_http_url(item.link):
        return "invalid_link"

    published_dt = parse_published_datetime(item.published)
    if USE_ARTICLE_AGE_FILTER and not is_article_fresh(published_dt, MAX_ARTICLE_AGE_DAYS):
        return "stale"

    if item.summary and len(item.summary.split()) < SNIPPET_MIN_WORDS:
        return "summary_too_short"

    return None


def resolve_feed_config(feed_config: RSSFeedEntry) -> tuple[str, str | None]:
    if isinstance(feed_config, str):
        url = feed_config.strip()
        if not is_valid_http_url(url):
            raise ValueError(f"Invalid feed URL: {feed_config!r}")
        return url, None

    url = feed_config.get("url")
    source = feed_config.get("source")

    if not isinstance(url, str) or not is_valid_http_url(url.strip()):
        raise ValueError(f"Invalid feed URL in feed config: {feed_config!r}")

    if source is not None and not isinstance(source, str):
        raise TypeError(
            f"feed_config['source'] must be a string if provided, got {type(source).__name__}"
        )

    cleaned_source = safe_clean_text(source, max_length=120) if isinstance(source, str) else ""
    return url.strip(), cleaned_source or None


def resolve_entry_source(entry: Any, *, source_hint: str | None = None) -> str | None:
    if source_hint:
        cleaned_hint = safe_clean_text(source_hint, max_length=120)
        if cleaned_hint:
            return cleaned_hint

    source_value = getattr(entry, "source", None)
    if isinstance(source_value, dict):
        for key in ("title", "value", "name"):
            cleaned = safe_clean_text(source_value.get(key), max_length=120)
            if cleaned:
                return cleaned

    for field_name in ("author",):
        cleaned = safe_clean_text(first_present(entry, field_name), max_length=120)
        if cleaned:
            return cleaned

    return None


def select_entry_summary(entry: Any) -> str:
    for field_name in ("summary", "description", "subtitle"):
        cleaned = safe_clean_html(first_present(entry, field_name), max_length=5000)
        if cleaned:
            return cleaned

    content_items = getattr(entry, "content", None)
    if isinstance(content_items, list):
        for item in content_items:
            if isinstance(item, dict):
                cleaned = safe_clean_html(item.get("value"), max_length=5000)
                if cleaned:
                    return cleaned

    return ""


def select_entry_published_string(entry: Any) -> str | None:
    for field_name in ("published", "updated", "created"):
        value = first_present(entry, field_name)
        if isinstance(value, str):
            cleaned = safe_clean_text(value, max_length=100)
            if cleaned:
                return cleaned
    return None


def select_entry_datetime(entry: Any) -> datetime | None:
    for field_name in ("published_parsed", "updated_parsed", "created_parsed"):
        value = getattr(entry, field_name, None)
        dt = parsed_struct_time_to_datetime(value)
        if dt is not None:
            return dt

    for field_name in ("published", "updated", "created"):
        value = first_present(entry, field_name)
        if isinstance(value, str):
            dt = parse_published_datetime(value)
            if dt is not None:
                return dt

    return None


def select_entry_category(entry: Any) -> str | None:
    tags = getattr(entry, "tags", None)
    if isinstance(tags, list):
        for tag in tags:
            for key in ("term", "label"):
                value = tag.get(key) if isinstance(tag, dict) else getattr(tag, key, None)
                cleaned = safe_clean_text(value, max_length=120)
                if cleaned:
                    return cleaned
    return None


def normalize_entry_link(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    cleaned = value.strip()
    if not cleaned or not is_valid_http_url(cleaned):
        return None

    return cleaned


def canonicalize_url(url: str) -> str:
    raw = url.strip()
    parts = urlsplit(raw)
    scheme = parts.scheme.lower()

    try:
        hostname = parts.hostname.lower() if parts.hostname else ""
        port = parts.port
    except ValueError:
        return raw.lower()

    if (scheme == "https" and port == 443) or (scheme == "http" and port == 80):
        netloc = hostname
    else:
        netloc = parts.netloc.lower()

    path = parts.path.rstrip("/") or "/"

    filtered_query_pairs: list[tuple[str, str]] = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        lowered = key.lower()
        if lowered in _TRACKING_QUERY_KEYS:
            continue
        if lowered.startswith(_TRACKING_QUERY_PREFIXES):
            continue
        filtered_query_pairs.append((key, value))

    query = urlencode(filtered_query_pairs, doseq=True)

    return urlunsplit((scheme, netloc, path, query, ""))


def parsed_struct_time_to_datetime(value: Any) -> datetime | None:
    if not isinstance(value, struct_time):
        return None

    try:
        return datetime(
            year=value.tm_year,
            month=value.tm_mon,
            day=value.tm_mday,
            hour=value.tm_hour,
            minute=value.tm_min,
            second=value.tm_sec,
            tzinfo=timezone.utc,
        )
    except (TypeError, ValueError):
        return None


def first_present(entry: Any, field_name: str) -> Any:
    value = getattr(entry, field_name, None)
    if value is not None:
        return value

    if isinstance(entry, dict):
        return entry.get(field_name)

    return None


def safe_clean_text(value: Any, *, max_length: int | None = None) -> str:
    if not isinstance(value, str):
        return ""
    try:
        return clean_text(value, max_length=max_length)
    except Exception as exc:
        logger.debug("safe_clean_text failed: %s", exc, exc_info=True)
        return ""


def safe_clean_html(value: Any, *, max_length: int | None = None) -> str:
    if not isinstance(value, str):
        return ""
    try:
        return clean_html(value, max_length=max_length)
    except Exception as exc:
        logger.debug("safe_clean_html failed: %s", exc, exc_info=True)
        return ""


__all__ = [
    "collect_articles",
    "collect_feed",
    "normalize_entry",
    "dedupe_articles",
    "prefilter_articles",
    "get_prefilter_rejection_reason",
    "resolve_feed_config",
    "resolve_entry_source",
    "select_entry_summary",
    "select_entry_published_string",
    "select_entry_datetime",
    "select_entry_category",
    "normalize_entry_link",
    "canonicalize_url",
    "parsed_struct_time_to_datetime",
    "first_present",
    "safe_clean_text",
    "safe_clean_html",
]