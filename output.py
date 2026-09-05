#output.py

from __future__ import annotations

import csv
import json
import logging
import os
from supabase import create_client
from pathlib import Path
from typing import Any, Iterable, Sequence

from config import DEFAULT_CSV_OUTPUT, DEFAULT_JSON_OUTPUT, PIPELINE_VERSION
from models import PipelineResultRow, PipelineStats, ScoredArticle
from utils import utc_now_iso

from dataclasses import asdict


logger = logging.getLogger(__name__)


class OutputError(RuntimeError):
    pass


def build_result_row(
    scored: ScoredArticle,
    *,
    created_at: str | None = None,
) -> PipelineResultRow:
    if not isinstance(scored, ScoredArticle):
        raise TypeError(f"scored must be a ScoredArticle, got {type(scored).__name__}")

    _ = created_at or utc_now_iso()

    return PipelineResultRow(
        article_id=scored.article_id,
        title=scored.title,
        topic_title=scored.topic_title,
        source=scored.source,
        published=scored.published,
        link=scored.link,
        weighted_score=scored.weighted_score,
        decision=scored.decision,
        summary=scored.summary,
        features=scored.features,
        evidence=scored.evidence,
        hard_filter_failed=scored.hard_filter_failed,
        hard_filter_rules_failed=scored.hard_filter_rules_failed,
        prompt_version=scored.prompt_version,
        feature_contributions=scored.feature_contributions,
    )


def build_result_rows(
    scored_articles: Iterable[ScoredArticle],
    *,
    created_at: str | None = None,
) -> list[PipelineResultRow]:
    timestamp = created_at or utc_now_iso()
    rows: list[PipelineResultRow] = []

    for scored in scored_articles:
        rows.append(build_result_row(scored, created_at=timestamp))

    return rows


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    return str(value)


def result_row_to_dict(row: PipelineResultRow) -> dict[str, Any]:
    if not isinstance(row, PipelineResultRow):
        raise TypeError(f"row must be a PipelineResultRow, got {type(row).__name__}")

    return {
        "article_id": row.article_id,
        "title": row.title,
        "topic_title": row.topic_title,
        "source": row.source,
        "published": row.published,
        "link": row.link,
        "weighted_score": row.weighted_score,
        "decision": row.decision,
        "summary": row.summary,
        "features": dict(row.features),
        "evidence": dict(row.evidence),
        "hard_filter_failed": row.hard_filter_failed,
        "hard_filter_rules_failed": list(row.hard_filter_rules_failed),
        "prompt_version": row.prompt_version,
        "feature_contributions": list(row.feature_contributions),
    }


def write_rows_to_json(
    rows: Sequence[PipelineResultRow],
    output_path: str | Path = DEFAULT_JSON_OUTPUT,
    *,
    stats: PipelineStats | None = None,
) -> Path:
    path = Path(output_path)

    for row in rows:
        if not isinstance(row, PipelineResultRow):
            raise TypeError(
                f"rows must contain only PipelineResultRow objects, got {type(row).__name__}"
            )

    if stats is not None and not isinstance(stats, PipelineStats):
        raise TypeError(f"stats must be a PipelineStats or None, got {type(stats).__name__}")

    payload: dict[str, Any] = {
        "pipeline_version": PIPELINE_VERSION,
        "created_at": utc_now_iso(),
        "count": len(rows),
        "rows": [result_row_to_dict(row) for row in rows],
    }

    if stats is not None:
        payload["stats"] = asdict(stats)

    _ensure_parent_dir(path)

    try:
        with path.open("w", encoding="utf-8") as handle:
            json.dump(
                payload,
                handle,
                ensure_ascii=False,
                indent=2,
                default=_json_default,
            )
            handle.write("\n")
    except OSError as exc:
        logger.error("Failed to write JSON output to %s: %s", path, exc)
        raise OutputError(f"Failed to write JSON output to {path}") from exc

    logger.info("Wrote JSON output to %s", path)
    return path


