# config.py - Configuration for Blue Enigma Hybrid Travel Assistant

NEO4J_URI = "your-neo4j-aura-uri-here"  # Example: neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "your-neo4j-password-here"

OPENAI_API_KEY = "your-openai-api-key-here"  # Example: sk-proj-...

PINECONE_API_KEY = "your-pinecone-api-key-here"  # Example: pcsk_...
PINECONE_ENV = "us-east-1"   # AWS region for serverless
PINECONE_INDEX_NAME = "vietnam-travel"
PINECONE_VECTOR_DIM = 1536  # text-embedding-3-small dimension
