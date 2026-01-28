# 🚀 Elasticsearch Search Quick Reference

## 📌 One-Line Interview Answers

### **Layer 2: Exact Match Priority**
> "I use `match_phrase` with boost=8 before standard `match` with boost=5 to ensure exact matches always rank higher."

### **Layer 3: Recency Boost**
> "I use a gauss decay function with 30-day scale to softly boost recent prescriptions without overpowering relevance."

### **Layer 4: Safe Fuzzy**
> "I use `prefix_length=2` and `max_expansions=50` to make fuzzy search safe and performant while handling typos."

### **Debugging**
> "I use `_explain=true` to debug why documents rank the way they do and fine-tune boost values."

---

## 🎯 Relevance Strategy Summary

```
Priority: Exact match > Prefix match > Fuzzy match
Fields:   Medicine > Doctor > Hospital
Time:     Recent > Old
```

---

## 📊 Boost Values Reference

| Query Type | Medicine | Doctor | Hospital |
|------------|----------|--------|----------|
| **Exact Match** | 8 | 4 | 2 |
| **Standard Match** | 5 | 2 | 1 |
| **Fuzzy Match** | 3 | 1.5 | 1 |

---

## 🔧 Configuration Quick Ref

### **Fuzzy Parameters**
```python
"fuzziness": "AUTO"           # Auto-adjust based on term length
"prefix_length": 2            # First 2 chars must match exactly
"max_expansions": 50          # Limit term expansions
```

### **Gauss Decay Parameters**
```python
"origin": "now"               # Starting point (today)
"scale": "30d"                # 30-day boost window
"decay": 0.5                  # Slow decay rate
"score_mode": "avg"           # Average function scores
"boost_mode": "sum"           # Add to relevance score
```

---

## 🚀 API Endpoints at a Glance

```bash
# Universal Search (All layers applied)
GET /search/all?q=paracetamol&user_id=user123&page=1&sort_by=relevance

# Autocomplete (Exact match priority)
GET /search/autocomplete?q=para&user_id=user123&size=10

# Fuzzy Search (Typo tolerance)
GET /search/fuzzy?q=paracetmol&user_id=user123&page=1

# Medicine-only Search
GET /search/medicine?q=aspirin&user_id=user123&size=10

# Doctor/Hospital Search
GET /search/provider?q=apollo&user_id=user123&size=10

# Date Range Search
GET /search/date-range?q=aspirin&user_id=user123&start_date=2024-01-01&end_date=2024-12-31
```

---

## 🧪 Quick Test Commands

### **Test Exact Match Priority**
```bash
curl -X POST "http://localhost:9200/prescriptions_current/_search?pretty" \
-H 'Content-Type: application/json' \
-d '{
  "query": {
    "bool": {
      "should": [
        {"match_phrase": {"medicine_names": {"query": "paracetamol", "boost": 8}}},
        {"match": {"medicine_names": {"query": "paracetamol", "boost": 5}}}
      ]
    }
  }
}'
```

### **Test Recency Boost**
```bash
curl -X POST "http://localhost:9200/prescriptions_current/_search?pretty" \
-H 'Content-Type: application/json' \
-d '{
  "query": {
    "function_score": {
      "query": {"match_all": {}},
      "functions": [{
        "gauss": {
          "created_at": {"origin": "now", "scale": "30d", "decay": 0.5}
        }
      }],
      "score_mode": "avg",
      "boost_mode": "sum"
    }
  }
}'
```

### **Debug with Explain**
```bash
curl -X POST "http://localhost:9200/prescriptions_current/_search?explain=true&pretty" \
-H 'Content-Type: application/json' \
-d '{
  "query": {"match": {"medicine_names": "paracetamol"}}
}'
```

---

## 🎓 Code Snippets

### **Layer 2: Exact Match Priority**
```python
"should": [
    {"match_phrase": {"medicine_names": {"query": text, "boost": 8}}},
    {"match": {"medicine_names": {"query": text, "boost": 5}}}
]
```

### **Layer 3: Recency Boost**
```python
"function_score": {
    "query": {"bool": {"should": [...]}},
    "functions": [{
        "gauss": {
            "created_at": {
                "origin": "now",
                "scale": "30d",
                "decay": 0.5
            }
        }
    }],
    "score_mode": "avg",
    "boost_mode": "sum"
}
```

### **Layer 4: Safe Fuzzy**
```python
"match": {
    "medicine_names": {
        "query": text,
        "fuzziness": "AUTO",
        "prefix_length": 2,
        "max_expansions": 50,
        "boost": 3
    }
}
```

---

## 🐛 Common Issues & Fixes

### **Issue: Partial matches rank too high**
**Fix:** Add `match_phrase` with higher boost before standard `match`

### **Issue: Old prescriptions rank too high**
**Fix:** Add gauss decay function with appropriate scale (e.g., 30d)

### **Issue: Fuzzy search returns too many results**
**Fix:** Set `prefix_length=2` and `max_expansions=50`

### **Issue: Performance problems with fuzzy**
**Fix:** Reduce `max_expansions` to 30 or lower

### **Issue: Unclear why document ranks high/low**
**Fix:** Add `?explain=true` to search request

---

## 📚 Files Modified

- `AI_OCR_Service/app/services/search_indexer.py` → Core search logic
- `AI_OCR_Service/app/api/search.py` → API endpoints
- `AI_OCR_Service/ELASTICSEARCH_SEARCH_GUIDE.md` → Full documentation

---

## ✅ Implementation Checklist

- [x] Layer 1: Field-level boosting
- [x] Layer 2: Exact match priority (match_phrase)
- [x] Layer 3: Recency boost (gauss decay)
- [x] Layer 4: Safe fuzzy (prefix_length + max_expansions)
- [x] Autocomplete with exact match priority
- [x] Pagination support
- [x] Sort by relevance/date
- [x] User-scoped filtering
- [x] Error handling
- [x] Documentation

---

## 🎯 Key Takeaways

1. **Multi-layer approach** balances relevance, recency, and safety
2. **Boost hierarchy** ensures proper field and match type priority
3. **Gauss decay** boosts recent items without overpowering relevance
4. **Safe fuzzy** prevents performance issues and wild matches
5. **Explainability** helps debug and optimize search results

---

## 📖 Quick Links

- [Full Documentation](./ELASTICSEARCH_SEARCH_GUIDE.md)
- [Elasticsearch Function Score](https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-function-score-query.html)
- [Match Phrase Query](https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-match-query-phrase.html)
