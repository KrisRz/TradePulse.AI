# Historical Context Support/Resistance Fix

## Problem Identified

`historical_market_context_service.py` zwraca **0 support/resistance levels** z powodu zbyt konserwatywnego algorytmu.

### Root Causes:

**1. Wymaga 2+ "touches" tego samego levelu**
- Bitcoin volatile → rzadko dotyka dokładnie tego samego punktu
- Weekend low volume → mało touches
- Tolerancja 2% ($2,440 dla $122k) → za duża dla day trading

**2. Zwraca tylko TOP 5 levels**
```python
return sorted(list(set(support_candidates)))[-5:]
```
- Day trading potrzebuje 10-20 micro-levels
- 5 strongest levels ≠ najbliższe levels dla current price

**3. Wymaga 100 candles lookahead**
```python
for j in range(i+1, min(i+100, len(df))):
```
- Weekend = mało danych
- 3-day filter (72h) + 100 candles = często brak danych

## Fix Strategy

### Option A: Relaks algorytmu (EASY, 10 min)
- Reduce touches requirement: 2 → 1
- Increase tolerance: 2% → 3% (for day trading micro-levels)
- Return TOP 10 instead of 5
- Reduce lookahead: 100 → 50 candles

### Option B: Hybrid approach (BETTER, 20 min)
- Keep strict algorithm for STRONG levels
- Add WEAK levels (1 touch, but high volume)
- Add RECENT levels (last 24h swing points)
- Combine: strong (5) + weak (5) + recent (5) = 15 levels

### Option C: Multi-method S/R (BEST, 30 min)
- Method 1: Current algorithm (historical touch points)
- Method 2: Bollinger Bands (statistical S/R)
- Method 3: Volume profile (high volume levels)
- Method 4: Fibonacci retracements (mathematical S/R)
- Combine all methods → comprehensive S/R levels

## Recommendation: Option B (Hybrid)

Best balance: Keep quality of current algorithm + add day trading relevant levels.

## Files to Change:
- `app/backend/services/historical_market_context_service.py` (lines 514-578)
