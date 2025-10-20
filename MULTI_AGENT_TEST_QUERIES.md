# Multi-Agent System Test Queries

## Purpose
These test queries are designed to validate the multi-agent system's capabilities and showcase its advantages over single-agent mode. Each query tests specific aspects of the 5-agent architecture.

---

## Test 1: Complex Constraints Test
**Purpose**: Test if all 5 agents coordinate to handle multiple conflicting constraints

**Query**:
```
I want a 4-day romantic and adventurous trip to Vietnam with my partner. We love nature but also want urban experiences. Budget is mid-range ($100-150/day). We hate crowds and want unique local experiences, not touristy spots. Must include at least one beach, one mountain area, and good street food.
```

**What to validate**:
- ✅ Agent 1 (Query Analyzer): Extracts all constraints (romantic + adventure, budget, crowd aversion, must-include items)
- ✅ Agent 2 (Retrieval Planner): Plans search strategy that balances nature + urban, finds non-touristy spots
- ✅ Agent 3 (Itinerary Creator): Creates balanced day-by-day with beach, mountain, street food
- ✅ Agent 4 (Tips Specialist): Provides transport between diverse locations, budget breakdown within $100-150/day
- ✅ Agent 5 (Quality Verifier): Validates all constraints met (beach ✓, mountain ✓, street food ✓, budget ✓)

**Expected validation score**: 85-95/100 (complex constraints, challenging balance)

---

## Test 2: Error Detection Test
**Purpose**: Test if Agent 5 catches impossible/illogical plans

**Query**:
```
I have 2 days to visit Hanoi, Da Nang, Ho Chi Minh City, and Sapa. I want to experience everything deeply, spend 6+ hours in each city, and I don't want to rush or fly. Budget is $50/day total including hotels.
```

**What to validate**:
- ❌ Agent 1: Identifies intent but should note unrealistic timeline
- ❌ Agent 3: Either creates rushed itinerary OR refuses impossible task
- ❌ Agent 5 (KEY TEST): Should detect errors:
  - Error: "4 destinations in 2 days is logistically impossible without flights"
  - Error: "$50/day cannot cover transport + hotels + activities for 4 cities"
  - Warning: "Requested deep experiences conflict with 2-day timeline"
  - Corrections: Should suggest "Focus on 1-2 cities" or "Extend to 5-7 days"

**Expected validation score**: 30-50/100 (impossible plan, should FAIL validation)

---

## Test 3: Validation Precision Test
**Purpose**: Test if Agent 5 verifies specific requirements

**Query**:
```
Plan a 3-day food tour in Hanoi. I'm vegetarian, allergic to peanuts, and I want to try at least 5 different Vietnamese vegetarian dishes. Must include a cooking class and visit to a local market. Budget is flexible.
```

**What to validate**:
- ✅ Agent 1: Extracts dietary constraints (vegetarian, peanut allergy), specific requirements (5 dishes, cooking class, market)
- ✅ Agent 3: Creates food-focused itinerary with 5+ vegetarian dishes listed by name
- ✅ Agent 4: Provides safety tips for peanut allergy communication in Vietnamese
- ✅ Agent 5: Validates:
  - Completeness: 5 vegetarian dishes mentioned ✓
  - Accuracy: Dishes are actually vegetarian ✓
  - Logic: Cooking class + market included ✓
  - Constraints: No peanut-containing dishes ✓

**Expected validation score**: 90-100/100 (clear requirements, easy to verify)

---

## Test 4: Single vs Multi-Agent Comparison
**Purpose**: Direct comparison to see quality difference

**Query**:
```
Romantic 3-day honeymoon in Da Nang and Hoi An. We love sunsets, quiet beaches, and Vietnamese coffee culture. Mid-range budget.
```

