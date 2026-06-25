#utils.py

from __future__ import annotations

import html
import re
import uuid
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Final
from urllib.parse import urlparse

from bs4 import BeautifulSoup


MAX_TEXT_LENGTH: Final[int] = 100_000
DEFAULT_EXTRACT_CHAR_LIMIT: Final[int] = 12_000
MIN_PARAGRAPH_WORDS: Final[int] = 20
MIN_ARTICLE_WORDS: Final[int] = 80


def _truncate(text: str, max_length: int | None) -> str:
    if max_length is None:
        return text
    if not isinstance(max_length, int) or max_length < 0:
        raise ValueError("max_length must be a non-negative int or None")
    return text[:max_length]


def normalize_whitespace(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"value must be a string, got {type(value).__name__}")
    return re.sub(r"\s+", " ", value).strip()


def clean_text(value: str, *, max_length: int | None = None) -> str:
    if not isinstance(value, str):
        raise TypeError(f"value must be a string, got {type(value).__name__}")

    text = normalize_whitespace(value)
    return _truncate(text, max_length)


def clean_html(value: str, *, max_length: int | None = None) -> str:
    if not isinstance(value, str):
        raise TypeError(f"value must be a string, got {type(value).__name__}")

    text = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
    text = normalize_whitespace(html.unescape(text))
    return _truncate(text, max_length)


def parse_published_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None

    if not isinstance(value, str):
        raise TypeError(
            f"published value must be a string or None, got {type(value).__name__}"
        )

    raw = value.strip()
    if not raw:
        return None

    try:
        dt = parsedate_to_datetime(raw)
    except (TypeError, ValueError, IndexError):
        return None

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def is_article_fresh(published_dt: datetime | None, max_age_days: int) -> bool:
    if published_dt is None:
        return True

    if not isinstance(published_dt, datetime):
        raise TypeError(
            f"published_dt must be a datetime or None, got {type(published_dt).__name__}"
        )

    if published_dt.tzinfo is None:
        published_dt = published_dt.replace(tzinfo=timezone.utc)
    else:
        published_dt = published_dt.astimezone(timezone.utc)

    if not isinstance(max_age_days, int) or max_age_days < 0:
        raise ValueError("max_age_days must be a non-negative int")

    max_age = timedelta(days=max_age_days)
    age = datetime.now(timezone.utc) - published_dt
    return age <= max_age


def stable_article_id(link: str, title: str) -> str:
    link_part = (link or "").strip().lower()
    title_part = (title or "").strip().lower()

    if link_part and title_part:
        seed = f"{link_part}::{title_part}"
    else:
        seed = link_part or title_part

    if not seed:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, "missing-article-identity"))

    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))


def extract_main_text(
    raw_html: str,
    *,
    char_limit: int = DEFAULT_EXTRACT_CHAR_LIMIT,
) -> str:
    if not isinstance(raw_html, str):
        raise TypeError(f"raw_html must be a string, got {type(raw_html).__name__}")

    if not isinstance(char_limit, int) or char_limit <= 0:
        raise ValueError("char_limit must be a positive int")

    soup = BeautifulSoup(raw_html, "html.parser")

    for tag in soup(
        ["script", "style", "noscript", "header", "footer", "svg", "form", "nav", "aside"]
    ):
        tag.decompose()

    selectors = (
        "article",
        "main",
        "[role='main']",
        ".article-body",
        ".story-body",
        ".post-content",
        ".entry-content",
        ".content",
    )

    for selector in selectors:
        blocks: list[str] = []

        for node in soup.select(selector):
            paragraphs = [
                clean_text(p.get_text(" ", strip=True), max_length=MAX_TEXT_LENGTH)
                for p in node.find_all("p")
            ]
            paragraphs = [p for p in paragraphs if len(p.split()) >= MIN_PARAGRAPH_WORDS]

            if paragraphs:
                candidate = "\n\n".join(paragraphs)
                if len(candidate.split()) >= MIN_ARTICLE_WORDS:
                    blocks.append(candidate)

        if blocks:
            best = max(blocks, key=len)
            return _truncate(best, char_limit)

    paragraphs = [
        clean_text(p.get_text(" ", strip=True), max_length=MAX_TEXT_LENGTH)
        for p in soup.find_all("p")
    ]
    paragraphs = [p for p in paragraphs if len(p.split()) >= MIN_PARAGRAPH_WORDS]

    if paragraphs:
        fallback = "\n\n".join(paragraphs)
        return _truncate(fallback, char_limit)

    return ""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_valid_http_url(value: str) -> bool:
    if not isinstance(value, str):
        return False

    raw = value.strip()
    if not raw:
        return False

    parsed = urlparse(raw)
    return parsed.scheme.lower() in {"http", "https"} and bool(parsed.netloc)


__all__ = [
    "MAX_TEXT_LENGTH",
    "DEFAULT_EXTRACT_CHAR_LIMIT",
    "MIN_PARAGRAPH_WORDS",
    "MIN_ARTICLE_WORDS",
    "normalize_whitespace",
    "clean_text",
    "clean_html",
    "parse_published_datetime",
    "is_article_fresh",
    "stable_article_id",
    "extract_main_text",
    "utc_now_iso",
    "is_valid_http_url",
]