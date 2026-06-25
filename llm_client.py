#llm_client.py

from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import re
import threading
import time
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel

from config import (
    DEFAULT_API_VERSION,
    DEFAULT_MODEL_NAME,
    LLM_PROVIDER,
    LLM_TEMPERATURE,
    MAX_LLM_RETRIES,
    MAX_OUTPUT_TOKENS,
    MOCK_MODE,
    PROMPT_VERSION,
    RETRY_BASE_DELAY_SECONDS,
    RETRY_JITTER,
    RETRY_MAX_DELAY_SECONDS,
)
from models import LLMFeaturePayload, LLMStructuredResponse

logger = logging.getLogger(__name__)

_FEATURE_KEYS = frozenset(
    {
        "controversy",
        "multiple_stakeholders",
        "policy_relevance",
        "ethical_dimension",
        "factual_freshness",
        "debate_balance",
        "public_impact",
        "topic_clarity",
    }
)

_BOOLEAN_FEATURES = frozenset(
    {
        "controversy",
        "multiple_stakeholders",
        "policy_relevance",
        "ethical_dimension",
    }
)

_ENUM_FEATURES = {
    "factual_freshness": frozenset({"low", "medium", "high"}),
    "debate_balance": frozenset({"low", "medium", "high"}),
    "public_impact": frozenset({"low", "medium", "high"}),
    "topic_clarity": frozenset({"low", "medium", "high"}),
}

_ALLOWED_FINISH_REASONS = frozenset({"STOP", "MAX_TOKENS"})
_MAX_TOPIC_CHARS = 200
_MAX_EVIDENCE_VALUE_CHARS = 240
_MIN_EVIDENCE_TOKENS = 2
_MAX_TOTAL_RAW_RESPONSE_CHARS = 12000
_TITLE_SIMILARITY_MIN = 0.80
_NEGATION_WINDOW_WORDS = 8
_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?;:])\s+")

_INJECTION_PATTERNS = (
    r"ignore[\s\W_]*previous",
    r"ignore[\s\W_]*all[\s\W_]*previous",
    r"system[\s\W_]*instruction",
    r"assistant[\s\W_]*:",
    r"output[\s\W_]*json",
    r"return[\s\W_]*only[\s\W_]*json",
    r"developer[\s\W_]*message",
    r"follow[\s\W_]*these[\s\W_]*instructions",
)

_COMPILED_INJECTION_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE) for pattern in _INJECTION_PATTERNS
)

_LOW_VALUE_EVIDENCE = frozenset(
    {
        "yes",
        "no",
        "maybe",
        "good",
        "bad",
        "relevant",
        "not relevant",
        "clear",
        "unclear",
        "important",
        "not important",
        "good issue",
    }
)

_THREAD_LOCAL = threading.local()

_CIRCUIT_LOCK = threading.Lock()
_CIRCUIT_STATE = {"consecutive_infra_failures": 0, "opened_until": 0.0}
_CIRCUIT_FAILURE_THRESHOLD = 5
_CIRCUIT_OPEN_SECONDS = 60


@dataclass(frozen=True)
class InjectionScanResult:
    risk_level: str
    matched_patterns: tuple[str, ...]


class LLMClientError(RuntimeError):
    pass


class LLMRetryableError(LLMClientError):
    pass


class LLMNonRetryableError(LLMClientError):
    pass


class LLMValidationError(LLMNonRetryableError):
    pass


class GeminiFeatureSchema(BaseModel):
    controversy: bool
    multiple_stakeholders: bool
    policy_relevance: bool
    ethical_dimension: bool
    factual_freshness: str
    debate_balance: str
    public_impact: str
    topic_clarity: str


class GeminiEvidenceSchema(BaseModel):
    controversy: str
    multiple_stakeholders: str
    policy_relevance: str
    ethical_dimension: str
    factual_freshness: str
    debate_balance: str
    public_impact: str
    topic_clarity: str


class GeminiStructuredPayloadSchema(BaseModel):
    article_title: str
    proposed_gd_topic: str
    features: GeminiFeatureSchema
    evidence: GeminiEvidenceSchema
    prompt_version: str


def _get_api_key() -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise LLMClientError("GEMINI_API_KEY is missing and MOCK_MODE is False.")
    return api_key


def _get_genai_client() -> genai.Client:
    client = getattr(_THREAD_LOCAL, "genai_client", None)
    if client is None:
        client = genai.Client(
            api_key=_get_api_key(),
            http_options=types.HttpOptions(api_version=DEFAULT_API_VERSION),
        )
        _THREAD_LOCAL.genai_client = client
    return client


