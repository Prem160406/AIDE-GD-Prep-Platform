# __main__.py

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timezone

from supabase import create_client

from config import DEFAULT_CSV_OUTPUT, DEFAULT_FEED_LIMIT, DEFAULT_JSON_OUTPUT, LOG_LEVEL
from pipeline import PipelineError, run_pipeline

from dotenv import load_dotenv
load_dotenv(override=True)

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aide",
        description="Run the AIDE GD-topic scoring pipeline.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--feed-limit",
        type=int,
        default=DEFAULT_FEED_LIMIT,
        help="Maximum number of configured feeds to process.",
    )
    parser.add_argument(
        "--json-output",
        type=str,
        default=str(DEFAULT_JSON_OUTPUT),
        help="Path for JSON output.",
    )
    parser.add_argument(
        "--csv-output",
        type=str,
        default=str(DEFAULT_CSV_OUTPUT),
        help="Path for CSV output.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default=LOG_LEVEL,
        help="Logging level.",
    )
    parser.add_argument(
        "--listen",
        action="store_true",
        help="Run in continuous background job listener mode, processing pipeline_jobs from Supabase.",
    )
    return parser


def _configure_logging(log_level: str) -> None:
    level_name = str(log_level).upper().strip()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def process_pending_jobs(feed_limit: int, json_path: str, csv_path: str) -> bool:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        return False

    try:
        supabase = create_client(url, key)
        response = (
            supabase.table("pipeline_jobs")
            .select("*")
            .eq("status", "pending")
            .order("created_at", desc=False)
            .limit(1)
            .execute()
        )
        jobs = response.data or []
        if not jobs:
            return False

        job = jobs[0]
        job_id = job["id"]
        logger.info("Found pending job #%s. Marking status=running...", job_id)

        supabase.table("pipeline_jobs").update({"status": "running"}).eq("id", job_id).execute()

        try:
            rows, stats = run_pipeline(
                feed_limit=feed_limit,
                json_output_path=json_path,
                csv_output_path=csv_path,
            )
            supabase.table("pipeline_jobs").update({
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", job_id).execute()
            logger.info("Job #%s completed successfully.", job_id)
            return True

        except Exception as exc:
            logger.error("Job #%s failed: %s", job_id, exc)
            supabase.table("pipeline_jobs").update({
                "status": "failed",
                "error_message": str(exc),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", job_id).execute()
            return True

    except Exception as exc:
        logger.warning("Job queue check encountered error: %s", exc)
        return False


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    _configure_logging(args.log_level)

    if args.listen:
        logger.info("AIDE Worker started in continuous job listener mode. Press Ctrl+C to stop.")
        while True:
            try:
                processed = process_pending_jobs(args.feed_limit, args.json_output, args.csv_output)
                if not processed:
                    time.sleep(5)
            except KeyboardInterrupt:
                logger.info("Listener stopped by user.")
                return 0
            except Exception as exc:
                logger.error("Worker error: %s", exc)
                time.sleep(5)

    # Standard one-shot run (also checks pending jobs)
    process_pending_jobs(args.feed_limit, args.json_output, args.csv_output)

    try:
        rows, stats = run_pipeline(
            feed_limit=args.feed_limit,
            json_output_path=args.json_output,
            csv_output_path=args.csv_output,
        )
    except PipelineError as exc:
        logger.error("Pipeline failed: %s", exc)
        return 1
    except Exception:
        logger.exception("Unexpected fatal error")
        return 1

    logger.info(
        "AIDE pipeline finished successfully: rows=%s final_count=%s failed_count=%s",
        len(rows),
        stats.final_count,
        stats.failed_count,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))