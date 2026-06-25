#config.py

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType
from typing import Final, Mapping
from urllib.parse import urlparse


APP_NAME: Final[str] = "AIDE"
PIPELINE_VERSION: Final[str] = "1.2.0"
PROMPT_VERSION: Final[str] = "2026-05-21-v3"


BASE_DIR: Final[Path] = Path(__file__).resolve().parent
OUTPUT_DIR: Final[Path] = BASE_DIR / "output"


FeedConfig = Mapping[str, str]
RSSFeedEntry = str | FeedConfig


RSS_FEEDS: Final[tuple[RSSFeedEntry, ...]] = (
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    {"url": "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms", "source": "TOI"},
    {"url": "https://www.thehindu.com/feeder/default.rss", "source": "The Hindu"},
    {"url": "https://indianexpress.com/feed/", "source": "Indian Express"},
    {"url": "https://www.livemint.com/rss/news", "source": "Mint"},
    {"url": "https://feeds.feedburner.com/ndtvnews-top-stories", "source": "NDTV"},
)


SCORING_CRITERIA: Final[tuple[str, ...]] = (
    "controversy",
    "multiple_stakeholders",
    "policy_relevance",
    "ethical_dimension",
    "factual_freshness",
    "debate_balance",
    "public_impact",
    "topic_clarity",
)


ALLOWED_SCORES: Final[frozenset[int]] = frozenset({0, 1, 3, 5})
VALID_LOG_LEVELS: Final[frozenset[str]] = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


DECISION_BANDS: Final[tuple[tuple[float, str], ...]] = (
    (0.80, "Suggest"),
    (0.60, "Borderline"),
    (0.40, "Background"),
    (0.00, "Drop"),
)


DEFAULT_FEED_LIMIT: Final[int] = 10
MAX_ARTICLE_AGE_DAYS: Final[int] = 7
USE_ARTICLE_AGE_FILTER: Final[bool] = True


SNIPPET_MIN_WORDS: Final[int] = 20
SUMMARY_CHAR_LIMIT: Final[int] = 2000
FETCH_BODY_CHAR_LIMIT: Final[int] = 9000
PROMPT_BODY_CHAR_LIMIT: Final[int] = 7000
MAX_PROMPT_CHARS: Final[int] = PROMPT_BODY_CHAR_LIMIT


MAX_INPUT_TOKENS: Final[int] = 6000
MAX_OUTPUT_TOKENS: Final[int] = 1200
PROMPT_OVERHEAD_BUFFER_TOKENS: Final[int] = 300
MAX_PROMPT_TOKENS_HEURISTIC: Final[int] = min(
    int(MAX_INPUT_TOKENS * 0.7),
    MAX_INPUT_TOKENS - MAX_OUTPUT_TOKENS - PROMPT_OVERHEAD_BUFFER_TOKENS,
)


FETCH_TIMEOUT_SECONDS: Final[int] = 20
LLM_TIMEOUT_SECONDS: Final[int] = 60
PIPELINE_TIMEOUT_SECONDS: Final[int] = 600


MAX_CONCURRENT_FETCH: Final[int] = 10
MAX_CONCURRENT_LLM: Final[int] = 2
MAX_CONCURRENT_SCORE: Final[int] = MAX_CONCURRENT_LLM
MAX_SAFE_CONCURRENT_FETCH: Final[int] = 50
MAX_SAFE_CONCURRENT_LLM: Final[int] = 5


LLM_PROVIDER: Final[str] = "gemini"
DEFAULT_MODEL_NAME: Final[str] = "gemini-3.1-flash-lite"
DEFAULT_API_VERSION: Final[str] = "v1beta"
LLM_TEMPERATURE: Final[float] = 0.1


RETRYABLE_STATUS_CODES: Final[frozenset[int]] = frozenset({429, 500, 502, 503})
MAX_LLM_RETRIES: Final[int] = 3
RETRY_BASE_DELAY_SECONDS: Final[float] = 2.0
RETRY_MAX_DELAY_SECONDS: Final[float] = 20.0
RETRY_JITTER: Final[bool] = True


MOCK_MODE: Final[bool] = False
DEFAULT_MOCK_BAND: Final[str] = "Borderline"


MIN_FETCH_BODY_WORDS: Final[int] = 80


HARD_FILTER_RULES: Final[tuple[dict[str, object], ...]] = (
    {
        "feature": "debate_balance",
        "condition": "equals",
        "value": "low",
        "label": "Weak debate balance",
    },
    {
        "feature": "factual_freshness",
        "condition": "equals",
        "value": "low",
        "label": "Not current enough",
    },
    {
        "feature": "topic_clarity",
        "condition": "equals",
        "value": "low",
        "label": "Topic framing too unclear",
    },
)


