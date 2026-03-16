"""
Intent Classifier

Classifies search queries into different intent categories for intelligent routing.
Uses rule-based and ML-based approaches for intent detection.
"""

import re
import logging
from typing import Optional, Dict, Any, List, cast
from enum import Enum
from dataclasses import dataclass

from app.core.logging.logger import get_logger

logger = get_logger("intent_classifier")


class SearchIntent(str, Enum):
    """
    Search intent categories for query routing.
    """
    MEDICINE_LOOKUP = "medicine_lookup"
    DOCTOR_SEARCH = "doctor_search"
    SYMPTOM_SEARCH = "symptom_search"
    TEMPORAL_RECALL = "temporal_recall"
    GENERAL = "general"


@dataclass
class IntentClassification:
    """
    Result of intent classification.
    """
    intent: SearchIntent
    confidence: float
    features: Dict[str, Any]


class IntentClassifier:
    """
    Classifies search queries to determine user intent.
    Routes queries to appropriate search strategies.
    """
    
    # Medical keywords for intent detection
    MEDICINE_KEYWORDS = [
        "medicine", "medication", "drug", "tablet", "pill", "capsule",
        "syrup", "injection", "dose", "dosage", "prescription",
        "mg", "ml", "mcg", "g", "IU", "%"
    ]
    
    DOCTOR_KEYWORDS = [
        "doctor", "physician", "dr", "specialist", "consultant",
        "cardiologist", "dermatologist", "physician", "surgeon",
        "clinic", "hospital", "medical center"
    ]
    
    SYMPTOM_KEYWORDS = [
        "symptom", "pain", "ache", "fever", "cough", "cold",
        "headache", "nausea", "dizziness", "tired", "fatigue",
        "swelling", "rash", "infection", "inflammation", "symptoms"
    ]
    
    TEMPORAL_KEYWORDS = [
        "last week", "last month", "yesterday", "recent", "previous",
        "before", "after", "date", "when", "history", "record",
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december",
        "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "oct", "nov", "dec"
    ]
    
    def __init__(self):
        self._initialized = True
        logger.info("✅ Intent classifier initialized")
    
    def detect_intent(self, query: str) -> str:
        """
        Detect the intent of a search query.
        
        Args:
            query: The user's search query
        
        Returns:
            Intent string from SearchIntent enum
        """
        if not query:
            return SearchIntent.GENERAL.value
        
        query_lower = query.lower()
        
        # Score each intent type - initialize with floats for stable comparison
        scores: Dict[SearchIntent, float] = {
            SearchIntent.MEDICINE_LOOKUP: float(self._score_medicine_intent(query_lower)),
            SearchIntent.DOCTOR_SEARCH: float(self._score_doctor_intent(query_lower)),
            SearchIntent.SYMPTOM_SEARCH: float(self._score_symptom_intent(query_lower)),
            SearchIntent.TEMPORAL_RECALL: float(self._score_temporal_intent(query_lower)),
        }
        
        # Get highest scoring intent
        # Use items() to get a list of tuples for stable comparison if needed, 
        # but the key issue is type narrowing for the key function
        best_intent = max(scores.keys(), key=lambda k: float(scores[k]))
        best_score = float(scores[best_intent])
        
        # Log classification
        logger.debug(f"Intent classification: '{query}' -> {best_intent.value} (score: {best_score:.2f})")
        
        # If no strong signal, return general
        if best_score < 0.3:
            return str(SearchIntent.GENERAL.value)
        
        res_val = str(best_intent.value)
        return res_val
    
    def classify(self, query: str) -> IntentClassification:
        """
        Full classification with confidence and features.
        
        Args:
            query: The user's search query
        
        Returns:
            IntentClassification with details
        """
        intent_str = self.detect_intent(query)
        # Explicitly cast to SearchIntent enum
        intent = SearchIntent(str(intent_str))
        
        conf = float(self._calculate_confidence(query, SearchIntent(intent_str)))
        features = self._extract_features(query)
        result = IntentClassification(intent=SearchIntent(intent_str), confidence=conf, features=features)
        return result
    
    def _score_medicine_intent(self, query: str) -> float:
        """Score how likely query is about medicine lookup."""
        score: float = 0.0
        
        # Check for medicine keywords with robust matching
        units = ["mg", "ml", "mcg", "g", "IU", "%"]
        for keyword in self.MEDICINE_KEYWORDS:
            if keyword in units:
                if re.search(rf"(?<![a-zA-Z]){re.escape(keyword)}(?![a-zA-Z])", query, re.IGNORECASE):
                    score = float(score) + 0.3
            else:
                if re.search(rf"\b{re.escape(keyword)}\b", query, re.IGNORECASE):
                    score: float = float(score) + 0.3
        
        # Additional numeric casts as requested
        score = float(score)
        # Check for medicine name patterns (capitalized words)
        if re.search(r'\b[A-Z][a-z]+\s+\d+\s*(mg|ml|mcg|g)\b', query, re.IGNORECASE):
            score = float(score) + 0.5
        
        # Check for frequency patterns
        if re.search(r'\b(BD|TID|OD|QID|HS)\b', query, re.IGNORECASE):
            score = float(score) + 0.4
        
        return float(min(score, 1.0))
    
    def _score_doctor_intent(self, query: str) -> float:
        """Score how likely query is about doctor/hospital search."""
        score: float = 0.0
        
        # Check for doctor keywords with word boundaries
        for keyword in self.DOCTOR_KEYWORDS:
            if re.search(rf"\b{re.escape(keyword)}\b", query, re.IGNORECASE):
                score: float = float(score) + 0.4
        
        return float(min(score, 1.0))
    
    def _score_symptom_intent(self, query: str) -> float:
        """Score how likely query is symptom-based search."""
        score: float = 0.0
        
        # Check for symptom keywords with word boundaries
        for keyword in self.SYMPTOM_KEYWORDS:
            if re.search(rf"\b{re.escape(keyword)}\b", query, re.IGNORECASE):
                score: float = float(score) + 0.3
        
        # Check for symptom description patterns
        if re.search(r'(feeling|having|experiencing|suffering from)', query, re.IGNORECASE):
            score = float(score) + 0.4
        
        return float(min(score, 1.0))
    
    def _score_temporal_intent(self, query: str) -> float:
        """Score how likely query is temporal/date-based."""
        score: float = 0.0
        
        # Check for temporal keywords with word boundaries
        for keyword in self.TEMPORAL_KEYWORDS:
            if re.search(rf"\b{re.escape(keyword)}\b", query, re.IGNORECASE):
                score: float = float(score) + 0.4
        
        # Check for date patterns (e.g. 2024, 2024-01-01, 01/01/2024)
        if re.search(r'\b(20\d{2}|19\d{2})\b', query) or re.search(r'\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}', query):
            score = float(score) + 0.5
        
        return float(min(score, 1.0))
    
    def _calculate_confidence(self, query: str, intent: SearchIntent) -> float:
        """Calculate confidence score for the classification."""
        query_lower = query.lower()
        
        if intent == SearchIntent.MEDICINE_LOOKUP:
            return self._score_medicine_intent(query_lower)
        elif intent == SearchIntent.DOCTOR_SEARCH:
            return self._score_doctor_intent(query_lower)
        elif intent == SearchIntent.SYMPTOM_SEARCH:
            return self._score_symptom_intent(query_lower)
        elif intent == SearchIntent.TEMPORAL_RECALL:
            return self._score_temporal_intent(query_lower)
        
        return 0.5  # Default confidence for GENERAL
    
    def _extract_features(self, query: str) -> Dict[str, Any]:
        """Extract features from the query for logging/analysis."""
        features = {
            "query_length": len(query),
            "word_count": len(query.split()),
            "has_medicine_terms": any(
                re.search(rf"(?<![a-zA-Z]){re.escape(kw)}(?![a-zA-Z])", query.lower()) if kw in ["mg", "ml", "mcg", "g", "IU", "%"]
                else re.search(rf"\b{re.escape(kw)}\b", query.lower())
                for kw in self.MEDICINE_KEYWORDS
            ),
            "has_doctor_terms": any(re.search(rf"\b{re.escape(kw)}\b", query.lower()) for kw in self.DOCTOR_KEYWORDS),
            "has_symptom_terms": any(re.search(rf"\b{re.escape(kw)}\b", query.lower()) for kw in self.SYMPTOM_KEYWORDS),
            "has_temporal_terms": any(re.search(rf"\b{re.escape(kw)}\b", query.lower()) for kw in self.TEMPORAL_KEYWORDS),
        }
        
        return features


# Global classifier instance
_intent_classifier: Optional[IntentClassifier] = None


def get_intent_classifier() -> IntentClassifier:
    """Get or create the intent classifier."""
    global _intent_classifier
    if _intent_classifier is None:
        _intent_classifier = IntentClassifier()
    return _intent_classifier


# Convenience alias for FastAPI dependency injection
intent_classifier = get_intent_classifier()