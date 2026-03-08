import sys
import argparse
from pathlib import Path
from lib.knowledge_manager import KnowledgeManager
from lib.ollama_client import chat
from lib.model_router import route

# /home/qwerty/NixOSenv/Jarvis/pipelines/query_knowledge.py

async def query_knowledge(query: str, category: str = None):
    km = KnowledgeManager()
    print(f"[RAG] Searching knowledge base for: '{query}'...")
    
    # 1. Retrieval (Automatic Context Injection)
    import os
    associations = km.get_associations(os.getcwd())
    if associations:
        print(f"[RAG] Using associated categories: {', '.join(associations)}")
    
    results = await km.search(query, category=category, categories=associations if associations else None)
    if not results:
        # Try a broader search if no direct match
        words = query.split()
        if len(words) > 1:
            results = await km.search(words[0], category=category)
    
    if not results:
        print("Jarvis: I couldn't find anything relevant in my knowledge base.")
        return False

    # 2. Context Preparation
    context_parts = [f"--- Source: {r['source_title']} ({r['source_url']}) ---\n{r['content']}" for r in results[:5]]
    
    try:
        from lib.episodic_memory import get_session_context
        context_parts.append(get_session_context())
    except ImportError:
        pass
        
    context = "\n\n".join(context_parts)

    # 3. Generation
    # 3. Generation
    system_prompt = """You ARE Jarvis, a high-performance local AI orchestrator for NixOS. 
Answer the user's question directly and in the first person. 
Use the provided context to inform your identity, capabilities, and technical knowledge. 
If the answer is not in the context, say you don't know based on current knowledge. 
DO NOT analyze the context as a set of files or code; internalize it as your own reality."""
    
    prompt = f"Context:\n{context}\n\nUser Question: {query}\n\nAnswer as Jarvis:"

    print("[RAG] Thinking...")
    try:
        # Using stream=True for "all output always in terminal" real-time feel
        decision = route("chat")
        response_gen = chat(decision.model_alias, [{"role": "user", "content": prompt}], system=system_prompt, thinking=False, stream=True)
        
        print("\nJarvis: ", end="", flush=True)
        for chunk in response_gen:
            print(chunk, end="", flush=True)
        print("\n")
        
        # Print sources
        print("\nSources:")
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
    import asyncio
    parser = argparse.ArgumentParser(description="Jarvis Knowledge Query (RAG)")
    parser.add_argument("query", help="Question to ask")
    parser.add_argument("--category", "-c", help="Specific category to search in")
    args = parser.parse_args()

    if not args.query:
        print("Usage: jarvis query <question>")
        sys.exit(1)

    success = asyncio.run(query_knowledge(args.query, category=args.category))
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