DEFAULT_JSON_OUTPUT: Final[Path] = OUTPUT_DIR / "aide_results.json"
DEFAULT_CSV_OUTPUT: Final[Path] = OUTPUT_DIR / "aide_results.csv"


LOG_LEVEL: Final[str] = "INFO"
MAX_FETCH_RETRIES: Final[int] = 3
FETCH_RETRY_BASE_DELAY_SECONDS: Final[float] = 1.5
MAX_RESPONSE_BYTES: Final[int] = 2_000_000


def _freeze_nested_criterion_definitions() -> MappingProxyType:
    raw: dict[str, dict[str, object]] = {
        "controversy": {
            "weight": 20,
            "description": "Whether the article contains a real point of tension, disagreement, contest, or opposable viewpoints that can spark discussion.",
            "anchors": {
                0: "No real disagreement or tension; mostly factual or one-sided.",
                1: "Some disagreement is implied, but weak or forced.",
                3: "Clear disagreement or contest exists with usable discussion angles.",
                5: "Strong, natural controversy with clearly discussable opposing positions.",
            },
        },
        "multiple_stakeholders": {
            "weight": 15,
            "description": "Whether multiple stakeholder groups are involved and affected in meaningfully different ways.",
            "anchors": {
                0: "No meaningful stakeholder contrast is visible.",
                1: "Only one clear stakeholder group is present.",
                3: "Two or more stakeholder groups with differing interests are visible.",
                5: "Several stakeholder groups with clearly distinct or conflicting interests are involved.",
            },
        },
        "policy_relevance": {
            "weight": 10,
            "description": "Whether the issue connects meaningfully to governance, regulation, institutional decisions, or public policy.",
            "anchors": {
                0: "No meaningful policy or governance angle is present.",
                1: "A weak or indirect policy angle exists.",
                3: "A clear policy, legal, or governance angle is present.",
                5: "Policy or institutional relevance is central to the issue.",
            },
        },
        "ethical_dimension": {
            "weight": 10,
            "description": "Whether the topic raises questions of fairness, responsibility, rights, harm, justice, or moral trade-offs.",
            "anchors": {
                0: "No meaningful ethical dimension is visible.",
                1: "A weak ethical angle is implied.",
                3: "A clear ethical concern or moral tension is present.",
                5: "Ethical conflict is central and strongly shapes the discussion.",
            },
        },
        "factual_freshness": {
            "weight": 15,
            "description": "How current, timely, and presently relevant the article appears for discussion.",
            "anchors": {
                0: "Stale, outdated, or weakly tied to current discussion.",
                1: "Somewhat current, but momentum or immediacy is limited.",
                3: "Clearly current and relevant to present affairs.",
                5: "Highly current, actively relevant, and strongly tied to an ongoing issue.",
            },
        },
        "debate_balance": {
            "weight": 15,
            "description": "Whether the topic supports a balanced discussion with more than one reasonable side or argument path.",
            "anchors": {
                0: "Too one-sided, too shallow, or mostly factual-only.",
                1: "Some room for debate exists, but one side clearly dominates.",
                3: "Two or more reasonable sides can be discussed meaningfully.",
                5: "Strong balance with multiple reasonable, discussable sides or trade-offs.",
            },
        },
        "public_impact": {
            "weight": 10,
            "description": "How strongly the issue affects the public, society, economy, institutions, or daily life.",
            "anchors": {
                0: "Little or no broader public effect.",
                1: "Limited effect on a small group or niche context.",
                3: "Clear effect on an important public area or group.",
                5: "Broad and meaningful effect on society, systems, or daily life.",
            },
        },
        "topic_clarity": {
            "weight": 5,
            "description": "How easily the article can be converted into a clear, concise, and usable GD topic title.",
            "anchors": {
                0: "Cannot be framed into a clear GD topic.",
                1: "Topic exists but is awkward, vague, or unclear.",
                3: "Can be framed into a usable GD topic with some cleanup.",
                5: "Easily becomes a sharp, direct, and understandable GD topic.",
            },
        },
    }
    return MappingProxyType(
        {
            criterion: MappingProxyType(
                {
                    "weight": definition["weight"],
                    "description": definition["description"],
                    "anchors": MappingProxyType(definition["anchors"]),
                }
            )
            for criterion, definition in raw.items()
        }
    )


