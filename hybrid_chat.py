# hybrid_chat.py
import json
import asyncio
import time
import hashlib
from typing import List, Dict, Optional
from functools import lru_cache
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec
from neo4j import GraphDatabase
import config

# -----------------------------
# Config
# -----------------------------
EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o-mini"
TOP_K = 5

INDEX_NAME = config.PINECONE_INDEX_NAME

# -----------------------------
# Initialize clients
# -----------------------------
client = OpenAI(api_key=config.OPENAI_API_KEY)
pc = Pinecone(api_key=config.PINECONE_API_KEY)

# Connect to Pinecone index
if INDEX_NAME not in pc.list_indexes().names():
    print(f"Creating managed index: {INDEX_NAME}")
    pc.create_index(
        name=INDEX_NAME,
        dimension=config.PINECONE_VECTOR_DIM,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )

index = pc.Index(INDEX_NAME)

# Connect to Neo4j with optimized connection pooling settings
driver = GraphDatabase.driver(
    config.NEO4J_URI, 
    auth=(config.NEO4J_USER, config.NEO4J_PASSWORD),
    max_connection_lifetime=600,
    max_connection_pool_size=50,
    connection_acquisition_timeout=60,
    keep_alive=True
)

# -----------------------------
# Cache System (In-Memory)
# -----------------------------
embedding_cache = {}

def get_cache_key(text: str) -> str:
    """Generate cache key from text."""
    return hashlib.md5(text.encode('utf-8')).hexdigest()

# -----------------------------
# Relationship Weighting & Query Analysis
# -----------------------------
RELATIONSHIP_WEIGHTS = {
    'Located_In': 1.0,
    'Connected_To': 0.9,
    'Near': 0.8,
    'Has_Activity': 0.7,
    'Has_Restaurant': 0.7,
    'Has_Hotel': 0.7,
    'Related_To': 0.5,
    'RELATED_TO': 0.5
}

def extract_query_intent(query: str) -> Dict:
    """Extract intent keywords from query for better filtering."""
    query_lower = query.lower()
    
    intent = {
        'keywords': [],
        'style': None,
        'duration': None,
        'entity_types': ['City', 'Attraction', 'Activity']
    }
    
    # Style detection
    if any(word in query_lower for word in ['romantic', 'romance', 'couple', 'honeymoon']):
        intent['style'] = 'romantic'
        intent['keywords'].extend(['romantic', 'lanterns', 'heritage', 'scenic'])
        intent['entity_types'].extend(['Restaurant', 'Hotel'])
    
    if any(word in query_lower for word in ['adventure', 'trek', 'hiking', 'climb']):
        intent['style'] = 'adventure'
        intent['keywords'].extend(['mountain', 'trekking', 'adventure', 'nature'])
        intent['entity_types'].extend(['Activity', 'Tour'])
    
    if any(word in query_lower for word in ['food', 'cuisine', 'restaurant', 'eat']):
        intent['style'] = 'food'
        intent['keywords'].extend(['food', 'cuisine', 'restaurant', 'market'])
        intent['entity_types'].extend(['Restaurant', 'Market'])
    
    if any(word in query_lower for word in ['beach', 'coast', 'sea', 'ocean']):
        intent['style'] = 'beach'
        intent['keywords'].extend(['beach', 'coast', 'cruise', 'island'])
    
    if any(word in query_lower for word in ['culture', 'history', 'heritage', 'temple']):
        intent['style'] = 'culture'
        intent['keywords'].extend(['culture', 'heritage', 'history', 'temple', 'museum'])
    
    # Duration detection
    import re
    duration_match = re.search(r'(\d+)\s*(day|week)', query_lower)
    if duration_match:
        days = int(duration_match.group(1))
        if duration_match.group(2) == 'week':
            days *= 7
        intent['duration'] = days
    
    return intent