def _estimate_tokens_rough(text: str) -> int:
    return 0 if not text else max(1, int(len(text) / 4))


def _compute_backoff_delay(attempt_index: int) -> float:
    delay = min(RETRY_BASE_DELAY_SECONDS * (2 ** attempt_index), RETRY_MAX_DELAY_SECONDS)
    if RETRY_JITTER:
        delay *= random.uniform(0.8, 1.25)
    return max(0.0, delay)


def _normalize_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split()).strip()


def normalized_title_matches(expected: str, actual: str) -> bool:
    return _normalize_text(expected).casefold() == _normalize_text(actual).casefold()


def _title_similarity(expected: str, actual: str) -> float:
    return SequenceMatcher(
        None,
        _normalize_text(expected).casefold(),
        _normalize_text(actual).casefold(),
    ).ratio()


def scan_text_for_injection_signals(text: str) -> tuple[str, ...]:
    lowered = unicodedata.normalize("NFKC", text).casefold()
    matches: list[str] = []
    for pattern in _COMPILED_INJECTION_PATTERNS:
        if pattern.search(lowered):
            matches.append(pattern.pattern)
    return tuple(matches)


def scan_article_fields_for_injection_risk(*, title: str, summary: str, body_text: str) -> InjectionScanResult:
    matches: list[str] = []
    for part in (title, summary, body_text):
        if part.strip():
            matches.extend(scan_text_for_injection_signals(part))
    unique_matches = tuple(sorted(set(matches)))
    if len(unique_matches) >= 3:
        return InjectionScanResult(risk_level="high", matched_patterns=unique_matches)
    if unique_matches:
        return InjectionScanResult(risk_level="medium", matched_patterns=unique_matches)
    return InjectionScanResult(risk_level="low", matched_patterns=())


def _check_circuit_breaker() -> None:
    with _CIRCUIT_LOCK:
        now = time.time()
        if float(_CIRCUIT_STATE["opened_until"]) > now:
            raise LLMClientError(f"LLM circuit breaker open until {_CIRCUIT_STATE['opened_until']:.0f}")


def _record_infra_success() -> None:
    with _CIRCUIT_LOCK:
        _CIRCUIT_STATE["consecutive_infra_failures"] = 0
        _CIRCUIT_STATE["opened_until"] = 0.0


def _record_infra_failure() -> None:
    with _CIRCUIT_LOCK:
        _CIRCUIT_STATE["consecutive_infra_failures"] += 1
        if _CIRCUIT_STATE["consecutive_infra_failures"] >= _CIRCUIT_FAILURE_THRESHOLD:
            _CIRCUIT_STATE["opened_until"] = time.time() + _CIRCUIT_OPEN_SECONDS
            logger.error(
                "LLM circuit breaker opened for %ss after %s consecutive infrastructure failures",
                _CIRCUIT_OPEN_SECONDS,
                _CIRCUIT_STATE["consecutive_infra_failures"],
            )


def _is_infra_failure(exc: Exception) -> bool:
    message = str(exc).lower()
    if any(code in message for code in ("500", "502", "503", "504")):
        return True
    if any(term in message for term in ("timeout", "timed out", "deadline exceeded")):
        return True
    if any(term in message for term in ("connection reset", "connection refused", "network")):
        return True
    return False


def _extract_retry_delay(exc: Exception) -> float | None:
    match = re.search(r"'retryDelay':\s*'([0-9.]+)s'", str(exc))
    if match:
        return float(match.group(1))
    return None


