#scorer.py

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache

from config import DECISION_BANDS, FEATURE_WEIGHTS, HARD_FILTER_RULES
from llm_client import (
    LLMClientError,
    LLMFeaturePayload,
    LLMStructuredResponse,
    generate_structured_response,
)
from models import ArticleRecord, ScoredArticle
from prompt import build_scoring_prompt

logger = logging.getLogger(__name__)


class ScoringError(RuntimeError):
    pass


class ScoringConfigError(RuntimeError):
    pass


_ENUM_RANK = {"low": 0, "medium": 1, "high": 2}
_ENUM_SCORE_MAP = {"low": 0.0, "medium": 0.5, "high": 1.0}
_ALLOWED_CONDITIONS = frozenset({"is_false", "equals", "enum_lte", "enum_lt"})


@dataclass(frozen=True)
class FeatureContribution:
    feature: str
    raw_value: bool | str
    normalized_score: float
    weight: float
    weighted_contribution: float


@cache
def validate_scoring_config() -> None:
    if not isinstance(FEATURE_WEIGHTS, Mapping) or not FEATURE_WEIGHTS:
        raise ScoringConfigError("FEATURE_WEIGHTS must be a non-empty dict")
    for key, weight in FEATURE_WEIGHTS.items():
        if not isinstance(key, str) or not key.strip():
            raise ScoringConfigError(f"FEATURE_WEIGHTS key must be a non-empty string, got {key!r}")
        if not isinstance(weight, (int, float)):
            raise ScoringConfigError(f"FEATURE_WEIGHTS[{key!r}] must be numeric, got {type(weight).__name__}")
        if weight <= 0:
            raise ScoringConfigError(f"FEATURE_WEIGHTS[{key!r}] must be positive, got {weight}")
    if not isinstance(DECISION_BANDS, (list, tuple)) or not DECISION_BANDS:
        raise ScoringConfigError("DECISION_BANDS must be a non-empty list")
    thresholds = []
    for i, band in enumerate(DECISION_BANDS):
        if not (isinstance(band, (list, tuple)) and len(band) == 2):
            raise ScoringConfigError(f"DECISION_BANDS[{i}] must be a (threshold, label) pair")
        threshold, label = band
        if not isinstance(threshold, (int, float)):
            raise ScoringConfigError(f"DECISION_BANDS[{i}] threshold must be numeric")
        if not isinstance(label, str) or not label.strip():
            raise ScoringConfigError(f"DECISION_BANDS[{i}] label must be a non-empty string")
        thresholds.append(threshold)
    if thresholds != sorted(thresholds, reverse=True):
        raise ScoringConfigError(f"DECISION_BANDS must be ordered by descending threshold, got {thresholds}")
    if not isinstance(HARD_FILTER_RULES, (list, tuple)):
        raise ScoringConfigError("HARD_FILTER_RULES must be a list")
    for i, rule in enumerate(HARD_FILTER_RULES):
        if not isinstance(rule, dict):
            raise ScoringConfigError(f"HARD_FILTER_RULES[{i}] must be a dict")
        for required_key in ("feature", "condition", "label"):
            if required_key not in rule:
                raise ScoringConfigError(f"HARD_FILTER_RULES[{i}] missing required key {required_key!r}")
        condition = rule["condition"]
        if condition not in _ALLOWED_CONDITIONS:
            raise ScoringConfigError(
                f"HARD_FILTER_RULES[{i}] condition {condition!r} not in {sorted(_ALLOWED_CONDITIONS)}"
            )
        if condition in ("equals", "enum_lte", "enum_lt") and "value" not in rule:
            raise ScoringConfigError(
                f"HARD_FILTER_RULES[{i}] with condition {condition!r} requires 'value' key"
            )
        if condition in ("enum_lte", "enum_lt"):
            threshold = str(rule["value"]).strip().lower()
            if threshold not in _ENUM_RANK:
                raise ScoringConfigError(
                    f"HARD_FILTER_RULES[{i}] {condition} value {rule['value']!r} must be one of {list(_ENUM_RANK)}"
                )