def rank_graph_facts(facts: List[Dict], query_keywords: List[str]) -> List[Dict]:
    """
    Rank graph facts by relevance to query.
    Uses relationship weights and keyword matching.
    """
    if not facts:
        return facts
    
    scored_facts = []
    
    for fact in facts:
        score = 0.0
        
        # Relationship importance
        rel_type = fact.get('rel', 'Related_To')
        score += RELATIONSHIP_WEIGHTS.get(rel_type, 0.5)
        
        # Keyword matching in description
        desc = fact.get('target_desc', '').lower()
        name = fact.get('target_name', '').lower()
        
        for keyword in query_keywords:
            if keyword.lower() in desc:
                score += 0.3
            if keyword.lower() in name:
                score += 0.2
        
        scored_facts.append((score, fact))
    
    # Sort by score descending and return top facts
    scored_facts.sort(key=lambda x: x[0], reverse=True)
    return [fact for score, fact in scored_facts[:20]]

def reciprocal_rank_fusion(pinecone_results: List[Dict], graph_facts: List[Dict], k=60) -> List[tuple]:
    """
    Apply Reciprocal Rank Fusion to combine Pinecone and Neo4j rankings.
    
    RRF Formula: score = 1/(k + rank)
    Combines rankings from both sources to produce unified ranking.
    
    Research: Cormack et al., 2009 - "RRF outperforms individual ranking methods"
    
    Args:
        pinecone_results: List of Pinecone matches with 'id' field
        graph_facts: List of Neo4j facts with 'target_id' or 'source' field
        k: RRF constant (default 60, research-backed optimal value)
    
    Returns:
        List of (node_id, fused_score) tuples, ranked by fused score
    """
    scores = {}
    
    # Score Pinecone results by rank (higher rank = more relevant)
    for rank, result in enumerate(pinecone_results, start=1):
        node_id = result.get('id')
        if node_id:
            rrf_score = 1.0 / (k + rank)
            scores[node_id] = scores.get(node_id, 0) + rrf_score
    
    # Score Neo4j facts by extracting unique target nodes and ranking them
    # Group facts by target_id to get unique nodes
    unique_targets = {}
    for fact in graph_facts:
        target_id = fact.get('target_id')
        source_id = fact.get('source')
        
        # Track both targets and sources (bidirectional relationships)
        if target_id and target_id not in unique_targets:
            unique_targets[target_id] = fact
        if source_id and source_id not in unique_targets:
            unique_targets[source_id] = {'target_id': source_id, 'target_name': fact.get('source')}
    
    # Rank unique targets by their relationship importance
    target_scores = []
    for target_id, fact in unique_targets.items():
        rel_weight = RELATIONSHIP_WEIGHTS.get(fact.get('rel', ''), 0.5)
        target_scores.append((rel_weight, target_id, fact))
    
    target_scores.sort(key=lambda x: x[0], reverse=True)
    
    # Apply RRF scoring to Neo4j results
    for rank, (rel_weight, target_id, fact) in enumerate(target_scores, start=1):
        rrf_score = 1.0 / (k + rank)
        scores[target_id] = scores.get(target_id, 0) + rrf_score
    
    # Sort by fused score (descending)
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    print(f"DEBUG: RRF fusion - Combined {len(pinecone_results)} vector + {len(unique_targets)} graph nodes into {len(ranked)} fused results")
    
    return ranked

# -----------------------------
# Helper functions
# -----------------------------
def embed_text(text: str) -> List[float]:
    """Get embedding for a text string with caching."""
    cache_key = get_cache_key(text)
    
    if cache_key in embedding_cache:
        return embedding_cache[cache_key]
    
    resp = client.embeddings.create(model=EMBED_MODEL, input=[text])
    embedding = resp.data[0].embedding
    
    embedding_cache[cache_key] = embedding
    return embedding