def _parse_json_object(raw_text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw_text)
    except ValueError as exc:
        logger.debug("JSON parse failed. raw_text=%r", raw_text[:500])
        raise LLMValidationError("Model returned invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise LLMValidationError("Model output must be a JSON object")
    return parsed


def _extract_finish_reason(response: Any) -> str:
    _FINISH_REASON_INT_MAP = {
        1: "STOP",
        2: "MAX_TOKENS",
        3: "SAFETY",
        4: "RECITATION",
        5: "OTHER",
    }
    candidates = getattr(response, "candidates", None)
    if isinstance(candidates, list) and candidates:
        candidate = candidates[0]
        finish_reason = getattr(candidate, "finish_reason", None)
        if finish_reason is None and isinstance(candidate, dict):
            finish_reason = candidate.get("finish_reason")
        if finish_reason is not None:
            if isinstance(finish_reason, int):
                return _FINISH_REASON_INT_MAP.get(finish_reason, f"UNKNOWN_INT_{finish_reason}")
            value = str(finish_reason).strip()
            if "." in value:
                value = value.rsplit(".", 1)[-1]
            return value.upper()
    return "UNKNOWN"


def _require_exact_keys(obj: dict[str, Any], expected: set[str], field_name: str) -> None:
    actual = set(obj.keys())
    if actual != expected:
        raise LLMValidationError(
            f"{field_name} keys must exactly match {sorted(expected)}, got {sorted(actual)}"
        )


def _validate_non_empty_string(value: Any, field_name: str, *, max_length: int | None = None) -> str:
    if not isinstance(value, str):
        raise LLMValidationError(f"{field_name} must be a string")
    cleaned = " ".join(value.split()).strip()
    if not cleaned:
        raise LLMValidationError(f"{field_name} must be non-empty")
    if max_length is not None and len(cleaned) > max_length:
        raise LLMValidationError(f"{field_name} exceeds max length {max_length}")
    return cleaned


def _validate_evidence_value(key: str, value: Any) -> str:
    cleaned = _validate_non_empty_string(
        value,
        f"evidence.{key}",
        max_length=_MAX_EVIDENCE_VALUE_CHARS,
    )
    if cleaned.casefold() in _LOW_VALUE_EVIDENCE:
        raise LLMValidationError(f"evidence.{key} is too low-information")
    if len(cleaned.split()) < _MIN_EVIDENCE_TOKENS:
        raise LLMValidationError(
            f"evidence.{key} must contain at least {_MIN_EVIDENCE_TOKENS} tokens"
        )
    return cleaned


_NEGATION_WORDS = frozenset(
    {"no", "not", "without", "lack", "lacks", "lacking", "absence", "none", "neither", "minimal", "little"}
)


def _term_has_unnegated_occurrence(text: str, term: str) -> bool:
    normalized_text = unicodedata.normalize("NFKC", text).casefold()
    normalized_term = unicodedata.normalize("NFKC", term).casefold()

    for sentence in _SENTENCE_SPLIT_PATTERN.split(normalized_text):
        if normalized_term not in sentence:
            continue
        for match in re.finditer(re.escape(normalized_term), sentence):
            preceding_words = re.findall(r"\b\w+\b", sentence[: match.start()])[-_NEGATION_WINDOW_WORDS:]
            if not any(word in _NEGATION_WORDS for word in preceding_words):
                return True
    return False


def _validate_feature_consistency(
    features: dict[str, bool | str],
    evidence: dict[str, str],
) -> None:
    controversy_evidence = evidence["controversy"].casefold()
    if features["controversy"] is False and any(
        _term_has_unnegated_occurrence(controversy_evidence, term)
        for term in (
            "clear disagreement",
            "active debate",
            "open conflict",
            "opposing sides",
            "competing claims",
        )
    ):
        logger.debug("Contradiction detail: controversy=False evidence=%r", controversy_evidence)
        raise LLMValidationError("controversy evidence contradicts controversy=False")

    balance_evidence = evidence["debate_balance"].casefold()
    if features["debate_balance"] == "low" and any(
        _term_has_unnegated_occurrence(balance_evidence, term)
        for term in (
            "both sides",
            "balanced arguments",
            "strong arguments on both sides",
            "multiple reasonable sides",
        )
    ):
        logger.debug("Contradiction detail: debate_balance=low evidence=%r", balance_evidence)
        raise LLMValidationError("debate_balance evidence contradicts debate_balance=low")

    clarity_evidence = evidence["topic_clarity"].casefold()
    if features["topic_clarity"] == "high" and any(
        _term_has_unnegated_occurrence(clarity_evidence, term)
        for term in ("unclear", "vague", "ambiguous")
    ):
        logger.debug("Contradiction detail: topic_clarity=high evidence=%r", clarity_evidence)
        raise LLMValidationError("topic_clarity evidence contradicts topic_clarity=high")


def _validate_feature_payload(
    data: dict[str, Any],
    *,
    expected_article_title: str | None = None,
) -> LLMFeaturePayload:
    _require_exact_keys(
        data,
        {"article_title", "proposed_gd_topic", "features", "evidence", "prompt_version"},
        "root",
    )

    article_title = _validate_non_empty_string(
        data["article_title"],
        "article_title",
        max_length=500,
    )
    proposed_gd_topic = _validate_non_empty_string(
        data["proposed_gd_topic"],
        "proposed_gd_topic",
        max_length=_MAX_TOPIC_CHARS,
    )
    prompt_version = _validate_non_empty_string(
        data["prompt_version"],
        "prompt_version",
        max_length=64,
    )

    if prompt_version != PROMPT_VERSION:
        raise LLMValidationError(
            f"prompt_version mismatch: expected {PROMPT_VERSION}, got {prompt_version}"
        )

    if expected_article_title is not None and not normalized_title_matches(
        expected_article_title, article_title
    ):
        similarity = _title_similarity(expected_article_title, article_title)
        if similarity < _TITLE_SIMILARITY_MIN:
            raise LLMValidationError(
                f"article_title does not match expected title after normalization "
                f"(similarity={similarity:.2f})"
            )
        logger.warning(
            "Accepting fuzzy article_title match similarity=%.2f expected=%r actual=%r",
            similarity,
            expected_article_title,
            article_title,
        )

    features = data["features"]
    evidence = data["evidence"]

    if not isinstance(features, dict):
        raise LLMValidationError("features must be an object")
    if not isinstance(evidence, dict):
        raise LLMValidationError("evidence must be an object")

    _require_exact_keys(features, set(_FEATURE_KEYS), "features")
    _require_exact_keys(evidence, set(_FEATURE_KEYS), "evidence")

    normalized_features: dict[str, bool | str] = {}
    for key in _BOOLEAN_FEATURES:
        value = features[key]
        if not isinstance(value, bool):
            raise LLMValidationError(f"features.{key} must be a boolean")
        normalized_features[key] = value

    for key, allowed in _ENUM_FEATURES.items():
        value = features[key]
        if not isinstance(value, str):
            raise LLMValidationError(f"features.{key} must be a string enum")
        cleaned = value.strip().lower()
        if cleaned not in allowed:
            raise LLMValidationError(
                f"features.{key} must be one of {sorted(allowed)}"
            )
        normalized_features[key] = cleaned

    normalized_evidence: dict[str, str] = {
        key: _validate_evidence_value(key, evidence[key]) for key in _FEATURE_KEYS
    }

    _validate_feature_consistency(normalized_features, normalized_evidence)

    return LLMFeaturePayload(
        article_title=article_title,
        proposed_gd_topic=proposed_gd_topic,
        features=normalized_features,
        evidence=normalized_evidence,
        prompt_version=prompt_version,
    )


def _mock_response(
    prompt: str,
    *,
    expected_article_title: str | None = None,
    injection_risk_level: str = "low",
) -> LLMStructuredResponse:
    bad_mode = os.getenv("AIDE_MOCK_BAD_OUTPUT", "").strip().lower()
    if bad_mode in {"invalid_json", "missing_fields", "bad_enum", "contradiction"}:
        raise LLMValidationError(f"Simulated {bad_mode}")

    title = expected_article_title or "Mock Article"
    mock_payload_dict = {
        "article_title": title,
        "proposed_gd_topic": "Should this issue be used for group discussion?",
        "features": {
            "controversy": True,
            "multiple_stakeholders": True,
            "policy_relevance": False,
            "ethical_dimension": True,
            "factual_freshness": "medium",
            "debate_balance": "high",
            "public_impact": "medium",
            "topic_clarity": "high",
        },
        "evidence": {
            "controversy": "clear disagreement exists between affected groups",
            "multiple_stakeholders": "government and public are affected differently",
            "policy_relevance": "article does not focus on a direct policy proposal",
            "ethical_dimension": "raises fairness and responsibility concerns",
            "factual_freshness": "article appears current from the stated context",
            "debate_balance": "strong arguments exist on both sides of the issue",
            "public_impact": "issue affects a broad section of society",
            "topic_clarity": "can be framed as a direct and understandable GD question",
        },
        "prompt_version": PROMPT_VERSION,
    }

    validated = _validate_feature_payload(
        mock_payload_dict,
        expected_article_title=expected_article_title,
    )
    raw_text = json.dumps(mock_payload_dict, ensure_ascii=False)
    return LLMStructuredResponse(
        provider="mock",
        model="mock-model",
        payload=validated,
        raw_text=raw_text,
        raw_response_hash=hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
        prompt_tokens_est=_estimate_tokens_rough(prompt),
        output_tokens_est=_estimate_tokens_rough(raw_text),
        finish_reason="STOP",
        request_id=None,
        latency_ms=0,
        retry_count=0,
        validation_flags=(),
        injection_risk_level=injection_risk_level,
    )


def generate_structured_response(
    prompt: str,
    *,
    article_title: str | None = None,
    article_summary: str = "",
    article_body_text: str = "",
) -> LLMStructuredResponse:
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt must be a non-empty string")

    scan_result = scan_article_fields_for_injection_risk(
        title=article_title or "",
        summary=article_summary,
        body_text=article_body_text,
    )

    if scan_result.risk_level == "high":
        raise LLMClientError(
            f"Article quarantined due to high prompt-injection risk: {scan_result.matched_patterns}"
        )

    if scan_result.risk_level == "medium":
        logger.warning(
            "Prompt injection medium-risk markers detected in article content: %s",
            scan_result.matched_patterns,
        )

    if MOCK_MODE:
        return _mock_response(
            prompt,
            expected_article_title=article_title,
            injection_risk_level=scan_result.risk_level,
        )

    if LLM_PROVIDER.lower() != "gemini":
        raise LLMClientError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")

    _check_circuit_breaker()
    client = _get_genai_client()
    last_error: Exception | None = None

    for attempt in range(MAX_LLM_RETRIES + 1):
        started = time.perf_counter()
        try:
            response = client.models.generate_content(
                model=DEFAULT_MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=LLM_TEMPERATURE,
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                    response_mime_type="application/json",
                    response_schema=GeminiStructuredPayloadSchema,
                ),
            )

            raw_text = (response.text or "").strip()
            if not raw_text:
                raise LLMValidationError("Gemini response contained no text output")
            if len(raw_text) > _MAX_TOTAL_RAW_RESPONSE_CHARS:
                raise LLMValidationError("Gemini response exceeded maximum allowed size")

            parsed_obj = response.parsed
            if parsed_obj is not None and hasattr(parsed_obj, "model_dump"):
                parsed_dict = parsed_obj.model_dump()
            else:
                parsed_dict = _parse_json_object(raw_text)

            validated = _validate_feature_payload(
                parsed_dict,
                expected_article_title=article_title,
            )

            finish_reason = _extract_finish_reason(response)
            if finish_reason not in _ALLOWED_FINISH_REASONS:
                raise LLMValidationError(f"Disallowed finish_reason from Gemini: {finish_reason}")

            latency_ms = int((time.perf_counter() - started) * 1000)
            raw_response_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
            _record_infra_success()

            return LLMStructuredResponse(
                provider=LLM_PROVIDER,
                model=DEFAULT_MODEL_NAME,
                payload=validated,
                raw_text=raw_text,
                raw_response_hash=raw_response_hash,
                prompt_tokens_est=_estimate_tokens_rough(prompt),
                output_tokens_est=_estimate_tokens_rough(raw_text),
                finish_reason=finish_reason,
                request_id=None,
                latency_ms=latency_ms,
                retry_count=attempt,
                validation_flags=(),
                injection_risk_level=scan_result.risk_level,
            )

        except Exception as exc:
            last_error = exc

            if _is_infra_failure(exc):
                _record_infra_failure()
            else:
                _record_infra_success()

            message = str(exc)
            retryable = (
                isinstance(exc, LLMRetryableError)
                or "429" in message
                or "500" in message
                or "503" in message
                or _is_infra_failure(exc)
            )

            if not retryable or attempt >= MAX_LLM_RETRIES:
                break

            retry_delay = (
                _extract_retry_delay(last_error)
                if last_error is not None and "429" in str(last_error)
                else None
            )
            wait = (
                retry_delay
                if (retry_delay is not None and retry_delay > 0)
                else _compute_backoff_delay(attempt)
            )
            logger.debug(
                "Retry attempt=%s waiting=%.1fs (source=%s)",
                attempt + 1,
                wait,
                "gemini_retry_delay" if retry_delay is not None else "backoff",
            )
            time.sleep(wait)

    raise LLMClientError(
        f"Gemini request failed after {attempt + 1} attempts: {last_error}"
    )


__all__ = [
    "InjectionScanResult",
    "LLMFeaturePayload",
    "LLMStructuredResponse",
    "LLMClientError",
    "LLMRetryableError",
    "LLMNonRetryableError",
    "LLMValidationError",
    "scan_text_for_injection_signals",
    "scan_article_fields_for_injection_risk",
    "normalized_title_matches",
    "generate_structured_response",
]