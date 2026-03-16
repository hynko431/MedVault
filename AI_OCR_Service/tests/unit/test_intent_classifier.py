"""
Unit tests for intent classifier.

Tests the IntentClassifier without requiring external services.
"""
import pytest
from app.services.search.intent_classifier import (
    IntentClassifier,
    SearchIntent,
    intent_classifier,
)


class TestIntentClassifier:
    """Test IntentClassifier functionality."""

    def test_init_creates_patterns(self):
        """Test that classifier initializes with patterns."""
        classifier = IntentClassifier()
        assert len(classifier.TEMPORAL_KEYWORDS) > 0
        assert len(classifier.SYMPTOM_KEYWORDS) > 0
        assert len(classifier.DOCTOR_KEYWORDS) > 0
        assert len(classifier.MEDICINE_KEYWORDS) > 0

    def test_contains_pattern_match(self):
        """Test pattern matching."""
        classifier = IntentClassifier()
        
        # The current implementation uses TEMPORAL_KEYWORDS and hardcoded regex
        result = classifier._score_temporal_intent("last month prescription") > 0
        assert result is True
        
        result = classifier._score_temporal_intent("january 2024") > 0
        assert result is True

    def test_contains_pattern_no_match(self):
        """Test pattern matching with no matches."""
        classifier = IntentClassifier()
        
        result = classifier._score_temporal_intent("just a regular query")
        assert result < 0.3

    def test_contains_keyword_match(self):
        """Test keyword matching."""
        classifier = IntentClassifier()
        
        # The current implementation uses _score methods with internal keywords
        result = classifier._score_symptom_intent("I have a headache") > 0
        assert result is True
        
        result = classifier._score_doctor_intent("dr smith prescribed this") > 0
        assert result is True
        
        result = classifier._score_medicine_intent("take this pill daily") > 0
        assert result is True

    def test_contains_keyword_no_match(self):
        """Test keyword matching with no matches."""
        classifier = IntentClassifier()
        
        result = classifier._score_symptom_intent("random text here")
        assert result == 0.0

    def test_detect_intent_empty_query(self):
        """Test intent detection with empty query."""
        classifier = IntentClassifier()
        
        result = classifier.detect_intent("")
        assert result == SearchIntent.GENERAL.value
        
        result = classifier.detect_intent("   ")
        assert result == SearchIntent.GENERAL.value
        
        from typing import cast
        result = classifier.detect_intent(cast(str, None))
        assert result == SearchIntent.GENERAL.value

    def test_detect_intent_temporal(self):
        """Test temporal intent detection."""
        classifier = IntentClassifier()
        
        queries = [
            "last month",
            "last week",
            "visit yesterday",
            "january 2024",
            "recent history"
        ]
        
        for query in queries:
            result = classifier.detect_intent(query)
            # Use lowercased value to match implementation
            assert result == SearchIntent.TEMPORAL_RECALL.value, f"Failed for: {query}"

    def test_detect_intent_doctor(self):
        """Test doctor search intent detection."""
        classifier = IntentClassifier()
        
        queries = [
            "dr johnson prescription",
            "doctor smith",
            "physician recommendation",
            "surgeon consult",
            "clinic visit"
        ]
        
        for query in queries:
            result = classifier.detect_intent(query)
            assert result == SearchIntent.DOCTOR_SEARCH.value, f"Failed for: {query}"

    def test_detect_intent_symptom(self):
        """Test symptom search intent detection."""
        classifier = IntentClassifier()
        
        queries = [
            "headache",
            "severe pain",
            "fever relief",
            "cough symptoms",
            "nausea",
            "dizziness"
        ]
        
        for query in queries:
            result = classifier.detect_intent(query)
            assert result == SearchIntent.SYMPTOM_SEARCH.value, f"Failed for: {query}"

    def test_detect_intent_medicine(self):
        """Test medicine lookup intent detection."""
        classifier = IntentClassifier()
        
        queries = [
            "paracetamol 500mg",
            "aspirin tablet",
            "ibuprofen dosage",
            "take this pill",
            "medication schedule"
        ]
        
        for query in queries:
            result = classifier.detect_intent(query)
            assert result == SearchIntent.MEDICINE_LOOKUP.value, f"Failed for: {query}"

    def test_detect_intent_general(self):
        """Test general intent fallback."""
        classifier = IntentClassifier()
        
        queries = [
            "hello",
            "random query",
            "what is this",
            "help me"
        ]
        
        for query in queries:
            result = classifier.detect_intent(query)
            assert result == SearchIntent.GENERAL.value, f"Failed for: {query}"

    def test_detect_intent_priority_order(self):
        """Test that intents are detected in correct priority order."""
        classifier = IntentClassifier()
        
        # The implementation uses max() of scores. 
        # "last month" gives 0.4 for temporal.
        # "dr smith" gives 1.0 for doctor (0.4 + 0.6).
        # So doctor wins here.
        result = classifier.detect_intent("dr smith last month")
        assert result == SearchIntent.DOCTOR_SEARCH.value
        
        # "headache" gives 0.3 for symptom.
        # "mg" gives 0.3 for medicine.
        # MEDICINE_LOOKUP (1st) wins over SYMPTOM_SEARCH (3rd) in case of a tie.
        result = classifier.detect_intent("headache 500mg")
        assert result == SearchIntent.MEDICINE_LOOKUP.value


class TestSearchIntentEnum:
    """Test SearchIntent enum."""

    def test_enum_values(self):
        """Test that enum values are correct."""
        assert SearchIntent.SYMPTOM_SEARCH.value == "symptom_search"
        assert SearchIntent.MEDICINE_LOOKUP.value == "medicine_lookup"
        assert SearchIntent.DOCTOR_SEARCH.value == "doctor_search"
        assert SearchIntent.TEMPORAL_RECALL.value == "temporal_recall"
        assert SearchIntent.GENERAL.value == "general"

    def test_enum_comparison(self):
        """Test enum value comparison."""
        assert SearchIntent.SYMPTOM_SEARCH == SearchIntent("symptom_search")
        assert SearchIntent.GENERAL == SearchIntent("general")


class TestGlobalClassifier:
    """Test global intent_classifier instance."""

    def test_global_classifier_exists(self):
        """Test that global classifier exists."""
        assert intent_classifier is not None
        assert isinstance(intent_classifier, IntentClassifier)

    def test_global_classifier_detect_intent(self):
        """Test that global classifier works."""
        result = intent_classifier.detect_intent("fever")
        assert result == SearchIntent.SYMPTOM_SEARCH.value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])