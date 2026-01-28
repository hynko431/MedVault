# 🔍 Advanced Elasticsearch Search Implementation Guide

## 📋 Overview

This guide documents the advanced Elasticsearch search features implemented in the MedVault AI OCR Service, including multi-layer relevance tuning, recency boosting, and safe fuzzy matching.

---

## 🧱 Architecture: Multi-Layer Relevance Strategy

### **Priority Hierarchy**
```
Exact match > Prefix match > Fuzzy match
Medicine > Doctor > Hospital
Recent > Old
```

---

## 🧱 LAYER 1: Field-Level Boosting

### **Concept**
Different fields have different importance in medical prescriptions. Medicine names are most critical for patient safety and relevance.

### **Implementation**
```python
# Medicine gets highest boost
"medicine_names": {"query": text, "boost": 5}

# Doctor gets medium boost
"doctor_name": {"query": text, "boost": 2}

# Hospital gets lowest boost
"hospital": {"query": text, "boost": 1}
```

### **Interview Line**
> "I use field-level boosting to prioritize medicine matches over doctor or hospital matches, as medicine names are most relevant for prescription searches."

---

## 🧱 LAYER 2: Exact Match > Partial Match

### **Problem**
Autocomplete and fuzzy searches can over-rank partial matches. Searching for "paracetamol" should rank exact "paracetamol" higher than "para..." prefix matches.

### **Solution: Multi-Field Matching with `match_phrase`**

```python
"should": [
    {
        "match_phrase": {
            "medicine_names": {
                "query": text,
                "boost": 8   # Exact phrase wins
            }
        }
    },
    {
        "match": {
            "medicine_names": {
                "query": text,
                "boost": 5   # Standard match lower
            }
        }
    }
]
```

### **Result**
- **"paracetamol"** (exact) → Higher score
- **"para..."** (prefix) → Lower score

### **Interview Line**
> "I use `match_phrase` queries with higher boost values to ensure exact matches always rank above partial or prefix matches."

---

## 🧱 LAYER 3: Recency Boost (Smart Freshness)

### **Problem**
Medical data is time-sensitive. Recent prescriptions are more relevant, but we don't want to override relevance completely.

### **Solution: Function Score Query with Gauss Decay**

```python
"query": {
    "function_score": {
        "query": {
            "bool": {
                "should": [...],  # Your relevance queries
                "filter": [{"term": {"user_id": user_id}}]
            }
        },
        "functions": [
            {
                "gauss": {
                    "created_at": {
                        "origin": "now",
                        "scale": "30d",   # 30-day window
                        "decay": 0.5      # Slow decay
                    }
                }
            }
        ],
        "score_mode": "avg",    # Average function scores
        "boost_mode": "sum"     # Add to relevance score
    }
}
```

### **How It Works**
1. **Newer prescriptions** (within 30 days) get higher score
2. **Older prescriptions** slowly decay
3. **Exact medicine match still wins** (relevance + recency = total score)

### **Interview Line**
> "I use a gauss decay function to softly boost recent prescriptions without overpowering relevance. The score_mode 'avg' and boost_mode 'sum' ensure recency enhances but doesn't dominate the final ranking."

---

## 🧱 LAYER 4: Fuzzy Search Without Chaos

### **Problem**
Fuzzy search is dangerous if unchecked. Without safeguards, "ab" could match hundreds of irrelevant terms.

### **Solution: Safe Fuzzy Tuning**

```python
{
    "match": {
        "medicine_names": {
            "query": text,
            "fuzziness": "AUTO",
            "prefix_length": 2,      # First 2 chars must match exactly
            "max_expansions": 50,    # Limit term expansions
            "boost": 3               # Lower than exact match
        }
    }
}
```

### **Why This Matters**
- **`prefix_length=2`** → Avoids wild matches (first 2 chars must be exact)
- **`max_expansions=50`** → Performance safe, limits how many terms ES checks
- **Lower boost** → Fuzzy matches rank below exact matches

### **Example**
- Query: "paracetmol" (typo)
- Matches: "paracetamol" ✅
- Doesn't match: "ibuprofen" ❌ (first 2 chars don't match)

### **Interview Line**
> "I use `prefix_length=2` and `max_expansions=50` to make fuzzy search safe and performant while still handling typos effectively."

---

## 🧱 BONUS: Explainability & Debugging

### **Debug Scores with `_explain`**

When debugging why documents rank the way they do:

```bash
POST prescriptions_current/_search?explain=true
{
  "query": {
    "match": {
      "medicine_names": "paracetamol"
    }
  }
}
```

### **Response Shows**
- ✅ Which field matched
- ✅ How much boost was applied
- ✅ Final score breakdown
- ✅ Why document A ranks higher than B