def write_rows_to_csv(
    rows: Sequence[PipelineResultRow],
    output_path: str | Path = DEFAULT_CSV_OUTPUT,
) -> Path:
    path = Path(output_path)

    for row in rows:
        if not isinstance(row, PipelineResultRow):
            raise TypeError(
                f"rows must contain only PipelineResultRow objects, got {type(row).__name__}"
            )

    _ensure_parent_dir(path)

    flat_rows = [result_row_to_dict(row) for row in rows]

    if flat_rows:
        fieldnames = list(flat_rows[0].keys())
        seen = set(fieldnames)

        for row in flat_rows[1:]:
            for key in row.keys():
                if key not in seen:
                    fieldnames.append(key)
                    seen.add(key)
    else:
        fieldnames = [
            "article_id",
            "title",
            "topic_title",
            "source",
            "published",
            "link",
            "weighted_score",
            "decision",
            "summary",
            "features",
            "evidence",
            "hard_filter_failed",
            "hard_filter_rules_failed",
            "prompt_version",
            "feature_contributions",
        ]

    try:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in flat_rows:
                csv_row = dict(row)
                if isinstance(csv_row.get("features"), dict):
                    csv_row["features"] = json.dumps(csv_row["features"], ensure_ascii=False)
                if isinstance(csv_row.get("evidence"), dict):
                    csv_row["evidence"] = json.dumps(csv_row["evidence"], ensure_ascii=False)
                if isinstance(csv_row.get("feature_contributions"), list):
                    csv_row["feature_contributions"] = json.dumps(
                        csv_row["feature_contributions"], ensure_ascii=False
                    )
                if isinstance(csv_row.get("hard_filter_rules_failed"), list):
                    csv_row["hard_filter_rules_failed"] = json.dumps(
                        csv_row["hard_filter_rules_failed"], ensure_ascii=False
                    )
                writer.writerow(csv_row)
    except OSError as exc:
        logger.error("Failed to write CSV output to %s: %s", path, exc)
        raise OutputError(f"Failed to write CSV output to {path}") from exc

    logger.info("Wrote CSV output to %s", path)
    return path

def push_rows_to_supabase(rows: Sequence[PipelineResultRow]) -> None:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        logger.warning("Supabase credentials not set — skipping DB push.")
        return

    supabase = create_client(url, key)
    pushed = 0
    skipped = 0

    for row in rows:
        if row.decision != "Suggest":
            skipped += 1
            continue

        try:
            supabase.table("topics").insert({
                "title": row.topic_title,
                "summary": row.summary,
                "source_url": row.link,
                "source_name": row.source,
                "pipeline_version": row.prompt_version,
                "weighted_score": row.weighted_score,
                "decision": row.decision,
                "published": row.published,
                "controversy": row.features.get("controversy"),
                "multiple_stakeholders": row.features.get("multiple_stakeholders"),
                "policy_relevance": row.features.get("policy_relevance"),
                "ethical_dimension": row.features.get("ethical_dimension"),
                "factual_freshness": row.features.get("factual_freshness"),
                "debate_balance": row.features.get("debate_balance"),
                "public_impact": row.features.get("public_impact"),
                "topic_clarity": row.features.get("topic_clarity"),
                "status": "active",
            }).execute()
            pushed += 1

        except Exception as exc:
            logger.error("Supabase insert failed for article_id %s: %s", row.article_id, exc)

    logger.info("Supabase push complete — %d inserted, %d skipped.", pushed, skipped)

def record_pipeline_run_telemetry(
    stats: PipelineStats | None,
    duration_seconds: float = 0.0,
    error_log: str | None = None,
) -> None:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        return

    try:
        supabase = create_client(url, key)
        payload = {
            "raw_count": stats.raw_count if stats else 0,
            "deduped_count": stats.deduped_count if stats else 0,
            "fetched_count": stats.fetched_count if stats else 0,
            "scored_count": stats.scored_count if stats else 0,
            "final_count": stats.final_count if stats else 0,
            "failed_count": stats.failed_count if stats else 0,
            "duration_seconds": round(duration_seconds, 2),
            "status": "failed" if error_log else "completed",
            "error_log": error_log,
        }
        supabase.table("pipeline_runs").insert(payload).execute()
        logger.info("Recorded pipeline run telemetry to Supabase.")
    except Exception as exc:
        logger.warning("Failed to record pipeline run telemetry: %s", exc)

def write_pipeline_outputs(
    rows: Sequence[PipelineResultRow],
    *,
    json_output_path: str | Path = DEFAULT_JSON_OUTPUT,
    csv_output_path: str | Path = DEFAULT_CSV_OUTPUT,
    stats: PipelineStats | None = None,
    duration_seconds: float = 0.0,
) -> tuple[Path, Path]:
    json_path = write_rows_to_json(rows, json_output_path, stats=stats)
    csv_path = write_rows_to_csv(rows, csv_output_path)
    push_rows_to_supabase(rows)
    record_pipeline_run_telemetry(stats, duration_seconds=duration_seconds)
    return json_path, csv_path


__all__ = [
    "OutputError",
    "build_result_row",
    "build_result_rows",
    "result_row_to_dict",
    "write_rows_to_json",
    "write_rows_to_csv",
    "push_rows_to_supabase",
    "record_pipeline_run_telemetry",
    "write_pipeline_outputs",
]