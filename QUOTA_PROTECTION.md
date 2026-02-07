# Quota Protection System

## ✅ Fixed Issues

### 1. Image Serialization Error
**Problem:** `Object of type Image is not JSON serializable`
**Fix:** Modified `_get_prompt_hash()` to detect PIL Image objects and convert them to `<IMAGE:(width,height)>` placeholders before hashing.

### 2. Multiple API Calls Per Request
**Root Cause:** System makes 4-5 sequential Gemini calls per single user request:
- Image Validator (1 call)
- Device Detector (1 call)  
- Query Parser (1 call)
- Spatial Mapper (1 call, conditional)
- Step Generator (1 call)

**Reality:** Even with 5 calls/minute limit, a single request exhausts quota instantly.

## 🛡️ Quota Protection Features

### Task 1: Smart Retry Policy
- **Never retry:** 429, RESOURCE_EXHAUSTED, quota errors
- **Retry once:** timeouts, 5xx errors only
- **Max retries:** 1 (down from 3)

### Task 2: Circuit Breaker
- Global `GEMINI_DISABLED` flag
- Trips on first quota error
- All future requests return structured error
- Reset only on server restart (or via admin endpoint)

### Task 3: Rate Limiter
- Sliding window: 5 calls per 60 seconds
- Blocks **before** calling Gemini API
- Returns: `429: Local rate limit exceeded`

### Task 4: Response Cache
- In-memory cache with SHA-256 prompt hashing
- TTL: 5 minutes
- Handles PIL Image objects in prompts
- Skips API call entirely on cache hit

### Task 5: Deterministic UX
```json
{
  "error": "AI temporarily unavailable (free tier quota reached)",
  "retry_after": "tomorrow"
}
```
No stack traces, no raw errors.

### Task 6: Single-Call Guarantee
- Each backend request → at most 1 Gemini call per agent
- No internal loops or hidden retries
- **Reality:** 4-5 calls per request (architectural)

## 📊 Monitoring

### Check Quota Status
```bash
GET /api/quota-status
```

Response:
```json
{
  "circuit_breaker_active": false,
  "total_calls_this_session": 42,
  "calls_in_last_minute": 3,
  "rate_limit_remaining": 2,
  "cache_size": 8,
  "status": "active"
}
```

### Reset Circuit Breaker (Admin Only)
```bash
POST /api/reset-quota
admin_key=fixit-admin-2026
```

## 🔍 Logging

Enhanced logging tracks every API call:
```
📊 API Call #42 | Rate: 3/5 in last 60s
❌ QUOTA EXHAUSTED - Activating circuit breaker
🚫 CIRCUIT BREAKER ACTIVE - Request rejected
```

## ⚠️ Known Limitations

1. **Architecture requires 4-5 calls per request** - This is by design for the multi-agent pipeline
2. **Rate limit (5/min) allows ~1 user request per minute** - Free tier constraint
3. **Cache only helps repeated identical queries** - Rare in troubleshooting scenarios
4. **Circuit breaker is global** - One quota exhaustion blocks all users until restart

## 💡 Recommendations

For production:
- Reduce agent calls (merge validator + detector)
- Add user-specific rate limiting
- Use Redis for distributed cache
- Implement progressive degradation (use cached device data, skip spatial)
- Add fallback to simpler models
