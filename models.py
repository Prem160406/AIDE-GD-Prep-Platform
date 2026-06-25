#models.py

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Mapping


def _require_non_empty_string(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string, got {type(value).__name__}")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty")
    return cleaned


def _optional_clean_string(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"Expected str | None, got {type(value).__name__}")
    cleaned = value.strip()
    return cleaned or None


def _freeze_string_map(data: Mapping[str, str], field_name: str) -> dict[str, str]:
    if not isinstance(data, Mapping):
        raise TypeError(f"{field_name} must be a mapping, got {type(data).__name__}")
    normalized: dict[str, str] = {}
    for key, value in data.items():
        if not isinstance(key, str):
            raise TypeError(f"{field_name} keys must be strings, got {type(key).__name__}")
        normalized[key] = _require_non_empty_string(value, f"{field_name}[{key!r}]")
    return normalized


def _freeze_feature_map(data: Mapping[str, bool | str], field_name: str) -> dict[str, bool | str]:
    if not isinstance(data, Mapping):
        raise TypeError(f"{field_name} must be a mapping, got {type(data).__name__}")
    normalized: dict[str, bool | str] = {}
    for key, value in data.items():
        if not isinstance(key, str):
            raise TypeError(f"{field_name} keys must be strings, got {type(key).__name__}")
        if not isinstance(value, (bool, str)):
            raise TypeError(f"{field_name}[{key!r}] must be bool | str, got {type(value).__name__}")
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                raise ValueError(f"{field_name}[{key!r}] cannot be empty")
            normalized[key] = cleaned
        else:
            normalized[key] = value
    return normalized


@dataclass(slots=True)
class ArticleRecord:
    article_id: str
    title: str
    link: str
    source: str
    published: str | None = None
    summary: str | None = None
    body_text: str | None = None
    topic: str | None = None

    def __post_init__(self) -> None:
        self.article_id = _require_non_empty_string(self.article_id, "article_id")
        self.title = _require_non_empty_string(self.title, "title")
        self.link = _require_non_empty_string(self.link, "link")
        self.source = _require_non_empty_string(self.source, "source")
        self.published = _optional_clean_string(self.published)
        self.summary = _optional_clean_string(self.summary)
        self.body_text = _optional_clean_string(self.body_text)
        self.topic = _optional_clean_string(self.topic)


@dataclass(slots=True, frozen=True)
class LLMFeaturePayload:
    article_title: str
    proposed_gd_topic: str
    features: Mapping[str, bool | str]
    evidence: Mapping[str, str]
    prompt_version: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "article_title", _require_non_empty_string(self.article_title, "article_title"))
        object.__setattr__(self, "proposed_gd_topic", _require_non_empty_string(self.proposed_gd_topic, "proposed_gd_topic"))
        object.__setattr__(self, "prompt_version", _require_non_empty_string(self.prompt_version, "prompt_version"))
        object.__setattr__(self, "features", _freeze_feature_map(self.features, "features"))
        object.__setattr__(self, "evidence", _freeze_string_map(self.evidence, "evidence"))


@dataclass(slots=True, frozen=True)
class LLMStructuredResponse:
    provider: str
    model: str
    payload: LLMFeaturePayload
    raw_text: str
    raw_response_hash: str
    prompt_tokens_est: int
    output_tokens_est: int
    finish_reason: str
    request_id: str | None = None
    latency_ms: int | None = None
    retry_count: int = 0
    validation_flags: tuple[str, ...] = ()
    injection_risk_level: str = "low"

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider", _require_non_empty_string(self.provider, "provider"))
        object.__setattr__(self, "model", _require_non_empty_string(self.model, "model"))
        object.__setattr__(self, "raw_text", _require_non_empty_string(self.raw_text, "raw_text"))
        object.__setattr__(self, "raw_response_hash", _require_non_empty_string(self.raw_response_hash, "raw_response_hash"))
        object.__setattr__(self, "finish_reason", _require_non_empty_string(self.finish_reason, "finish_reason"))
        object.__setattr__(self, "request_id", _optional_clean_string(self.request_id))
        object.__setattr__(self, "injection_risk_level", _require_non_empty_string(self.injection_risk_level, "injection_risk_level"))

        for field_name in ("prompt_tokens_est", "output_tokens_est", "retry_count"):
            value = getattr(self, field_name)
            if not isinstance(value, int):
                raise TypeError(f"{field_name} must be int, got {type(value).__name__}")
            if value < 0:
                raise ValueError(f"{field_name} cannot be negative")

        if self.latency_ms is not None:
            if not isinstance(self.latency_ms, int):
                raise TypeError(f"latency_ms must be int | None, got {type(self.latency_ms).__name__}")
            if self.latency_ms < 0:
                raise ValueError("latency_ms cannot be negative")

        if not isinstance(self.validation_flags, tuple):
            raise TypeError(f"validation_flags must be tuple[str, ...], got {type(self.validation_flags).__name__}")
        for flag in self.validation_flags:
            _require_non_empty_string(flag, "validation_flags item")


