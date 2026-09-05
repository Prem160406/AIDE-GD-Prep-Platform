#pipeline.py

from __future__ import annotations

import asyncio
import logging
import time

from collector import collect_articles
from config import (
    DEFAULT_CSV_OUTPUT,
    DEFAULT_FEED_LIMIT,
    DEFAULT_JSON_OUTPUT,
    MAX_CONCURRENT_FETCH,
    MAX_CONCURRENT_SCORE,
    PIPELINE_TIMEOUT_SECONDS,
    RSS_FEEDS,
)
from fetcher import fetch_articles
from models import ArticleRecord, PipelineResultRow, PipelineStats, ScoredArticle
from output import build_result_rows, write_pipeline_outputs
from scorer import ScoringError, score_article, validate_scoring_config


logger = logging.getLogger(__name__)


class PipelineError(RuntimeError):
    pass


def _coerce_feed_url(feed_item: object) -> str:
    if isinstance(feed_item, str):
        return feed_item
    if isinstance(feed_item, dict):
        url = feed_item.get("url")
        if isinstance(url, str) and url.strip():
            return url.strip()
    raise TypeError(f"Invalid RSS feed configuration item: {feed_item!r}")


def _get_feed_urls(limit: int | None = None) -> list[str]:
    urls = [_coerce_feed_url(item) for item in RSS_FEEDS]
    if limit is None:
        return urls
    return urls[:limit]


async def _fetch_articles_async(articles: list[ArticleRecord]) -> list[ArticleRecord]:
    return await fetch_articles(articles)


async def _run_fetch_stage(articles: list[ArticleRecord]) -> list[ArticleRecord]:
    try:
        return await asyncio.wait_for(
            _fetch_articles_async(articles),
            timeout=PIPELINE_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as exc:
        raise PipelineError("Fetch stage timed out") from exc


async def _score_one(
    article: ArticleRecord,
    semaphore: asyncio.Semaphore,
) -> tuple[ScoredArticle | None, Exception | None]:
    async with semaphore:
        await asyncio.sleep(4)
        try:
            scored = await asyncio.to_thread(score_article, article)
            return scored, None
        except ScoringError as exc:
            logger.warning(
                "Scoring failed for article_id=%s title=%r: %s",
                article.article_id,
                article.title,
                exc,
            )
            return None, exc
        except Exception as exc:
            logger.exception(
                "Unexpected scoring failure for article_id=%s title=%r",
                article.article_id,
                article.title,
            )
            return None, exc


async def _run_scoring_stage(
    articles: list[ArticleRecord],
) -> tuple[list[ScoredArticle], int]:
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCORE)
    tasks = [_score_one(article, semaphore) for article in articles]

    try:
        results = await asyncio.wait_for(
            asyncio.gather(*tasks),
            timeout=PIPELINE_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as exc:
        raise PipelineError("Scoring stage timed out") from exc

    successful: list[ScoredArticle] = []
    failed_count = 0

    for scored, error in results:
        if error is not None or scored is None:
            failed_count += 1
            continue
        successful.append(scored)

    return successful, failed_count


def _build_stats(
    *,
    raw_count: int,
    deduped_count: int,
    prefiltered_count: int,
    fetched_articles: list[ArticleRecord],
    scored_articles: list[ScoredArticle],
    failed_count: int,
) -> PipelineStats:
    scored_count = len(scored_articles)
    hard_filtered_count = sum(1 for scored in scored_articles if scored.hard_filter_failed)
    final_count = sum(1 for scored in scored_articles if not scored.hard_filter_failed)

    return PipelineStats(
        raw_count=raw_count,
        deduped_count=deduped_count,
        prefiltered_count=prefiltered_count,
        fetched_count=len(fetched_articles),
        scored_count=scored_count,
        hard_filtered_count=hard_filtered_count,
        final_count=final_count,
        failed_count=failed_count,
    )


async def run_pipeline_async(
    *,
    feed_limit: int = DEFAULT_FEED_LIMIT,
    json_output_path: str | None = None,
    csv_output_path: str | None = None,
) -> tuple[list[PipelineResultRow], PipelineStats]:
    if type(feed_limit) is not int or feed_limit <= 0:
        raise ValueError("feed_limit must be a positive int")

    start_time = time.perf_counter()
    validate_scoring_config()

    feed_urls = _get_feed_urls(feed_limit)

    logger.info("Starting collection from %s feeds", len(feed_urls))
    collected_articles, collection_stats = collect_articles(feed_urls)

    logger.info(
        "Collected articles: raw=%s deduped=%s prefiltered=%s",
        collection_stats.raw_count,
        collection_stats.deduped_count,
        collection_stats.prefiltered_count,
    )

    logger.info("Starting fetch stage for %s articles", len(collected_articles))
    fetched_articles = await _run_fetch_stage(collected_articles)

    scorable_articles = [
        article
        for article in fetched_articles
        if (getattr(article, "summary", None) and str(article.summary).strip())
        or (getattr(article, "body_text", None) and str(article.body_text).strip())
    ]

    skipped_empty_count = len(fetched_articles) - len(scorable_articles)
    if skipped_empty_count:
        logger.info(
            "Skipping %s fetched articles with empty summary and body_text",
            skipped_empty_count,
        )

    logger.info("Starting scoring stage for %s articles", len(scorable_articles))
    scored_articles, scoring_failed_count = await _run_scoring_stage(scorable_articles)

    rows = build_result_rows(scored_articles)

    stats = _build_stats(
        raw_count=collection_stats.raw_count,
        deduped_count=collection_stats.deduped_count,
        prefiltered_count=collection_stats.prefiltered_count,
        fetched_articles=fetched_articles,
        scored_articles=scored_articles,
        failed_count=collection_stats.failed_count + scoring_failed_count + skipped_empty_count,
    )

    json_path = json_output_path or str(DEFAULT_JSON_OUTPUT)
    csv_path = csv_output_path or str(DEFAULT_CSV_OUTPUT)

    duration_seconds = time.perf_counter() - start_time

    write_pipeline_outputs(
        rows,
        json_output_path=json_path,
        csv_output_path=csv_path,
        stats=stats,
        duration_seconds=duration_seconds,
    )

    logger.info(
        "Pipeline complete: scored=%s final=%s failed=%s",
        stats.scored_count,
        stats.final_count,
        stats.failed_count,
    )

    return rows, stats


def run_pipeline(
    *,
    feed_limit: int = DEFAULT_FEED_LIMIT,
    json_output_path: str | None = None,
    csv_output_path: str | None = None,
) -> tuple[list[PipelineResultRow], PipelineStats]:
    try:
        return asyncio.run(
            run_pipeline_async(
                feed_limit=feed_limit,
                json_output_path=json_output_path,
                csv_output_path=csv_output_path,
            )
        )
    except PipelineError:
        raise
    except Exception as exc:
        raise PipelineError(f"Pipeline execution failed: {exc}") from exc


__all__ = [
    "PipelineError",
    "run_pipeline_async",
    "run_pipeline",
]