### **Interview Line**
> "I use the `_explain` parameter to debug relevance scores and understand exactly why documents rank in a certain order. This helps fine-tune boost values and query structure."

---

## 📊 Complete Relevance Strategy Summary

### **Priority Matrix**

| Layer | Feature | Boost/Config | Purpose |
|-------|---------|--------------|---------|
| 1 | Medicine Field | boost: 5-8 | Most important field |
| 1 | Doctor Field | boost: 2-4 | Medium importance |
| 1 | Hospital Field | boost: 1-2 | Lowest importance |
| 2 | Exact Match (match_phrase) | boost: 8-10 | Exact wins over partial |
| 2 | Standard Match | boost: 3-5 | Partial matching |
| 3 | Recency (gauss decay) | 30d scale | Recent > Old |
| 4 | Fuzzy Safe | prefix_length: 2 | Typo tolerance |
| 4 | Fuzzy Performance | max_expansions: 50 | Performance safe |

---

## 🎯 Implementation Checklist

- [x] **Field-level boosting** (Medicine > Doctor > Hospital)
- [x] **Exact match priority** (match_phrase with high boost)
- [x] **Recency boost** (function_score with gauss decay)
- [x] **Safe fuzzy search** (prefix_length + max_expansions)
- [x] **Autocomplete** with exact match priority
- [x] **Pagination & sorting** support
- [x] **User-scoped filtering** (multi-tenancy)

---

## 🚀 API Endpoints

### 1. **Universal Search** (Recommended)
```http
GET /search/all?q=paracetamol&user_id=user123&page=1&page_size=10&sort_by=relevance
```

**Features:**
- All layers applied (exact match, recency, field boosting)
- Pagination support
- Sort by relevance or date

### 2. **Autocomplete Search**
```http
GET /search/autocomplete?q=para&user_id=user123&size=10
```

**Features:**
- Exact match priority
- Fast prefix matching
- No pagination (top results only)

### 3. **Fuzzy Search** (Typo Tolerance)
```http
GET /search/fuzzy?q=paracetmol&user_id=user123&page=1&page_size=10
```

**Features:**
- Safe fuzzy matching
- Handles typos
- prefix_length=2 for safety

---

## 🧪 Testing Search Relevance

### **Test Scenarios**

#### 1. Exact Match Priority
```bash
# Query: "paracetamol"
# Expected: Exact "paracetamol" ranks higher than "paracetamol 500mg"
```

#### 2. Recency Boost
```bash
# Query: "aspirin"
# Expected: Recent prescriptions rank higher for same medicine
```

#### 3. Field Priority
```bash
# Query: "apollo"
# Expected: Medicine named "apollo" ranks higher than hospital "Apollo Hospital"
```

#### 4. Fuzzy Safety
```bash
# Query: "ab"
# Expected: Limited results (prefix_length prevents wild matches)
```

---

## 📝 Interview Talking Points

### **When asked about search optimization:**

1. **Multi-layer approach**: "I implemented a 4-layer relevance strategy: field boosting, exact match priority, recency boost, and safe fuzzy search."

2. **Gauss decay**: "I use a gauss decay function for time-based relevance, which softly boosts recent prescriptions without overpowering exact matches."

3. **Safe fuzzy**: "I configured fuzzy search with prefix_length=2 and max_expansions=50 to prevent performance issues and wild matches."

4. **Explainability**: "I use the _explain parameter to debug and validate ranking decisions during development."

5. **Production-ready**: "The implementation includes user-scoped filtering, pagination, multiple sort options, and graceful error handling."

---

## 🔧 Configuration

### **Environment Variables**
```bash
ELASTICSEARCH_ENABLED=true
ELASTICSEARCH_HOST=http://localhost:9200
```

### **Index Settings**
- **Alias**: `prescriptions_current`
- **Field Types**: `search_as_you_type` for autocomplete
- **Date Field**: `created_at` for recency boost

---

## 📚 Additional Resources

### **Elasticsearch Documentation**
- [Function Score Query](https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-function-score-query.html)
- [Decay Functions](https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-function-score-query.html#function-decay)
- [Match Phrase Query](https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-match-query-phrase.html)
- [Fuzzy Query](https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-fuzzy-query.html)

### **Best Practices**
1. Always test relevance with real data
2. Use `_explain` for debugging
3. Monitor query performance
4. Adjust boost values based on user feedback
5. Keep fuzzy search parameters conservative

---

## 🎓 Final Notes

This implementation balances:
- **Relevance** (exact matches win)
- **Recency** (newer prescriptions boosted)
- **Performance** (safe fuzzy limits)
- **User Experience** (fast autocomplete)

All layers work together to provide the best possible search experience for medical prescription data.
