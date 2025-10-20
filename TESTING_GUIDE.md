# Testing Guide for Hybrid Travel Assistant v2.0

## Test Queries to Run

### Test 1: Romantic Itinerary (Intent Detection)
**Query**: "create a romantic 4 day itinerary for Vietnam"

**Expected Behavior**:
- Should detect "romantic" style
- Keywords: romantic, lanterns, heritage, scenic
- Should prioritize: Hoi An, Da Lat
- Should include restaurants and hotels
- 4-day structured itinerary
- WHY explanations for each location

**Performance Target**:
- First run: ~12s
- Cached run: ~7s
- Cache hit on repeated query

---

### Test 2: Adventure Travel (Style Detection)
**Query**: "best adventure activities in Vietnam for trekking"

**Expected Behavior**:
- Should detect "adventure" style
- Keywords: mountain, trekking, adventure, nature
- Should prioritize: Sapa, mountain activities
- Should mention trekking tours
- Activity-focused recommendations

**Performance Target**:
- First run: ~10-12s
- Should use cached embedding if query repeated

---

### Test 3: Food & Cuisine (Category Detection)
**Query**: "where can I find the best Vietnamese food and street markets"

**Expected Behavior**:
- Should detect "food" style
- Keywords: food, cuisine, restaurant, market
- Should prioritize restaurants and markets
- Specific dish recommendations
- Market locations (Hanoi, Ho Chi Minh City)

**Performance Target**:
- ~10-12s first run
- Better fact ranking for food-related content

---

### Test 4: Beach Destinations (Style Detection)
**Query**: "recommend beach destinations and coastal areas in Vietnam"

**Expected Behavior**:
- Should detect "beach" style
- Keywords: beach, coast, cruise, island
- Should prioritize: Nha Trang, Ha Long Bay, Da Nang
- Beach activities mentioned
- Coastal travel tips

**Performance Target**:
- ~10-12s
- High relevance scores for beach-related nodes

---

### Test 5: Cultural Heritage (Style Detection)
**Query**: "I want to explore Vietnamese culture and historical temples"

**Expected Behavior**:
- Should detect "culture" style
- Keywords: culture, heritage, history, temple, museum
- Should prioritize: Hue, Hanoi, historical sites
- Temple and museum recommendations
- Historical context included

**Performance Target**:
- ~10-12s
- Relevant cultural content prioritized

---

### Test 6: Duration Detection
**Query**: "plan a 10 day comprehensive tour of Vietnam"

**Expected Behavior**:
- Should detect "10 day" duration
- Should structure itinerary across 10 days
- Coverage of North, Central, South Vietnam
- Logical routing and connections
- Travel time considerations

**Performance Target**:
- ~12-15s (longer response)
- Well-structured 10-day plan

---

### Test 7: Repeat Query (Cache Test)
**Repeat any previous query exactly**

**Expected Behavior**:
- Embedding generation: 0.0s (cache hit)
- Cache size should increase by 1 (if new query)
- Should not increase for exact repeat
- Significant speedup overall

**Performance Target**:
- ~7s total (vs ~12s first time)
- "Cache size: X embeddings cached" shown

---

### Test 8: Error Recovery (Connection Test)
**Wait 2-3 minutes without activity, then query**

**Query**: "what are the most visited places in Vietnam"

**Expected Behavior**:
- Should handle Neo4j connection timeout gracefully
- Should retry up to 3 times
- Should show retry messages
- Should eventually succeed or fallback gracefully
- NO CRASH

**Performance Target**:
- May take longer due to retries (15-20s)
- Should complete successfully

---

### Test 9: Simple Query (Performance)
**Query**: "tell me about Hanoi"

**Expected Behavior**:
- Quick, focused response about Hanoi
- Should retrieve relevant Hanoi-related facts
- Brief but informative
- City overview with highlights

**Performance Target**:
- ~8-10s
- Efficient retrieval

---

### Test 10: Complex Multi-Part Query
**Query**: "I want a romantic 7 day trip focusing on culture and food with beach relaxation"

