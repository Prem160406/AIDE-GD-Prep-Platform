#__main__.py

from __future__ import annotations

import argparse
import logging
import sys

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
    return parser


def _configure_logging(log_level: str) -> None:
    level_name = str(log_level).upper().strip()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    _configure_logging(args.log_level)

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