CRITERION_DEFINITIONS: Final[MappingProxyType] = _freeze_nested_criterion_definitions()


WEIGHTS: Final[MappingProxyType] = MappingProxyType(
    {criterion: int(CRITERION_DEFINITIONS[criterion]["weight"]) for criterion in SCORING_CRITERIA}
)


FEATURE_WEIGHTS: Final[MappingProxyType] = WEIGHTS


def _validate_feed_url(feed_url: str) -> None:
    if not feed_url or not feed_url.strip():
        raise ValueError("RSS feed URL cannot be empty.")
    parsed = urlparse(feed_url)
    if parsed.scheme.lower() != "https":
        raise ValueError(f"RSS feed must use HTTPS: {feed_url}")
    if not parsed.netloc:
        raise ValueError(f"RSS feed must include a valid host: {feed_url}")


def _extract_feed_url(feed_entry: RSSFeedEntry) -> str:
    if isinstance(feed_entry, str):
        return feed_entry.strip()
    if isinstance(feed_entry, Mapping):
        raw_url = feed_entry.get("url")
        if not isinstance(raw_url, str) or not raw_url.strip():
            raise ValueError(f"Feed mapping must contain a non-empty 'url': {feed_entry}")
        return raw_url.strip()
    raise TypeError(f"Invalid RSS feed entry type: {type(feed_entry).__name__}")


def validate_config() -> None:
    if not RSS_FEEDS:
        raise ValueError("RSS_FEEDS cannot be empty.")
    if not SCORING_CRITERIA:
        raise ValueError("SCORING_CRITERIA cannot be empty.")
    if set(SCORING_CRITERIA) != set(CRITERION_DEFINITIONS.keys()):
        raise ValueError("CRITERION_DEFINITIONS keys do not match SCORING_CRITERIA.")
    if set(SCORING_CRITERIA) != set(WEIGHTS.keys()):
        raise ValueError("WEIGHTS keys do not match SCORING_CRITERIA.")
    if sum(WEIGHTS.values()) != 100:
        raise ValueError(f"WEIGHTS must sum to 100, got {sum(WEIGHTS.values())}.")
    if DEFAULT_MOCK_BAND not in {"Suggest", "Borderline", "Background", "Drop"}:
        raise ValueError(f"Invalid DEFAULT_MOCK_BAND: {DEFAULT_MOCK_BAND}")
    if LOG_LEVEL not in VALID_LOG_LEVELS:
        raise ValueError(f"LOG_LEVEL must be one of {sorted(VALID_LOG_LEVELS)}, got {LOG_LEVEL}")
    if MAX_CONCURRENT_FETCH < 1 or MAX_CONCURRENT_FETCH > MAX_SAFE_CONCURRENT_FETCH:
        raise ValueError(f"MAX_CONCURRENT_FETCH must be between 1 and {MAX_SAFE_CONCURRENT_FETCH}, got {MAX_CONCURRENT_FETCH}")
    if MAX_CONCURRENT_LLM < 1 or MAX_CONCURRENT_LLM > MAX_SAFE_CONCURRENT_LLM:
        raise ValueError(f"MAX_CONCURRENT_LLM must be between 1 and {MAX_SAFE_CONCURRENT_LLM}, got {MAX_CONCURRENT_LLM}")
    if not (0.0 <= LLM_TEMPERATURE <= 2.0):
        raise ValueError(f"LLM_TEMPERATURE must be between 0.0 and 2.0, got {LLM_TEMPERATURE}")
    if FETCH_BODY_CHAR_LIMIT < PROMPT_BODY_CHAR_LIMIT:
        raise ValueError("FETCH_BODY_CHAR_LIMIT should be >= PROMPT_BODY_CHAR_LIMIT.")
    if PROMPT_BODY_CHAR_LIMIT // 4 >= MAX_INPUT_TOKENS:
        raise ValueError("PROMPT_BODY_CHAR_LIMIT is too high relative to MAX_INPUT_TOKENS.")
    if MAX_OUTPUT_TOKENS < 200:
        raise ValueError("MAX_OUTPUT_TOKENS is unrealistically low for structured JSON output.")
    if FETCH_TIMEOUT_SECONDS <= 0 or LLM_TIMEOUT_SECONDS <= 0 or PIPELINE_TIMEOUT_SECONDS <= 0:
        raise ValueError("All timeout values must be > 0.")
    if PIPELINE_TIMEOUT_SECONDS < (FETCH_TIMEOUT_SECONDS + LLM_TIMEOUT_SECONDS):
        raise ValueError("PIPELINE_TIMEOUT_SECONDS must be at least the combined fetch and LLM timeout budget.")
    if RETRY_BASE_DELAY_SECONDS <= 0:
        raise ValueError("RETRY_BASE_DELAY_SECONDS must be > 0.")
    if RETRY_MAX_DELAY_SECONDS < RETRY_BASE_DELAY_SECONDS:
        raise ValueError("RETRY_MAX_DELAY_SECONDS must be >= RETRY_BASE_DELAY_SECONDS.")
    thresholds = [threshold for threshold, _ in DECISION_BANDS]
    labels = [label for _, label in DECISION_BANDS]
    if thresholds != sorted(thresholds, reverse=True):
        raise ValueError(f"DECISION_BANDS thresholds must be in descending order, got {thresholds}")
    if len(labels) != len(set(labels)):
        raise ValueError(f"DECISION_BANDS labels must be unique, got {labels}")
    if thresholds[-1] != 0:
        raise ValueError("Lowest DECISION_BANDS threshold must be 0.")
    seen_feeds: set[str] = set()
    for feed_entry in RSS_FEEDS:
        feed_url = _extract_feed_url(feed_entry)
        _validate_feed_url(feed_url)
        normalized = feed_url.lower()
        if normalized in seen_feeds:
            raise ValueError(f"Duplicate RSS feed detected: {feed_url}")
        seen_feeds.add(normalized)
    for criterion in SCORING_CRITERIA:
        definition = CRITERION_DEFINITIONS[criterion]
        weight = int(definition["weight"])
        anchors = definition["anchors"]
        if weight < 1 or weight > 40:
            raise ValueError(f"Weight for {criterion} must be between 1 and 40, got {weight}")
        if set(anchors.keys()) != set(ALLOWED_SCORES):
            raise ValueError(f"Anchors for {criterion} must exactly match ALLOWED_SCORES.")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