def _feature_to_score(key: str, value: bool | str) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, str):
        mapped = _ENUM_SCORE_MAP.get(value.strip().lower())
        if mapped is None:
            raise ScoringError(f"Unknown enum value for feature {key!r}: {value!r}")
        return mapped
    raise ScoringError(f"Unexpected feature type for {key!r}: {type(value).__name__}")


def _compute_weighted_score(features: dict[str, bool | str]) -> tuple[float, list[FeatureContribution]]:
    unknown_features = set(features) - set(FEATURE_WEIGHTS)
    if unknown_features:
        raise ScoringError(
            f"Features present in payload but not in FEATURE_WEIGHTS — possible schema drift: {sorted(unknown_features)}"
        )
    contributions: list[FeatureContribution] = []
    total_weighted = 0.0
    total_weight = 0.0
    for key, weight in FEATURE_WEIGHTS.items():
        if key not in features:
            raise ScoringError(f"Missing feature key in payload: {key!r}")
        normalized = _feature_to_score(key, features[key])
        weighted_contribution = normalized * weight
        total_weighted += weighted_contribution
        total_weight += weight
        contributions.append(
            FeatureContribution(
                feature=key,
                raw_value=features[key],
                normalized_score=normalized,
                weight=weight,
                weighted_contribution=weighted_contribution,
            )
        )
    if total_weight == 0.0:
        raise ScoringError("Total feature weight is zero — check FEATURE_WEIGHTS in config")
    raw_score = (total_weighted / total_weight) * 10.0
    if not (0.0 <= raw_score <= 10.0):
        logger.error(
            "Weighted score %.4f is outside expected [0, 10] range — likely a config error; clamping",
            raw_score,
        )
    clamped = max(0.0, min(10.0, raw_score))
    return round(clamped, 1), contributions


def _apply_hard_filters(features: dict[str, bool | str]) -> tuple[bool, list[str]]:
    failed_rules: list[str] = []
    for rule in HARD_FILTER_RULES:
        feature_key = rule["feature"]
        condition = rule["condition"]
        label = rule["label"]

        if feature_key not in features:
            logger.warning("Hard filter rule references unknown feature key %r — skipping", feature_key)
            continue

        value = features[feature_key]

        if condition == "is_false" and value is False:
            failed_rules.append(label)
            continue

        if condition == "equals" and value == rule.get("value"):
            failed_rules.append(label)
            continue

        if condition in {"enum_lte", "enum_lt"}:
            if not isinstance(value, str):
                logger.warning(
                    "Hard filter rule %r expects enum string for feature %r, got %r — skipping",
                    label,
                    feature_key,
                    type(value).__name__,
                )
                continue

            threshold = str(rule.get("value", "low")).strip().lower()
            value_normalized = value.strip().lower()

            if value_normalized not in _ENUM_RANK or threshold not in _ENUM_RANK:
                logger.warning(
                    "Hard filter rule %r has invalid enum value %r or threshold %r — skipping",
                    label,
                    value_normalized,
                    threshold,
                )
                continue

            if condition == "enum_lte" and _ENUM_RANK[value_normalized] <= _ENUM_RANK[threshold]:
                failed_rules.append(label)
                continue

            if condition == "enum_lt" and _ENUM_RANK[value_normalized] < _ENUM_RANK[threshold]:
                failed_rules.append(label)
                continue

    return bool(failed_rules), failed_rules


def _assign_decision(weighted_score: float, hard_filter_failed: bool) -> str:
    if hard_filter_failed:
        return "Drop"
    for threshold, label in DECISION_BANDS:
        if weighted_score >= threshold:
            return label
    return "Drop"


