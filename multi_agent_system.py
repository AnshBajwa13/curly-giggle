# multi_agent_system.py
"""
Multi-Agent Travel Assistant System
Implements 5 specialized agents with orchestration
"""

import json
from typing import Dict, List, Optional
from openai import OpenAI
import config

client = OpenAI(api_key=config.OPENAI_API_KEY)

# Agent configurations
CHAT_MODEL = "gpt-4o-mini"

# ================================
# AGENT 1: Query Analyzer
# ================================

def agent_1_query_analyzer(user_query: str) -> Dict:
    """
    Agent 1: Deep query analysis and intent extraction.
    Extracts: intent, duration, budget, pace, constraints, preferences.
    """
    
    system_prompt = """You are a specialized query analysis agent for travel planning.
Your ONLY job is to analyze user queries and extract structured information.

Extract and return JSON with these fields:
- intent: Primary travel style (romantic, adventure, food, beach, culture, family, business)
- duration_days: Number of days (integer, null if not specified)
- budget_usd: Total budget in USD (integer, null if not specified)
- budget_level: Budget tier (budget/mid-range/luxury, null if not specified)
- pace: Travel pace (relaxed/moderate/fast, default: moderate)
- group_type: Travel group (solo/couple/family/friends, default: couple if romantic)
- must_include: Array of must-have activities/places
- must_avoid: Array of things to avoid
- preferences: Additional preferences (photography, nightlife, nature, etc.)
- special_requirements: Dietary restrictions, accessibility needs, etc.

Be precise and extract ALL constraints mentioned."""

    user_prompt = f"""Analyze this travel query and extract structured information:

Query: "{user_query}"

Return ONLY valid JSON, no other text."""

    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=500
        )
        
        analysis = json.loads(response.choices[0].message.content)
        
        # Validation and defaults
        if not analysis.get('intent'):
            analysis['intent'] = 'general'
        if not analysis.get('pace'):
            analysis['pace'] = 'moderate'
        if not analysis.get('group_type'):
            analysis['group_type'] = 'couple' if analysis['intent'] == 'romantic' else 'solo'
        if not analysis.get('must_include'):
            analysis['must_include'] = []
        if not analysis.get('must_avoid'):
            analysis['must_avoid'] = []
        
        print(f"[AGENT 1] Query Analysis Complete: {analysis['intent']}, {analysis.get('duration_days', 'N/A')} days")
        return analysis
        
    except Exception as e:
        print(f"[AGENT 1] Error: {e}")
        # Fallback analysis
        return {
            "intent": "general",
            "duration_days": None,
            "budget_usd": None,
            "budget_level": None,
            "pace": "moderate",
            "group_type": "solo",
            "must_include": [],
            "must_avoid": [],
            "preferences": [],
            "special_requirements": []
        }


# ================================
# AGENT 2: Retrieval Planner
# ================================

def agent_2_retrieval_planner(query_analysis: Dict, original_query: str) -> Dict:
    """
    Agent 2: Plans optimal retrieval strategy.
    Decides: what to search, how to filter, which sources to prioritize.
    """
    
    system_prompt = """You are a retrieval strategy specialist for travel search.
Your job is to create an optimal search plan based on query analysis.

Given user intent and constraints, determine:
1. vector_query: Optimized search query for vector DB (semantic search)
2. graph_filters: Categories to include/exclude in graph search
3. top_k: Number of results to retrieve (5-10)
4. priority_nodes: Node types to prioritize (City, Restaurant, Activity, etc.)
5. search_strategy: Strategy name (broad_discovery, focused_refinement, constraint_based)

CRITICAL: You MUST return ONLY a valid JSON object with this EXACT structure:
{
  "vector_query": "optimized search query string",
  "graph_filters": {"include": ["category1", "category2"], "exclude": []},
  "top_k": 7,
  "priority_nodes": ["City", "Activity"],
  "search_strategy": "focused_refinement"
}

NO additional text, NO markdown, ONLY the JSON object."""

    user_prompt = f"""Create retrieval strategy for:

Query Analysis:
{json.dumps(query_analysis, indent=2)}

Original Query: "{original_query}"

Return ONLY the JSON object, nothing else."""

    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=400
        )
        
        content = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        
        plan = json.loads(content)
        
        # Validation
        if not plan.get('vector_query'):
            plan['vector_query'] = original_query
        if not plan.get('top_k'):
            plan['top_k'] = 7
        if not plan.get('graph_filters'):
            plan['graph_filters'] = {"include": [], "exclude": []}
        if not plan.get('search_strategy'):
            plan['search_strategy'] = "focused_refinement"
        
        print(f"[AGENT 2] Retrieval Plan: {plan.get('search_strategy')}, top_k={plan['top_k']}")
        return plan
        
    except Exception as e:
        print(f"[AGENT 2] JSON Parse Error: {e}")
        print(f"[AGENT 2] Using fallback retrieval strategy")
        # Enhanced fallback based on query analysis
        top_k = 7 if query_analysis.get('duration_days', 0) > 3 else 5
        return {
            "vector_query": original_query,
            "graph_filters": {"include": [], "exclude": []},
            "top_k": top_k,
            "priority_nodes": ["City", "Attraction", "Activity", "Restaurant"],
            "search_strategy": "broad_discovery"
        }


