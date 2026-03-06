import sys
import argparse
from pathlib import Path
from lib.knowledge_manager import KnowledgeManager
from lib.ollama_client import chat
from lib.model_router import route

# /THE_VAULT/jarvis/pipelines/query_knowledge.py

def query_knowledge(query: str, category: str = None):
    km = KnowledgeManager()
    print(f"[RAG] Searching knowledge base for: '{query}'...")
    
    # 1. Retrieval
    results = km.search(query, category=category)
    if not results:
        # Try a broader search if no direct match
        words = query.split()
        if len(words) > 1:
            results = km.search(words[0], category=category)
    
    if not results:
        print("Jarvis: I couldn't find anything relevant in my knowledge base.")
        return False

    # 2. Context Preparation
    context = "\n\n".join([f"--- Source: {r['source_title']} ({r['source_url']}) ---\n{r['content']}" for r in results[:5]])
    
    # 3. Generation
    prompt = f"""You are Jarvis, a helpful AI assistant. Answer the user's question based ONLY on the provided context from the knowledge base.
If the answer is not in the context, say you don't know based on the current knowledge base.

Context:
{context}

User Question: {query}

Answer:"""

    print("[RAG] Thinking...")
    try:
        response = chat(route("classify"), [{"role": "user", "content": prompt}], thinking=False)
        print(f"\nJarvis: {response}\n")
        
        # Print sources
        print("Sources:")
        seen_sources = set()
        for r in results[:5]:
            source = f"  - {r['source_title']} ({r['source_url']})"
            if source not in seen_sources:
                print(source)
                seen_sources.add(source)
        return True
    except Exception as e:
        print(f"Jarvis: Error generating response: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Jarvis Knowledge Query (RAG)")
    parser.add_argument("query", help="Question to ask")
    parser.add_argument("--category", "-c", help="Specific category to search in")
    args = parser.parse_args()

    if not args.query:
        print("Usage: jarvis query <question>")
        sys.exit(1)

    success = query_knowledge(args.query, category=args.category)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