validate_config()


__all__ = [
    "APP_NAME",
    "PIPELINE_VERSION",
    "PROMPT_VERSION",
    "BASE_DIR",
    "OUTPUT_DIR",
    "FeedConfig",
    "RSSFeedEntry",
    "RSS_FEEDS",
    "SCORING_CRITERIA",
    "CRITERION_DEFINITIONS",
    "WEIGHTS",
    "FEATURE_WEIGHTS",
    "HARD_FILTER_RULES",
    "ALLOWED_SCORES",
    "VALID_LOG_LEVELS",
    "DECISION_BANDS",
    "DEFAULT_FEED_LIMIT",
    "MAX_ARTICLE_AGE_DAYS",
    "USE_ARTICLE_AGE_FILTER",
    "SNIPPET_MIN_WORDS",
    "SUMMARY_CHAR_LIMIT",
    "FETCH_BODY_CHAR_LIMIT",
    "PROMPT_BODY_CHAR_LIMIT",
    "MAX_PROMPT_CHARS",
    "MAX_PROMPT_TOKENS_HEURISTIC",
    "MAX_INPUT_TOKENS",
    "MAX_OUTPUT_TOKENS",
    "FETCH_TIMEOUT_SECONDS",
    "LLM_TIMEOUT_SECONDS",
    "PIPELINE_TIMEOUT_SECONDS",
    "MAX_CONCURRENT_FETCH",
    "MAX_CONCURRENT_LLM",
    "MAX_CONCURRENT_SCORE",
    "MAX_SAFE_CONCURRENT_FETCH",
    "MAX_SAFE_CONCURRENT_LLM",
    "LLM_PROVIDER",
    "DEFAULT_MODEL_NAME",
    "DEFAULT_API_VERSION",
    "LLM_TEMPERATURE",
    "RETRYABLE_STATUS_CODES",
    "MAX_LLM_RETRIES",
    "RETRY_BASE_DELAY_SECONDS",
    "RETRY_MAX_DELAY_SECONDS",
    "RETRY_JITTER",
    "MOCK_MODE",
    "DEFAULT_MOCK_BAND",
    "DEFAULT_JSON_OUTPUT",
    "DEFAULT_CSV_OUTPUT",
    "LOG_LEVEL",
    "MAX_RESPONSE_BYTES",
    "MIN_FETCH_BODY_WORDS",
    "MAX_FETCH_RETRIES",
    "FETCH_RETRY_BASE_DELAY_SECONDS",
    "validate_config",
    "PROMPT_OVERHEAD_BUFFER_TOKENS",
]