def score_payload(
    payload: LLMFeaturePayload,
    *,
    article_id: str | None = None,
    title: str | None = None,
    source: str | None = None,
    link: str | None = None,
    published: str | None = None,
    summary: str | None = None,
) -> ScoredArticle:
    if not isinstance(payload, LLMFeaturePayload):
        raise TypeError(f"payload must be LLMFeaturePayload, got {type(payload).__name__}")
    validate_scoring_config()
    hard_filter_failed, failed_rules = _apply_hard_filters(dict(payload.features))
    weighted_score, contributions = _compute_weighted_score(dict(payload.features))
    decision = _assign_decision(weighted_score, hard_filter_failed)
    if hard_filter_failed:
        logger.info(
            "Hard filter triggered article_id=%s rules=%s weighted_score=%.4f",
            article_id,
            failed_rules,
            weighted_score,
        )

    return ScoredArticle(
        article_id=article_id or "",
        title=title or payload.article_title,
        topic_title=payload.proposed_gd_topic,
        source=source or "",
        link=link or "",
        published=published,
        summary=summary or payload.proposed_gd_topic,
        weighted_score=weighted_score,
        decision=decision,
        features=dict(payload.features),
        evidence=dict(payload.evidence),
        hard_filter_failed=hard_filter_failed,
        hard_filter_rules_failed=tuple(failed_rules),
        prompt_version=payload.prompt_version,
        feature_contributions=[
            {
                "feature": c.feature,
                "raw_value": c.raw_value,
                "normalized_score": c.normalized_score,
                "weight": c.weight,
                "weighted_contribution": c.weighted_contribution,
            }
            for c in contributions
        ],
    )


def score_article(article: ArticleRecord) -> ScoredArticle:
    if not isinstance(article, ArticleRecord):
        raise TypeError(f"article must be an ArticleRecord, got {type(article).__name__}")
    validate_scoring_config()
    try:
        prompt = build_scoring_prompt(article)
    except ValueError as exc:
        raise ScoringError(f"Prompt build failed for article_id={article.article_id}: {exc}") from exc
    try:
        llm_response = generate_structured_response(
            prompt,
            article_title=article.title,
            article_summary=getattr(article, "summary", "") or "",
            article_body_text=getattr(article, "body_text", "") or "",
        )
    except LLMClientError as exc:
        raise ScoringError(f"LLM call failed for article_id={article.article_id}: {exc}") from exc
    return score_article_from_llm_response(article, llm_response)


def score_article_from_llm_response(article: ArticleRecord, llm_response: LLMStructuredResponse) -> ScoredArticle:
    if not isinstance(article, ArticleRecord):
        raise TypeError(f"article must be an ArticleRecord, got {type(article).__name__}")
    if not isinstance(llm_response, LLMStructuredResponse):
        raise TypeError(f"llm_response must be LLMStructuredResponse, got {type(llm_response).__name__}")
    logger.debug(
        "Scoring article_id=%s latency_ms=%s retry_count=%s injection_risk=%s response_hash=%s",
        article.article_id,
        llm_response.latency_ms,
        llm_response.retry_count,
        llm_response.injection_risk_level,
        llm_response.raw_response_hash,
    )
    logger.debug(
        "Features article_id=%s controversy=%s multiple_stakeholders=%s policy_relevance=%s "
        "ethical_dimension=%s factual_freshness=%s debate_balance=%s public_impact=%s topic_clarity=%s",
        article.article_id,
        llm_response.payload.features.get("controversy"),
        llm_response.payload.features.get("multiple_stakeholders"),
        llm_response.payload.features.get("policy_relevance"),
        llm_response.payload.features.get("ethical_dimension"),
        llm_response.payload.features.get("factual_freshness"),
        llm_response.payload.features.get("debate_balance"),
        llm_response.payload.features.get("public_impact"),
        llm_response.payload.features.get("topic_clarity"),
    )
    payload = llm_response.payload
    return score_payload(
        payload,
        article_id=article.article_id,
        title=article.title,
        source=article.source,
        link=article.link,
        published=article.published,
        summary=article.summary or payload.proposed_gd_topic,
    )


__all__ = [
    "ScoringError",
    "ScoringConfigError",
    "FeatureContribution",
    "validate_scoring_config",
    "score_payload",
    "score_article",
    "score_article_from_llm_response",
]