@dataclass(slots=True, frozen=True)
class ScoredArticle:
    article_id: str
    title: str
    topic_title: str
    source: str
    link: str
    published: str | None
    summary: str
    weighted_score: float
    decision: str
    features: Mapping[str, bool | str]
    evidence: Mapping[str, str]
    hard_filter_failed: bool = False
    hard_filter_rules_failed: tuple[str, ...] = ()
    prompt_version: str = ""
    feature_contributions: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "article_id", _require_non_empty_string(self.article_id, "article_id"))
        object.__setattr__(self, "title", _require_non_empty_string(self.title, "title"))
        object.__setattr__(self, "topic_title", _require_non_empty_string(self.topic_title, "topic_title"))
        object.__setattr__(self, "source", _require_non_empty_string(self.source, "source"))
        object.__setattr__(self, "link", _require_non_empty_string(self.link, "link"))
        object.__setattr__(self, "summary", _require_non_empty_string(self.summary, "summary"))
        object.__setattr__(self, "decision", _require_non_empty_string(self.decision, "decision"))
        object.__setattr__(self, "prompt_version", _optional_clean_string(self.prompt_version) or "")
        if self.published is not None:
            object.__setattr__(self, "published", _optional_clean_string(self.published))
        if not isinstance(self.weighted_score, (int, float)):
            raise TypeError(f"weighted_score must be numeric, got {type(self.weighted_score).__name__}")
        weighted_score = float(self.weighted_score)
        if not (0.0 <= weighted_score <= 1.0):
            raise ValueError(f"weighted_score must be between 0 and 1, got {weighted_score}")
        object.__setattr__(self, "weighted_score", weighted_score)
        object.__setattr__(self, "features", _freeze_feature_map(self.features, "features"))
        object.__setattr__(self, "evidence", _freeze_string_map(self.evidence, "evidence"))
        if not isinstance(self.hard_filter_rules_failed, tuple):
            raise TypeError(f"hard_filter_rules_failed must be tuple[str, ...], got {type(self.hard_filter_rules_failed).__name__}")
        for rule in self.hard_filter_rules_failed:
            _require_non_empty_string(rule, "hard_filter_rules_failed item")
        if not isinstance(self.feature_contributions, list):
            raise TypeError(f"feature_contributions must be list[dict[str, Any]], got {type(self.feature_contributions).__name__}")
        if self.hard_filter_failed and not self.hard_filter_rules_failed:
            raise ValueError("hard_filter_rules_failed is required when hard_filter_failed is True")
        if not self.hard_filter_failed and self.hard_filter_rules_failed:
            raise ValueError("hard_filter_rules_failed must be empty when hard_filter_failed is False")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class PipelineStats:
    raw_count: int
    deduped_count: int
    prefiltered_count: int
    fetched_count: int
    scored_count: int
    hard_filtered_count: int
    final_count: int
    failed_count: int = 0

    def __post_init__(self) -> None:
        numeric_fields = (
            "raw_count", "deduped_count", "prefiltered_count", "fetched_count",
            "scored_count", "hard_filtered_count", "final_count", "failed_count",
        )
        for field_name in numeric_fields:
            value = getattr(self, field_name)
            if not isinstance(value, int):
                raise TypeError(f"{field_name} must be int, got {type(value).__name__}")
            if value < 0:
                raise ValueError(f"{field_name} cannot be negative, got {value}")
        if self.deduped_count > self.raw_count:
            raise ValueError("deduped_count cannot exceed raw_count")
        if self.prefiltered_count > self.deduped_count:
            raise ValueError("prefiltered_count cannot exceed deduped_count")
        if self.fetched_count > self.prefiltered_count:
            raise ValueError("fetched_count cannot exceed prefiltered_count")
        if self.scored_count > self.fetched_count:
            raise ValueError("scored_count cannot exceed fetched_count")
        if self.hard_filtered_count > self.scored_count:
            raise ValueError("hard_filtered_count cannot exceed scored_count")
        if self.final_count > self.scored_count:
            raise ValueError("final_count cannot exceed scored_count")
        if self.final_count + self.hard_filtered_count != self.scored_count:
            raise ValueError("final_count + hard_filtered_count must equal scored_count")

    def to_dict(self) -> dict[str, int]:
        return {
            "raw_count": self.raw_count,
            "deduped_count": self.deduped_count,
            "prefiltered_count": self.prefiltered_count,
            "fetched_count": self.fetched_count,
            "scored_count": self.scored_count,
            "hard_filtered_count": self.hard_filtered_count,
            "final_count": self.final_count,
            "failed_count": self.failed_count,
        }


