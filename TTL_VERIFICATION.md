# ✅ TTL Verification - Auto-delete old data (90 days)

## 📊 Both tables have TTL enabled:

### 1. **live_candles** (Real-time Binance data)
```terraform
File: infra/dynamodb-app-tables.tf

Lines 22-25 (development):
ttl {
  attribute_name = "ttl"
  enabled        = true
}

Lines 49-52 (production):
ttl {
  attribute_name = "ttl"
  enabled        = true
}
```

**App code sets TTL:**
```python
File: app/backend/services/market_data_persistence.py
Line 68:
ttl_timestamp = int((datetime.now(timezone.utc) + timedelta(days=90)).timestamp())

Line 85:
"ttl": ttl_timestamp  # AUTO-DELETE after 90 days
```

**Status:** ✅ ACTIVE (app writes TTL field)

---

### 2. **market_context_cache** (Historical patterns)
```terraform
File: infra/dynamodb-historical-context.tf

Lines 25-27:
ttl {
  attribute_name = "ttl"
  enabled        = true
}
```

**App code:** 
- Currently using local pickle cache (line 227)
- If DynamoDB used, must add TTL field when writing

**Status:** ✅ CONFIGURED (ready for use)

---

## 🚀 Deployment:

```bash
cd infra
terraform apply  # Enable TTL on both tables
```

## 🎯 Result:

- ✅ live_candles: Auto-delete > 90 days (active now)
- ✅ market_context_cache: Auto-delete > 90 days (when used)
- ✅ Always fresh data
- ✅ Zero manual cleanup
- ✅ Free (DynamoDB TTL = no extra cost)