**Expected Behavior**:
- Should detect multiple styles: romantic, culture, food, beach
- Should balance all requirements
- 7-day structure
- Mix of cultural sites, restaurants, and beaches
- Logical flow and connections

**Performance Target**:
- ~12-15s
- Well-balanced recommendations

---

## What to Check During Testing

### Performance Metrics
- [ ] Embedding generation time (should be 0.0s on repeats)
- [ ] Pinecone search time (~0.2-1.5s)
- [ ] Neo4j query time (~0.6-2s)
- [ ] OpenAI generation time (~5-7s)
- [ ] Total time (~7-15s depending on cache)
- [ ] Cache size increasing appropriately

### Response Quality
- [ ] Professional summary at start
- [ ] Day-by-day structure for itineraries
- [ ] Actual place names (not just IDs)
- [ ] WHY explanations included
- [ ] Practical tips (transportation, timing)
- [ ] No generic "Attraction 250" style names
- [ ] Relevant to query intent

### Error Handling
- [ ] No crashes on connection timeout
- [ ] Retry messages shown if needed
- [ ] Graceful degradation if all retries fail
- [ ] Clean exit on Ctrl+C
- [ ] Resource cleanup on exit

### Intent Detection (Check Debug Output)
- [ ] "Detected travel style: romantic" for romantic queries
- [ ] "Trip duration: X days" for duration queries
- [ ] Keywords extracted appropriately
- [ ] Fact ranking working (relevant facts prioritized)

### Cache Behavior
- [ ] First query of same text: generates embedding
- [ ] Second query of same text: 0.0s embedding
- [ ] Cache size increases with unique queries
- [ ] Cache size stable for repeated queries

---

## Expected Output Format

```
============================================================
ENHANCED HYBRID TRAVEL ASSISTANT v2.0
Features: Async | Caching | Error Handling | Retry Logic
============================================================

Type your question or 'exit' to quit.

Your travel question: [YOUR QUERY]

Processing your request...
DEBUG: Pinecone results: 5
DEBUG: Graph facts: 20

============================================================
ANSWER
============================================================

[PROFESSIONAL SUMMARY]

### Day 1: [Location]
- [Activity with details]
- Why: [Explanation]

### Day 2: [Location]
...

[PRACTICAL TIPS]

============================================================
PERFORMANCE METRICS
============================================================
Embedding generation: 0.0s
Pinecone search: 0.241s
Neo4j graph query: 0.633s
OpenAI generation: 6.241s
Total time: 7.114s
Results: 5 vector matches, 20 graph facts
Cache size: 3 embeddings cached
============================================================
```

---

## Troubleshooting

### If Neo4j Connection Fails
- Check Neo4j Aura is running
- Verify credentials in config.py
- Check internet connection
- Wait for automatic retry (3 attempts)

### If Pinecone Fails
- Verify API key is valid
- Check index exists
- Verify internet connection
- Should retry automatically

### If OpenAI Fails
- Check API key is valid
- Verify quota/billing
- Check for rate limits
- Should retry automatically

### If Response is Slow
- First query is always slower
- Check individual component times
- OpenAI generation is expected bottleneck (6s+)
- Network latency affects all APIs

---

## Success Criteria

### Phase 2 Complete When:
- [x] All 10 test queries work correctly
- [x] Cache working (0.0s on repeats)
- [x] Error recovery working (no crashes)
- [x] Intent detection working
- [x] Fact ranking improving relevance
- [x] Performance metrics showing
- [x] Professional responses generated
- [x] improvements.md created

### Ready for Submission When:
- [ ] All tests pass
- [ ] Documentation complete
- [ ] Screenshots taken
- [ ] Performance verified
- [ ] Quality validated
- [ ] Error handling confirmed

---

## Commands to Run

```bash
# Activate conda environment
conda activate blue

# Run the enhanced system
python hybrid_chat.py

# Test queries one by one
# Use the 10 queries above
# Note the performance metrics
# Check cache behavior
# Verify error handling
```

---

## Notes

- Run queries in order for best demonstration
- Wait 2-3 minutes before Test 8 to simulate timeout
- Take screenshots of interesting results
- Note any unexpected behavior
- Compare quality to original system
- Track performance improvements