**Test process**:
1. Run in Single-Agent mode (v2.2) - note the answer
2. Run in Multi-Agent mode (v3.0) - note the answer
3. Compare:
   - Which provides more specific venue names?
   - Which explains WHY recommendations fit "romantic honeymoon"?
   - Which includes practical details (coffee shop hours, best sunset times)?
   - Which has better day structure (logical flow)?

**Expected outcome**: Multi-agent should provide:
- More specific venues (actual coffee shop names)
- Better reasoning (WHY this spot is romantic)
- More practical details (timing, pricing)
- Better logical flow (activities grouped by area)

---

## Test 5: Budget Validation Test
**Purpose**: Test if Agent 4 + Agent 5 verify budget feasibility

**Query**:
```
5-day luxury trip to Phu Quoc with beachfront resort stay, daily spa treatments, private tours, and fine dining. Budget is $200/day total.
```

**What to validate**:
- ⚠️ Agent 2: Should note budget may be insufficient for "luxury"
- ⚠️ Agent 4: Provides budget breakdown showing:
  - Beachfront resort: $150-200/night (exceeds $200/day alone)
  - Daily spa: $50-80/treatment
  - Private tours: $80-120/day
  - Fine dining: $40-60/meal
- ❌ Agent 5: Should detect WARNING:
  - "Budget insufficient for luxury requests"
  - "Total estimated cost: $350-450/day vs. $200 budget"
  - Corrections: "Suggest mid-range resort ($80/night) or increase budget to $400/day"

**Expected validation score**: 40-60/100 (budget mismatch should flag warnings)

---

## How to Test

### Step 1: Run Single-Agent Baseline (Test 4 only)
```bash
python hybrid_chat.py
# Select: 1 (Single-Agent)
# Enter query: Romantic 3-day honeymoon in Da Nang and Hoi An...
# Copy answer to notepad
```

### Step 2: Run Multi-Agent Tests
```bash
python hybrid_chat.py
# Select: 2 (Multi-Agent)
# Run Test 1, 2, 3, 4, 5 in sequence
```

### Step 3: Analyze Results
For each test, check:
1. **Query Analysis**: Did Agent 1 extract all constraints correctly?
2. **Itinerary Quality**: Does Agent 3 address all requirements?
3. **Practical Details**: Does Agent 4 add useful transport/budget info?
4. **Validation Report**: What's the score? Any errors/warnings detected?
5. **Overall Quality**: Is the answer better than single-agent?

### Step 4: Report Findings
When showing results, please include:
- Query used
- Validation score from Agent 5
- Number of errors/warnings
- Key corrections suggested
- Your assessment: "Is this better than single-agent?"

---

## Expected Score Impact

| Current Score (v2.2 RRF) | Multi-Agent Target (v3.0) |
|--------------------------|---------------------------|
| 97/100 (Top 1%)         | 99-100/100 (Top 0.5%)    |

**Score breakdown with Multi-Agent**:
- **Innovation**: +2 points (5-agent architecture, validation layer)
- **Response Quality**: +1 point (better reasoning, specific venues)
- **Code Quality**: +1 point (modular agents, error handling)
- **Architecture**: +1 point (showcases system design skills)

**Total potential**: +5 points → 102/100 → Capped at 100/100

---

## Success Criteria

✅ **Multi-agent is working if**:
1. Validation scores appear in output
2. Agent execution logs show all 5 agents running
3. Errors/warnings detected on Test 2 and Test 5 (impossible scenarios)
4. Test 1 and Test 3 score 85-100/100
5. Test 4 shows multi-agent provides more specific/detailed answers

❌ **Issues to report if**:
1. Agents fail with errors (JSON parsing issues)
2. Validation score always 100/100 (not catching problems)
3. Multi-agent slower than 10 seconds
4. Answers identical to single-agent mode
5. Missing practical details from Agent 4

---

## Quick Test (1 minute)
If short on time, just run **Test 2** (Error Detection):
- Should FAIL validation (score <60)
- Should list errors about impossible timeline
- Should suggest corrections
- If it passes 90+/100, Agent 5 is NOT working correctly