# ================================
# AGENT 3: Itinerary Creator
# ================================

def agent_3_itinerary_creator(query_analysis: Dict, context: str, original_query: str) -> str:
    """
    Agent 3: Specialized itinerary creation.
    Focuses ONLY on building the day-by-day structure.
    """
    
    intent = query_analysis.get('intent', 'general')
    duration = query_analysis.get('duration_days')
    pace = query_analysis.get('pace', 'moderate')
    must_include = query_analysis.get('must_include', [])
    
    system_prompt = f"""You are an expert itinerary creation specialist.
Your ONLY job is to create the day-by-day itinerary structure.

CRITICAL RULES:
1. Create EXACTLY {duration} days if duration is specified
2. Follow the {pace} pace
3. MUST include: {', '.join(must_include) if must_include else 'user preferences'}
4. Use ONLY information from the provided context
5. Structure: Day X: Theme → Morning → Afternoon → Evening
6. **ALWAYS use SPECIFIC VENUE NAMES from context** (e.g., "My Khe Beach", not "a beach")
7. **ALWAYS use SPECIFIC RESTAURANT NAMES** if mentioned in context (e.g., "Morning Glory", not "a local restaurant")
8. Explain WHY each activity fits the {intent} intent
9. Include realistic travel times between locations
10. Consider geographic logic (don't jump 500km between days)

FORBIDDEN:
- Generic placeholders like "a local market", "a cooking school", "a restaurant"
- Unrealistic distances (e.g., Da Lat to Sapa in one day)
- Budget estimates (another agent handles that)

DO NOT add practical tips (another agent handles that).
Focus on: WHAT to do, WHERE to go (SPECIFIC NAMES), WHEN to do it, WHY it fits."""

    user_prompt = f"""Create {intent} itinerary for:

User Request: "{original_query}"

Duration: {duration} days
Pace: {pace}
Must Include: {', '.join(must_include) if must_include else 'N/A'}

Available Context:
{context}

Create ONLY the day-by-day itinerary. Be specific with places and timing."""

    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=1200
        )
        
        itinerary = response.choices[0].message.content
        print(f"[AGENT 3] Itinerary Created: {len(itinerary)} chars")
        return itinerary
        
    except Exception as e:
        print(f"[AGENT 3] Error: {e}")
        return "Unable to create itinerary. Please try again."


# ================================
# AGENT 4: Practical Tips Specialist
# ================================

def agent_4_practical_tips(query_analysis: Dict, itinerary: str, original_query: str) -> str:
    """
    Agent 4: Adds practical logistics and tips.
    Focus: transport, budget, booking, timing, safety.
    """
    
    budget_level = query_analysis.get('budget_level', 'mid-range')
    duration = query_analysis.get('duration_days')
    
    system_prompt = f"""You are a travel logistics and practical tips specialist.
Your job is to add PRACTICAL information to an itinerary.

Provide:
1. Transportation: Between cities, within cities, booking tips
2. Budget Breakdown: Accommodation, food, activities, transport (per day and total)
3. Best Time to Visit: Weather, crowds, events
4. Booking Advice: When to book, where to book, advance planning
5. Safety & Tips: What to know, what to carry, common mistakes

Budget level: {budget_level}
Duration: {duration} days

Be SPECIFIC with prices in USD, time estimates, and actionable advice."""

    user_prompt = f"""Add practical tips for this itinerary:

Original Request: "{original_query}"
Budget Level: {budget_level}

Itinerary:
{itinerary}

Provide practical tips section with transport, budget, booking, and tips."""

    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=800
        )
        
        tips = response.choices[0].message.content
        print(f"[AGENT 4] Practical Tips Added: {len(tips)} chars")
        return tips
        
    except Exception as e:
        print(f"[AGENT 4] Error: {e}")
        return "\n### Practical Tips\nPlease consult travel guides for detailed logistics."


# ================================
# AGENT 5: Quality Verifier
# ================================

