# Latency Analysis Report - Fallback Mechanisms

## Executive Summary
Identified **4 critical latency issues** in the OCR and LLM extraction fallback mechanisms that cause unnecessary delays when providers fail.

---

## 1. LATENCY ISSUES IDENTIFIED

### Issue #1: Inconsistent Retry Logic in LLM Fallback
**Location:** `app/services/claude_extractor.py`

**Problem:**
- Anthropic: `max_retries=1` ✅ (Fast)
- OpenRouter: `max_retries=1` ✅ (Fast) 
- **Groq: `max_retries=2` ❌ (Slow)**

**Impact:**
When Groq is called, if it fails the first time, it will retry with exponential backoff:
- Attempt 1 fails (timeout 30s)
- Wait 2^0 = 1s
- Attempt 2 fails (timeout 30s)
- **Total latency: 61 seconds** (vs. 30s for others)

**Severity:** 🔴 HIGH - Adds unnecessary 31 second delay to fallback chain

---

### Issue #2: Long Timeout Values Cause Cascading Delays
**Location:** `app/services/claude_extractor.py` (line 17)

**Problem:**
```python
def retry_with_backoff(max_retries: int = 1, backoff_factor: float = 2.0, timeout: int = 30):
```

**Timeout Chain Latency Analysis:**

| Provider | Timeout | Retries | Max Wait | Backoff | Total |
|----------|---------|---------|----------|---------|-------|
| Anthropic | 30s | 1 | 30s | N/A | 30s |
| OpenRouter | 30s | 1 | 30s | N/A | 30s |
| Groq | 30s | 2 | 30s | 1s | 61s |

**Cascading Scenario (All providers fail):**
- OCR Chain: Gemini (30s) + Google Vision (30s) + TrOCR (varies) = **~60s+**
- Then LLM Chain: Anthropic (30s) + OpenRouter (30s) + Groq (61s) = **~121s**
- **Total worst-case: 3+ minutes**

**Severity:** 🔴 HIGH - Unacceptable user experience

---

### Issue #3: Sequential Fallback (No Parallelization)
**Location:** `app/services/vision_ocr.py` and `app/services/claude_extractor.py`

**Current Flow (Sequential):**
```
Gemini fails (30s)
  ↓
Google Vision fails (30s)
  ↓
TrOCR fails (varies)
  ↓
Anthropic fails (30s)
  ↓
OpenRouter fails (30s)
  ↓
Groq fails (61s)
```

**Problem:** Each provider waits for the previous one to fully timeout before trying next.

**Impact:** If primary providers have connection issues, user waits 60+ seconds unnecessarily.

**Severity:** 🔴 HIGH - No early failure detection

---

### Issue #4: Missing Fast-Fail Detection
**Location:** `app/services/vision_ocr.py` and `app/services/claude_extractor.py`

**Problem:** 
- No distinction between timeout and client errors
- All failures go through full retry + backoff cycles
- No fast-fail for permanent errors (API key missing, invalid auth)

**Impact:**
- Invalid credentials still retry and wait 30 seconds
- Network errors treated same as timeout errors
- No immediate fallback on 4xx errors (except claude_extractor has some handling)

**Severity:** 🟡 MEDIUM

---

## 2. ROOT CAUSE ANALYSIS

### Architecture Issues

1. **Blocking Sequential Fallback**: OCR providers are tried sequentially with full timeout waits
2. **Uniform Timeout Duration**: All providers share same 30s timeout regardless of expected latency
3. **Inconsistent Retry Policies**: Different providers have different retry counts
4. **No Health Awareness**: Fallback doesn't know which providers are healthy/slow

---

## 3. PERFORMANCE IMPACT METRICS

### Current Scenario: Primary Provider Fails
```
Expected: User sees error in ~30-40 seconds (primary timeout + error response)
Actual: User waits 121+ seconds (all fallbacks exhausted)
Regression: 3-4x slower than optimal
```