def pinecone_query(query_text: str, top_k=TOP_K, max_retries=3):
    """Query Pinecone index using embedding with retry logic."""
    for attempt in range(max_retries):
        try:
            vec = embed_text(query_text)
            res = index.query(
                vector=vec,
                top_k=top_k,
                include_metadata=True,
                include_values=False
            )
            print(f"DEBUG: Pinecone results: {len(res['matches'])}")
            return res["matches"]
        except Exception as e:
            print(f"Pinecone query attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                print("Max retries reached. Returning empty results.")
                return []
    return []

def fetch_graph_context(node_ids: List[str], neighborhood_depth=1, max_retries=3):
    """
    Fetch neighboring nodes from Neo4j with retry logic and connection handling.
    Uses batched query for better performance.
    """
    facts = []
    
    if not node_ids:
        return facts
    
    for attempt in range(max_retries):
        try:
            with driver.session() as session:
                batch_query = """
                UNWIND $node_ids AS nid
                MATCH (n:Entity {id:nid})-[r]-(m:Entity)
                RETURN nid AS source, type(r) AS rel, labels(m) AS labels, 
                       m.id AS id, m.name AS name, m.type AS type, 
                       m.description AS description
                LIMIT 100
                """
                
                result = session.run(batch_query, node_ids=node_ids)
                
                for record in result:
                    facts.append({
                        "source": record["source"],
                        "rel": record["rel"],
                        "target_id": record["id"],
                        "target_name": record["name"],
                        "target_desc": (record["description"] or "")[:400],
                        "labels": record["labels"]
                    })
                
                print(f"DEBUG: Graph facts: {len(facts)}")
                return facts
                
        except Exception as e:
            print(f"Neo4j query attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {2 ** attempt} seconds...")
                time.sleep(2 ** attempt)
            else:
                print("Max retries reached. Returning empty graph context.")
                return []
    
    return facts

def build_prompt(user_query, pinecone_matches, graph_facts, intent=None):
    """
    Build a chat prompt combining vector DB matches and graph facts with enhanced reasoning.
    Uses intent analysis for better targeting.
    """
    system = """You are an expert Vietnam travel consultant with deep knowledge of local culture, destinations, and travel logistics.

YOUR REASONING PROCESS:
1. Analyze the user's intent (duration, style, preferences, budget if mentioned)
2. Evaluate retrieved locations for relevance and compatibility
3. Consider practical logistics (distances, travel times, connections)
4. Optimize for seasonal factors when mentioned in the data

OUTPUT FORMAT:
- Start with a brief summary addressing the user's request
- Provide specific, actionable recommendations with clear structure
- Use actual place names from the data, not just IDs
- Include WHY each recommendation fits the request
- Add 2-3 practical tips (best time to visit, transportation, booking advice)

QUALITY STANDARDS:
- Prioritize authentic experiences over generic tourist advice
- Balance popular destinations with practical considerations
- Use specific details from the provided context
- Keep responses organized and easy to follow
"""

    vec_context = []
    for m in pinecone_matches:
        meta = m["metadata"]
        score = m.get("score", None)
        tags = meta.get('tags', [])
        tags_str = ', '.join(tags) if isinstance(tags, list) else str(tags)
        
        snippet = f"- ID: {m['id']}\n  Name: {meta.get('name','Unknown')}\n  Type: {meta.get('type','')}\n  Relevance Score: {score:.3f}"
        if meta.get("city"):
            snippet += f"\n  Location: {meta.get('city')}"
        if tags_str:
            snippet += f"\n  Tags: {tags_str}"
        vec_context.append(snippet)

    graph_context = []
    for f in graph_facts[:20]:
        context_item = f"- {f['target_name']} ({f['target_id']})\n  Type: {f.get('labels', ['Unknown'])[0] if f.get('labels') else 'Unknown'}\n  Relationship: {f['rel']} from {f['source']}\n  Description: {f['target_desc'][:200]}"
        graph_context.append(context_item)
    
    # Add intent context if available
    intent_context = ""
    if intent:
        if intent.get('style'):
            intent_context += f"\nDetected travel style: {intent['style']}"
        if intent.get('duration'):
            intent_context += f"\nTrip duration: {intent['duration']} days"

    user_content = f"""User Query: "{user_query}"{intent_context}

SEMANTICALLY SIMILAR DESTINATIONS (from vector search):
{chr(10).join(vec_context[:10])}

RELATED LOCATIONS & CONNECTIONS (from knowledge graph):
{chr(10).join(graph_context) if graph_context else "No additional graph context available."}

Based on the above context, provide a comprehensive answer that:
1. Directly addresses the user's query
2. Uses specific place names and details from the context
3. Explains WHY these recommendations fit the request
4. Includes practical travel advice (transportation, timing, costs if relevant)
5. Structures information clearly (use day-by-day format for multi-day itineraries)
6. Prioritizes authentic experiences and local insights
"""

    prompt = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content}
    ]
    return prompt