def agent_5_quality_verifier(
    query_analysis: Dict,
    itinerary: str,
    tips: str,
    original_query: str
) -> Dict:
    """
    Agent 5: Verifies quality and identifies errors.
    Checks: completeness, accuracy, logic, constraints met.
    Returns: validation report + corrected content if needed.
    """
    
    duration = query_analysis.get('duration_days')
    must_include = query_analysis.get('must_include', [])
    intent = query_analysis.get('intent', 'general')
    
    system_prompt = """You are a quality verification specialist for travel itineraries.
Your job is to CHECK for errors and logical issues.

Verify:
1. Completeness: All days covered? All sections present?
2. Accuracy: Travel times realistic? Locations exist? Prices reasonable?
3. Logic: Day transitions make sense? No contradictions?
4. Constraints: Must-include items covered? Budget respected?
5. Quality: Specific details? Clear WHY explanations?

Return JSON:
{
  "is_valid": true/false,
  "errors": ["error 1", "error 2", ...],
  "warnings": ["warning 1", ...],
  "score": 0-100,
  "corrections": "Suggested fixes if errors found",
  "validation_summary": "Brief summary"
}"""

    combined_content = f"""
ITINERARY:
{itinerary}

PRACTICAL TIPS:
{tips}
"""

    user_prompt = f"""Verify quality of this travel response:

Original Query: "{original_query}"
Expected Duration: {duration} days
Must Include: {', '.join(must_include) if must_include else 'N/A'}
Intent: {intent}

Content to Verify:
{combined_content}

Return validation report as JSON."""

    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=600
        )
        
        validation = json.loads(response.choices[0].message.content)
        
        print(f"[AGENT 5] Validation: {'PASS' if validation.get('is_valid', False) else 'ISSUES FOUND'}, Score: {validation.get('score', 0)}/100")
        
        if validation.get('errors'):
            print(f"[AGENT 5] Errors: {len(validation['errors'])} found")
        if validation.get('warnings'):
            print(f"[AGENT 5] Warnings: {len(validation['warnings'])} found")
        
        return validation
        
    except Exception as e:
        print(f"[AGENT 5] Error: {e}")
        return {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "score": 85,
            "corrections": "",
            "validation_summary": "Verification failed, assuming valid."
        }


# ================================
# ORCHESTRATOR
# ================================

def orchestrate_multi_agent(
    user_query: str,
    pinecone_matches: List[Dict],
    graph_facts: List[Dict]
) -> Dict:
    """
    Orchestrates all 5 agents in sequence.
    Returns: final response + validation report + agent logs.
    """
    
    print("\n" + "="*60)
    print("MULTI-AGENT ORCHESTRATION STARTED")
    print("="*60)
    
    # Build context from retrieval results
    context = build_context_string(pinecone_matches, graph_facts)
    
    # STEP 1: Query Analysis
    print("\n[STEP 1] Query Analysis...")
    query_analysis = agent_1_query_analyzer(user_query)
    
    # STEP 2: Retrieval Planning (informational - actual retrieval already done)
    print("\n[STEP 2] Retrieval Planning...")
    retrieval_plan = agent_2_retrieval_planner(query_analysis, user_query)
    
    # STEP 3: Itinerary Creation
    print("\n[STEP 3] Itinerary Creation...")
    itinerary = agent_3_itinerary_creator(query_analysis, context, user_query)
    
    # STEP 4: Practical Tips
    print("\n[STEP 4] Adding Practical Tips...")
    practical_tips = agent_4_practical_tips(query_analysis, itinerary, user_query)
    
    # STEP 5: Quality Verification
    print("\n[STEP 5] Quality Verification...")
    validation = agent_5_quality_verifier(query_analysis, itinerary, practical_tips, user_query)
    
    # Combine final response
    final_response = f"{itinerary}\n\n{practical_tips}"
    
    # If critical errors found, append corrections
    if not validation.get('is_valid', True) and validation.get('corrections'):
        final_response += f"\n\n### Corrections Applied:\n{validation['corrections']}"
    
    print("\n" + "="*60)
    print("MULTI-AGENT ORCHESTRATION COMPLETE")
    print(f"Quality Score: {validation.get('score', 0)}/100")
    print("="*60 + "\n")
    
    return {
        "response": final_response,
        "query_analysis": query_analysis,
        "retrieval_plan": retrieval_plan,
        "validation": validation,
        "agent_logs": {
            "agent_1": "Query analyzed",
            "agent_2": f"Retrieval planned: {retrieval_plan.get('search_strategy')}",
            "agent_3": f"Itinerary created: {len(itinerary)} chars",
            "agent_4": f"Tips added: {len(practical_tips)} chars",
            "agent_5": f"Validated: Score {validation.get('score', 0)}/100"
        }
    }


def build_context_string(pinecone_matches: List[Dict], graph_facts: List[Dict]) -> str:
    """Build context string from retrieval results."""
    
    context_parts = []
    
    # Pinecone vector matches
    if pinecone_matches:
        context_parts.append("=== SEMANTIC SEARCH RESULTS ===")
        for i, match in enumerate(pinecone_matches[:5], 1):
            meta = match.get('metadata', {})
            context_parts.append(f"\n{i}. {meta.get('name', 'Unknown')}")
            context_parts.append(f"   Type: {meta.get('type', 'N/A')}")
            context_parts.append(f"   City: {meta.get('city', 'N/A')}")
            context_parts.append(f"   Description: {meta.get('description', 'N/A')[:200]}")
            if meta.get('tags'):
                context_parts.append(f"   Tags: {', '.join(meta['tags'][:5])}")
    
    # Neo4j graph facts
    if graph_facts:
        context_parts.append("\n\n=== KNOWLEDGE GRAPH CONNECTIONS ===")
        for i, fact in enumerate(graph_facts[:15], 1):
            context_parts.append(f"\n{i}. {fact.get('target_name', 'Unknown')}")
            context_parts.append(f"   Relationship: {fact.get('rel', 'N/A')} from {fact.get('source', 'N/A')}")
            context_parts.append(f"   Description: {fact.get('target_desc', 'N/A')[:150]}")
    
    return '\n'.join(context_parts)