### Example Timeline (All providers fail):
```
T+0s  → Request starts
T+30s → Gemini timeout, try Google Vision
T+60s → Google Vision timeout, try TrOCR
T+90s → TrOCR fails, try Anthropic
T+120s → Anthropic timeout, try OpenRouter
T+150s → OpenRouter timeout, try Groq
T+180s → Groq timeout (first attempt)
T+181s → Wait 1s backoff
T+211s → Groq timeout (second attempt)
T+212s → All providers exhausted, return error

Total: 3.5+ minutes for user to see failure!
```

---

## 4. ARCHITECTURE CONSTRAINTS

### Current Design:
- **Sequential Processing**: By design, tries providers one at a time
- **Synchronous API Calls**: All API calls are blocking
- **No Circuit Breaker**: Failed providers aren't cached/skipped

### Must Maintain:
- Provider priority order (Gemini → Google Vision → TrOCR for OCR)
- Fast response preference (Gemini is fastest primary)
- Local fallback availability (TrOCR when no internet)
- API key flexibility (supports multiple providers)

---

## 5. RECOMMENDED SOLUTIONS

### Solution A: Fix Immediate Issues (Quick Wins)
**Effort:** ⚡ Very Low | **Impact:** 🟢 High | **Risk:** 🟢 Very Low

1. **Fix Groq retry to max_retries=1** (currently 2)
   - Reduce cascading latency by ~31 seconds
   
2. **Reduce timeout durations strategically:**
   - Gemini: 15s (API is fast)
   - Google Vision: 20s (usually responds within 10-15s)
   - TrOCR: 45s (local model, slower but can't timeout)
   - LLM APIs: 20s (extraction is faster than OCR)

### Solution B: Add Aggressive Fast-Fail Detection
**Effort:** ⚡ Low | **Impact:** 🟢 High | **Risk:** 🟡 Medium

1. Detect client errors (4xx) immediately without retry
2. Skip retries for authentication failures
3. Log provider health for monitoring

### Solution C: Timeout Staggering (Medium-term)
**Effort:** ⚡⚡ Medium | **Impact:** 🟡 Medium | **Risk:** 🟡 Medium

1. Different timeout strategies per provider:
   - API-based providers: aggressive timeouts (15s)
   - Local models: generous timeouts (60s)

### Solution D: Optional Future - Parallel Probing (Advanced)
**Effort:** ⚡⚡⚡ High | **Impact:** 🟢 Very High | **Risk:** 🔴 High

1. Start second provider after 5s if primary is slow
2. Return first successful response
3. Requires async refactoring

---

## 6. RECOMMENDED APPROACH

**Implement Solutions A + B** for optimal results:

1. **Immediate (5 min):** Fix Groq retry inconsistency
2. **Quick (15 min):** Optimize timeout values per provider
3. **Monitor (ongoing):** Log provider performance metrics
4. **Future:** Consider async parallel attempts if latency still an issue

**Expected Improvement:**
- Best case (primary succeeds): No change (~30s)
- Worst case (all fail): **180s → 90s** (50% reduction)
- Typical fallback scenario: **30-60s** vs current 90-120s

---

## 7. IMPLEMENTATION ORDER

### Phase 1: Fix Inconsistencies (5 min)
- [ ] Reduce Groq max_retries from 2 → 1
- [ ] Align all LLM providers to same retry logic

### Phase 2: Optimize Timeouts (10 min)
- [ ] Update Gemini timeout: 30s → 15s
- [ ] Update Google Vision timeout: 30s → 20s
- [ ] Update LLM timeouts: 30s → 20s
- [ ] Keep TrOCR timeout: 45s (local model)

### Phase 3: Smart Error Handling (15 min)
- [ ] Add immediate fail-fast for authentication errors
- [ ] Skip retries on 4xx client errors (already partial in claude_extractor)
- [ ] Log provider error types for monitoring

### Phase 4: Monitoring (Optional)
- [ ] Add latency metrics per provider
- [ ] Track success rates by provider
- [ ] Alert if provider response times degrade

---