def call_chat(prompt_messages, max_retries=3, stream=False):
    """Call OpenAI ChatCompletion with retry logic and optional streaming."""
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=CHAT_MODEL,
                messages=prompt_messages,
                max_tokens=1000,
                temperature=0.2,
                stream=stream
            )
            
            if stream:
                return resp
            else:
                return resp.choices[0].message.content
                
        except Exception as e:
            print(f"OpenAI API attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                return "I apologize, but I'm having trouble generating a response right now. Please try again."
    return "Service temporarily unavailable."

# -----------------------------
# Async Hybrid Retrieval
# -----------------------------
async def hybrid_retrieval_async(query_text: str, top_k: int = TOP_K, stream_response: bool = True, use_multi_agent: bool = False) -> Dict:
    """
    Asynchronous hybrid retrieval combining Pinecone and Neo4j.
    Includes error handling, retry logic, and optional streaming for production resilience.
    """
    start_time = time.time()
    
    try:
        # Step 1: Generate embedding (required for Pinecone query)
        embedding = await asyncio.to_thread(embed_text, query_text)
        embed_time = time.time() - start_time
        
        # Step 2: Query Pinecone (async with error handling)
        pinecone_start = time.time()
        try:
            matches_result = await asyncio.to_thread(pinecone_query, query_text, top_k)
            matches = matches_result if matches_result else []
        except Exception as e:
            print(f"Pinecone query failed: {e}")
            matches = []
        pinecone_time = time.time() - pinecone_start
        
        # Step 3: Extract query intent
        intent = extract_query_intent(query_text)
        
        # Step 4: Extract match IDs and query Neo4j (async with error handling)
        match_ids = [m["id"] for m in matches] if matches else []
        neo4j_start = time.time()
        try:
            graph_facts_raw = await asyncio.to_thread(fetch_graph_context, match_ids) if match_ids else []
        except Exception as e:
            print(f"Neo4j query failed: {e}")
            graph_facts_raw = []
        neo4j_time = time.time() - neo4j_start
        
        # Step 5: Apply Reciprocal Rank Fusion to combine Pinecone + Neo4j rankings
        rrf_start = time.time()
        if matches and graph_facts_raw:
            # Get fused ranking
            fused_ranking = reciprocal_rank_fusion(matches, graph_facts_raw, k=60)
            
            # Extract top node IDs from fused ranking
            top_node_ids = [node_id for node_id, score in fused_ranking[:20]]
            
            # Filter graph facts to only include top-ranked nodes
            graph_facts = [fact for fact in graph_facts_raw if fact.get('target_id') in top_node_ids or fact.get('source') in top_node_ids]
            
            # Final ranking by keywords (secondary sort)
            graph_facts = rank_graph_facts(graph_facts, intent.get('keywords', []))
        else:
            # Fallback to keyword ranking only if RRF not applicable
            graph_facts = rank_graph_facts(graph_facts_raw, intent.get('keywords', []))
        
        rrf_time = time.time() - rrf_start
        print(f"DEBUG: RRF fusion completed in {rrf_time:.3f}s")
        
        # Step 6: Build prompt with intent
        if not matches and not graph_facts:
            return {
                "answer": "I apologize, but I couldn't retrieve enough information to answer your question. Please try rephrasing or try again.",
                "matches": [],
                "graph_facts_count": 0,
                "stream": None,
                "multi_agent_report": None,
                "timing": {
                    "embedding": round(embed_time, 3),
                    "pinecone": round(pinecone_time, 3),
                    "neo4j": round(neo4j_time, 3),
                    "rrf_fusion": 0.0,
                    "multi_agent": 0.0,
                    "openai": 0.0,
                    "total": round(time.time() - start_time, 3)
                }
            }
        
        # Step 7: Build prompt and call OpenAI
        prompt = build_prompt(query_text, matches, graph_facts, intent)
        chat_start = time.time()
        
        # Step 8: Call OpenAI (async with error handling and optional streaming)
        chat_start = time.time()
        
        if stream_response:
            stream = await asyncio.to_thread(call_chat, prompt, 3, True)
            chat_time = time.time() - chat_start
            
            return {
                "answer": None,
                "stream": stream,
                "matches": matches,
                "graph_facts_count": len(graph_facts),
                "multi_agent_report": None,
                "timing": {
                    "embedding": round(embed_time, 3),
                    "pinecone": round(pinecone_time, 3),
                    "neo4j": round(neo4j_time, 3),
                    "rrf_fusion": round(rrf_time, 3),
                    "multi_agent": 0.0,
                    "openai": round(chat_time, 3),
                    "total": round(time.time() - start_time, 3)
                }
            }
        else:
            answer = await asyncio.to_thread(call_chat, prompt, 3, False)
            chat_time = time.time() - chat_start
            
            total_time = time.time() - start_time
            
            return {
                "answer": answer,
                "stream": None,
                "matches": matches,
                "graph_facts_count": len(graph_facts),
                "multi_agent_report": None,
                "timing": {
                    "embedding": round(embed_time, 3),
                    "pinecone": round(pinecone_time, 3),
                    "neo4j": round(neo4j_time, 3),
                    "rrf_fusion": round(rrf_time, 3),
                    "openai": round(chat_time, 3),
                    "total": round(total_time, 3)
                }
            }
    
    except Exception as e:
        print(f"Critical error in hybrid retrieval: {e}")
        return {
            "answer": f"An unexpected error occurred: {str(e)}. Please try again.",
            "matches": [],
            "graph_facts_count": 0,
            "stream": None,
            "timing": {
                "embedding": 0.0,
                "pinecone": 0.0,
                "neo4j": 0.0,
                "rrf_fusion": 0.0,
                "openai": 0.0,
                "total": round(time.time() - start_time, 3)
            }
        }

# -----------------------------
# Interactive chat (Synchronous wrapper)
# -----------------------------
def interactive_chat():
    """Interactive CLI for travel queries with performance metrics and streaming responses."""
    print("="*60)
    print("ENHANCED HYBRID TRAVEL ASSISTANT v2.2")
    print("Features: RRF Fusion | Streaming | Async | Caching")
    print("="*60)
    print("\nType your question or 'exit' to quit.\n")
    
    query_count = 0
    
    try:
        while True:
            try:
                query = input("Your travel question: ").strip()
                if not query or query.lower() in ("exit", "quit"):
                    print(f"\nProcessed {query_count} queries. Cache hits: {len(embedding_cache)}")
                    print("Thank you for using the travel assistant!")
                    break
                
                query_count += 1
                print("\nProcessing your request...\n")
                
                # Run async function in event loop with streaming enabled
                result = asyncio.run(hybrid_retrieval_async(query, stream_response=True))
                
                # Display results with streaming
                print("="*60)
                print("ANSWER")
                print("="*60 + "\n")
                
                if result.get("stream"):
                    # Stream the response token by token
                    full_answer = ""
                    for chunk in result["stream"]:
                        if chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            print(content, end='', flush=True)
                            full_answer += content
                    print("\n")
                    
                    # Update timing for total with streaming completion
                    result["answer"] = full_answer
                else:
                    # Non-streaming fallback
                    print(result["answer"])
                    print()
                
                print("="*60)
                print("PERFORMANCE METRICS")
                print("="*60)
                print(f"Embedding generation: {result['timing']['embedding']}s")
                print(f"Pinecone search: {result['timing']['pinecone']}s")
                print(f"Neo4j graph query: {result['timing']['neo4j']}s")
                print(f"RRF fusion: {result['timing']['rrf_fusion']}s")
                print(f"OpenAI generation: {result['timing']['openai']}s (streaming)")
                print(f"Total time: {result['timing']['total']}s")
                print(f"Results: {len(result['matches'])} vector matches, {result['graph_facts_count']} graph facts")
                print(f"Cache size: {len(embedding_cache)} embeddings cached")
                print("="*60 + "\n")
                
            except KeyboardInterrupt:
                print("\n\nInterrupted by user. Exiting gracefully...")
                break
            except Exception as e:
                print(f"\nError processing query: {e}")
                print("Please try again with a different question.\n")
                continue
    
    finally:
        # Clean up resources
        try:
            driver.close()
            print("Neo4j connection closed.")
        except:
            pass

if __name__ == "__main__":
    print("="*60)
    print("BLUE ENIGMA HYBRID TRAVEL ASSISTANT v2.2")
    print("RRF-Powered Hybrid Retrieval with Streaming")
    print("="*60)
    print("\n Starting chat session...\n")
    
    try:
        interactive_chat()
    except KeyboardInterrupt:
        print("\n\nSession cancelled. Goodbye!")
    except Exception as e:
        print(f"\n\nError during startup: {e}")
        print("Please check your configuration and try again.")
