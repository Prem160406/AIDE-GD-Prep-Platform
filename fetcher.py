#fetcher.py

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import replace

import httpx

from config import (
    FETCH_BODY_CHAR_LIMIT,
    FETCH_RETRY_BASE_DELAY_SECONDS,
    FETCH_TIMEOUT_SECONDS,
    MAX_CONCURRENT_FETCH,
    MAX_FETCH_RETRIES,
    MAX_RESPONSE_BYTES,
    MIN_FETCH_BODY_WORDS,
    RETRYABLE_STATUS_CODES,
    RETRY_JITTER,
)
from models import ArticleRecord
from utils import extract_main_text


logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


async def fetch_articles(articles: list[ArticleRecord]) -> list[ArticleRecord]:
    if not articles:
        return []

    timeout = httpx.Timeout(
        connect=FETCH_TIMEOUT_SECONDS,
        read=FETCH_TIMEOUT_SECONDS,
        write=FETCH_TIMEOUT_SECONDS,
        pool=FETCH_TIMEOUT_SECONDS,
    )
    limits = httpx.Limits(
        max_connections=MAX_CONCURRENT_FETCH,
        max_keepalive_connections=MAX_CONCURRENT_FETCH,
    )
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_FETCH)

    async with httpx.AsyncClient(
        timeout=timeout,
        limits=limits,
        headers=DEFAULT_HEADERS,
        follow_redirects=True,
    ) as client:
        tasks = [
            fetch_article_body(article, client=client, semaphore=semaphore)
            for article in articles
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    normalized_results: list[ArticleRecord] = []
    for article, result in zip(articles, results):
        if isinstance(result, Exception):
            logger.warning(
                "Unexpected fetch error for article_id=%s link=%s: %s",
                article.article_id,
                article.link,
                type(result).__name__,
                exc_info=True,
            )
            normalized_results.append(article)
        else:
            normalized_results.append(result)

    return normalized_results


async def fetch_article_body(
    article: ArticleRecord,
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
) -> ArticleRecord:
    async with semaphore:
        for attempt in range(MAX_FETCH_RETRIES):
            try:
                response = await client.get(article.link)
                status_code = response.status_code

                if status_code >= 400:
                    error_code = f"http_{status_code}"
                    if status_code not in RETRYABLE_STATUS_CODES:
                        logger.debug(
                            "Non-retryable HTTP status for article_id=%s status=%s",
                            article.article_id,
                            status_code,
                        )
                        return article
                else:
                    content_type = response.headers.get("content-type", "").lower()
                    is_html = "text/html" in content_type or "application/xhtml+xml" in content_type
                    if not is_html:
                        logger.debug(
                            "Skipping non-HTML response for article_id=%s content_type=%s",
                            article.article_id,
                            content_type or "unknown",
                        )
                        return article

                    content_length = response.headers.get("content-length")
                    if content_length:
                        try:
                            if int(content_length) > MAX_RESPONSE_BYTES:
                                logger.debug(
                                    "Response too large by header for article_id=%s bytes=%s",
                                    article.article_id,
                                    content_length,
                                )
                                return article
                        except ValueError:
                            logger.debug(
                                "Invalid content-length header for article_id=%s value=%r",
                                article.article_id,
                                content_length,
                            )

                    response_bytes = response.content
                    if len(response_bytes) > MAX_RESPONSE_BYTES:
                        logger.debug(
                            "Response too large after download for article_id=%s",
                            article.article_id,
                        )
                        return article

                    try:
                        response_text = response.text
                    except UnicodeDecodeError:
                        logger.debug(
                            "Decode error for article_id=%s link=%s",
                            article.article_id,
                            article.link,
                        )
                        return article

                    body_text = extract_main_text(
                        response_text,
                        char_limit=FETCH_BODY_CHAR_LIMIT,
                    )
                    if not body_text:
                        logger.debug(
                            "Empty extracted body for article_id=%s link=%s",
                            article.article_id,
                            article.link,
                        )
                        return article

                    if len(body_text.split()) < MIN_FETCH_BODY_WORDS:
                        logger.debug(
                            "Extracted body too short for article_id=%s words=%s",
                            article.article_id,
                            len(body_text.split()),
                        )
                        return article

                    return apply_fetched_body(article, body_text)

            except httpx.TimeoutException:
                error_code = "timeout"
            except httpx.HTTPError as exc:
                error_code = f"http_error:{type(exc).__name__}"
            except Exception as exc:
                logger.warning(
                    "Unexpected fetch failure for article_id=%s link=%s: %s",
                    article.article_id,
                    article.link,
                    exc,
                    exc_info=True,
                )
                return article

            if attempt == MAX_FETCH_RETRIES - 1:
                logger.debug(
                    "Fetch retries exhausted for article_id=%s error=%s",
                    article.article_id,
                    error_code,
                )
                return article

            delay = FETCH_RETRY_BASE_DELAY_SECONDS * (2 ** attempt)
            if RETRY_JITTER:
                delay *= random.uniform(0.8, 1.2)
            await asyncio.sleep(delay)

    return article


def apply_fetched_body(article: ArticleRecord, body_text: str) -> ArticleRecord:
    return replace(article, body_text=body_text)


__all__ = [
    "fetch_articles",
    "fetch_article_body",
    "apply_fetched_body",
]