# test_scorer.py

import unittest
from models import LLMFeaturePayload
from scorer import (
    ScoringConfigError,
    ScoringError,
    _apply_hard_filters,
    _assign_decision,
    _compute_weighted_score,
    score_payload,
    validate_scoring_config,
)


class TestScorer(unittest.TestCase):
    def test_validate_scoring_config_passes(self):
        validate_scoring_config()

    def test_compute_weighted_score_perfect_score(self):
        features = {
            "controversy": True,
            "multiple_stakeholders": True,
            "policy_relevance": True,
            "ethical_dimension": True,
            "factual_freshness": "high",
            "debate_balance": "high",
            "public_impact": "high",
            "topic_clarity": "high",
        }
        score, contributions = _compute_weighted_score(features)
        self.assertEqual(score, 10.0)
        self.assertEqual(len(contributions), 8)

    def test_compute_weighted_score_zero_score(self):
        features = {
            "controversy": False,
            "multiple_stakeholders": False,
            "policy_relevance": False,
            "ethical_dimension": False,
            "factual_freshness": "low",
            "debate_balance": "low",
            "public_impact": "low",
            "topic_clarity": "low",
        }
        score, contributions = _compute_weighted_score(features)
        self.assertEqual(score, 0.0)

    def test_hard_filter_trigger_low_debate_balance(self):
        features = {
            "controversy": True,
            "multiple_stakeholders": True,
            "policy_relevance": True,
            "ethical_dimension": True,
            "factual_freshness": "high",
            "debate_balance": "low",
            "public_impact": "high",
            "topic_clarity": "high",
        }
        failed, rules = _apply_hard_filters(features)
        self.assertTrue(failed)
        self.assertIn("Weak debate balance", rules)

    def test_hard_filter_passes_high_quality(self):
        features = {
            "controversy": True,
            "multiple_stakeholders": True,
            "policy_relevance": True,
            "ethical_dimension": True,
            "factual_freshness": "high",
            "debate_balance": "high",
            "public_impact": "high",
            "topic_clarity": "high",
        }
        failed, rules = _apply_hard_filters(features)
        self.assertFalse(failed)
        self.assertEqual(len(rules), 0)

    def test_assign_decision_bands(self):
        self.assertEqual(_assign_decision(9.0, hard_filter_failed=False), "Suggest")
        self.assertEqual(_assign_decision(8.0, hard_filter_failed=False), "Suggest")
        self.assertEqual(_assign_decision(7.0, hard_filter_failed=False), "Borderline")
        self.assertEqual(_assign_decision(5.0, hard_filter_failed=False), "Background")
        self.assertEqual(_assign_decision(3.0, hard_filter_failed=False), "Drop")
        self.assertEqual(_assign_decision(9.5, hard_filter_failed=True), "Drop")

    def test_score_payload_integration(self):
        payload = LLMFeaturePayload(
            article_title="Test Article Title",
            proposed_gd_topic="Should Artificial Intelligence Be Regulated in Higher Education?",
            features={
                "controversy": True,
                "multiple_stakeholders": True,
                "policy_relevance": True,
                "ethical_dimension": True,
                "factual_freshness": "high",
                "debate_balance": "high",
                "public_impact": "high",
                "topic_clarity": "high",
            },
            evidence={
                "controversy": "Clear debate between faculty and administrators",
                "multiple_stakeholders": "Students, professors, and universities affected",
                "policy_relevance": "Connects directly to university governance policies",
                "ethical_dimension": "Raises academic integrity concerns",
                "factual_freshness": "Highly relevant to present day education",
                "debate_balance": "Multiple valid perspectives exist",
                "public_impact": "Broad impact on higher education systems",
                "topic_clarity": "Direct and understandable GD framing",
            },
            prompt_version="2026-05-21-v3",
        )

        scored = score_payload(payload, article_id="art-123", source="Tech Crunch", link="https://example.com/art")
        self.assertEqual(scored.weighted_score, 10.0)
        self.assertEqual(scored.decision, "Suggest")
        self.assertFalse(scored.hard_filter_failed)


if __name__ == "__main__":
    unittest.main()