@dataclass(slots=True, frozen=True)
class PipelineResultRow:
    article_id: str
    title: str
    topic_title: str
    source: str
    published: str | None
    link: str
    weighted_score: float
    decision: str
    summary: str
    features: Mapping[str, bool | str] = field(default_factory=dict)
    evidence: Mapping[str, str] = field(default_factory=dict)
    hard_filter_failed: bool = False
    hard_filter_rules_failed: tuple[str, ...] = ()
    prompt_version: str = ""
    feature_contributions: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "article_id", _require_non_empty_string(self.article_id, "article_id"))
        object.__setattr__(self, "title", _require_non_empty_string(self.title, "title"))
        object.__setattr__(self, "topic_title", _require_non_empty_string(self.topic_title, "topic_title"))
        object.__setattr__(self, "source", _require_non_empty_string(self.source, "source"))
        object.__setattr__(self, "link", _require_non_empty_string(self.link, "link"))
        object.__setattr__(self, "summary", _require_non_empty_string(self.summary, "summary"))
        object.__setattr__(self, "decision", _require_non_empty_string(self.decision, "decision"))
        object.__setattr__(self, "published", _optional_clean_string(self.published))
        object.__setattr__(self, "prompt_version", _optional_clean_string(self.prompt_version) or "")
        if not isinstance(self.weighted_score, (int, float)):
            raise TypeError(f"weighted_score must be numeric, got {type(self.weighted_score).__name__}")
        weighted_score = float(self.weighted_score)
        if not (0.0 <= weighted_score <= 1.0):
            raise ValueError(f"weighted_score must be between 0 and 1, got {weighted_score}")
        object.__setattr__(self, "weighted_score", weighted_score)
        object.__setattr__(self, "features", _freeze_feature_map(self.features, "features"))
        object.__setattr__(self, "evidence", _freeze_string_map(self.evidence, "evidence"))
        if not isinstance(self.hard_filter_rules_failed, tuple):
            raise TypeError(f"hard_filter_rules_failed must be tuple[str, ...], got {type(self.hard_filter_rules_failed).__name__}")
        for rule in self.hard_filter_rules_failed:
            _require_non_empty_string(rule, "hard_filter_rules_failed item")
        if not isinstance(self.feature_contributions, list):
            raise TypeError(f"feature_contributions must be list[dict[str, Any]], got {type(self.feature_contributions).__name__}")
        if self.hard_filter_failed and not self.hard_filter_rules_failed:
            raise ValueError("hard_filter_rules_failed is required when hard_filter_failed is True")
        if not self.hard_filter_failed and self.hard_filter_rules_failed:
            raise ValueError("hard_filter_rules_failed must be empty when hard_filter_failed is False")


__all__ = [
    "ArticleRecord",
    "LLMFeaturePayload",
    "LLMStructuredResponse",
    "ScoredArticle",
    "PipelineStats",
    "PipelineResultRow",
]