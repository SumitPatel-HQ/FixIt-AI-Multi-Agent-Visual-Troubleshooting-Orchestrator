# RPD Optimization Summary

## Current Architecture

### API Call Reduction
- **Before**: 5 sequential calls per request (25 RPD)
  1. Image Validation (5 RPD)
  2. Device Detection (5 RPD)
  3. Query Parsing (5 RPD)
  4. Spatial Mapping (5 RPD)
  5. Step Generation (5 RPD)

- **After**: 2-3 calls per request (10-15 RPD)
  1. Combined Analysis (Gates 1-3) (5 RPD) ✅
  2. Spatial Mapping (5 RPD) - conditional ✅
  3. Step Generation (5 RPD) - conditional ✅

### RPD Savings Per Request Type

| Request Type | Old RPD Cost | New RPD Cost | Savings |
|--------------|--------------|--------------|---------|
| Simple Locate ("where is X?") | 25 | 10 | **15 RPD** |
| Troubleshoot (no spatial) | 25 | 15 | **10 RPD** |
| Full Pipeline | 25 | 15 | **10 RPD** |

## Quota Protection Features

### 1. Circuit Breaker ✅
- Trips on first quota error
- Blocks all future requests until server restart
- Returns structured error: `{"error": "AI temporarily unavailable", "retry_after": "tomorrow"}`

### 2. Rate Limiter ✅
- 5 calls per 60-second sliding window
- Blocks BEFORE calling Gemini API
- Returns: `429: Local rate limit exceeded`

### 3. Response Caching ✅
- 5-minute TTL
- SHA-256 prompt hashing
- Handles PIL Image objects
- Skips API call entirely on cache hit

### 4. RPD Budget Tracking ✅
- Tracks: 5 RPD per call
- Daily limit: 20 RPD (free tier)
- Warnings when ≤5 RPD remaining
- Exposed via `/api/quota-status`

### 5. Smart Retry Logic ✅
- **Never retry**: 429, RESOURCE_EXHAUSTED, quota errors
- **Retry once**: timeouts, 5xx errors
- Max retries: 1

### 6. Conditional Step Generation ✅
- Skips steps for simple "where is X?" queries
- Always generates steps for action verbs (remove, replace, install, repair, fix)
- Explicit logic: `needs_steps == False AND query_type == "locate" AND no_action_verb`

## Current RPD Budget

Check anytime via:
```bash
GET /api/quota-status
```

Response:
```json
{
  "circuit_breaker_active": false,
  "total_calls_this_session": 12,
  "calls_in_last_minute": 2,
  "rate_limit_remaining": 3,
  "rpd_consumed": 60,
  "rpd_remaining": -40,
  "rpd_budget_percent": 300,
  "cache_size": 4,
  "status": "active"
}
```

## Expected Free Tier Usage

With 20 RPD daily limit:
- **Locate queries**: ~2 requests/day (10 RPD each)
- **Troubleshoot queries**: ~1-2 requests/day (15 RPD each)
- **Mixed usage**: ~1-2 requests/day

## Further Optimization Options (Not Implemented)

1. **Skip Spatial Mapping** when RPD < 10
   - Save 5 RPD per request
   - Fallback to generic location descriptions

2. **Progressive Degradation**
   - High budget: Full pipeline
   - Medium budget: Skip spatial
   - Low budget: Skip spatial + steps

3. **Cache Device Detection** by image hash
   - Reuse detection results for same device
   - Save 5 RPD on repeated uploads

4. **Upgrade to Paid Tier**
   - Unlimited RPD
   - Best long-term solution

## Logging Output

Now includes RPD tracking:
```
📊 API Call #3 | Rate: 2/5 per min | RPD: 15/20 (5 remaining)
⚠️ Low RPD budget! Only 5 RPD remaining today
```
