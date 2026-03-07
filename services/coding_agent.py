#!/usr/bin/env python3
"""
MVP 12 — Coding Agent HTTP Server
/home/qwerty/NixOSenv/Jarvis/services/coding_agent.py

HTTP server on localhost:7002. Powers the Jarvis Neovim plugin.
Endpoints:
  GET  /health    — health check + DB stats
  POST /complete  — FIM autocomplete (Qwen3-1.7B, REQUIRES suffix=)
  POST /chat      — RAG-augmented chat (Qwen3-14B, BM25+vector hybrid)
  POST /fix       — looped agent fix via agent_loop.py (Qwen3-14B + thinking)
  POST /explain   — explain code without RAG (Qwen3-14B fast)
  POST /index     — index a codebase into codebase.db

CRITICAL: All Ollama calls are blocking (CPU inference 3-90s).
The Lua plugin MUST use plenary.curl async — never synchronous vim.fn.system().
"""

import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
import threading
import signal
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from pathlib import Path

# Base directory configuration (Unified SSD Architecture)
JARVIS_ROOT = Path(os.environ.get("JARVIS_ROOT", Path(__file__).resolve().parent.parent))
BASE_DIR = JARVIS_ROOT # For backward compatibility

sys.path.insert(0, str(BASE_DIR))
from lib.ollama_client import chat as ollama_chat, generate, embed, is_healthy, OllamaError
from lib.model_router import route
from lib.llm import ask, Privacy
from lib.event_bus import emit

# Active data on SSD
INDEX_DB = JARVIS_ROOT / "index" / "codebase.db"
USER_CONTEXT = JARVIS_ROOT / "config" / "user_context.md"

PORT = 7002

# Task tracking for cancellation
active_tasks = {}  # task_id -> { "process": subprocess.Popen, "start_time": float }
tasks_lock = threading.Lock()


# ── RAG: BM25 + Vector Hybrid ─────────────────────────────────────────────────

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

# ── RAG 2.0: BM25 + Vector RRF Hybrid ─────────────────────────────────────────

def _load_all_sentences(db_path: Path) -> list[dict]:
    if not db_path.exists():
        return []
    try:
        con = sqlite3.connect(db_path)
        rows = con.execute("SELECT sentence_id, chunk_id, text, embedding FROM sentences").fetchall()
        con.close()
        return [{"id": r[0], "chunk_id": r[1], "text": r[2], "embedding": json.loads(r[3])} for r in rows]
    except Exception:
        return []

def _load_parent_text(db_path: Path, chunk_id: str) -> str:
    try:
        con = sqlite3.connect(db_path)
        row = con.execute("SELECT text FROM chunks WHERE chunk_id = ?", (chunk_id,)).fetchone()
        con.close()
        return row[0] if row else ""
    except Exception:
        return ""

def retrieve_hybrid(query: str, top_k: int = 3, k_rrf: int = 60) -> list[dict]:
    """
    RAG 2.0: Reciprocal Rank Fusion of Lexical (Parent BM25) and Semantic (Child Vector).
    """
    sentences = _load_all_sentences(INDEX_DB)
    if not sentences:
        return []

    # 1. Semantic Search (Sentence Level)
    vec_results = []
    try:
        query_emb = embed("embed", query)
        # Use child sentences for precise semantic match
        vec_raw = sorted(
            [{"chunk_id": s["chunk_id"], "score": _cosine_similarity(query_emb, s["embedding"])} for s in sentences],
            key=lambda x: x["score"], reverse=True
        )
        vec_results = vec_raw[:50]
    except Exception:
        pass

    # 2. Lexical Search (Parent Level - BM25)
    lex_results = []
    try:
        from rank_bm25 import BM25Okapi
        con = sqlite3.connect(INDEX_DB)
        parents = con.execute("SELECT chunk_id, text FROM chunks").fetchall()
        con.close()
        
        corpus = [p[1].lower().split() for p in parents]
        bm25 = BM25Okapi(corpus)
        bm25_scores = bm25.get_scores(query.lower().split())
        
        lex_raw = sorted(
            [{"chunk_id": parents[i][0], "score": float(bm25_scores[i])} for i in range(len(parents))],
            key=lambda x: x["score"], reverse=True
        )
        lex_results = lex_raw[:50]
    except (ImportError, Exception):
        pass

    # 3. Reciprocal Rank Fusion (RRF)
    # score = sum(1 / (rank + k_rrf))
    rrf_scores: dict[str, float] = {}
    
    for rank, res in enumerate(vec_results):
        cid = str(res["chunk_id"])
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (rank + k_rrf))
        
    for rank, res in enumerate(lex_results):
        cid = str(res["chunk_id"])
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (rank + k_rrf))

    # 4. Final Retrieval Rank
    final_rank = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
    
    results = []
    for chunk_id, score in final_rank:
        text = _load_parent_text(INDEX_DB, chunk_id)
        results.append({"chunk_id": chunk_id, "text": text, "score": float(score)})
        
    return results

# ── System Prompt Builder ─────────────────────────────────────────────────────

def build_system_prompt(rag_chunks: list[dict]) -> str:
    parts = []

    if USER_CONTEXT.exists():
        parts.append(f"## User Context\n{USER_CONTEXT.read_text().strip()}")

    # Today's events for episodic context
    try:
        con = sqlite3.connect(str(BASE_DIR / "logs" / "events.db"))
        rows = con.execute(
            "SELECT source, event FROM events WHERE ts > date('now') ORDER BY ts DESC LIMIT 10"
        ).fetchall()
        con.close()
        if rows:
            events_str = "\n".join(f"- [{r[0]}] {r[1]}" for r in rows)
            parts.append(f"## Today's Activity\n{events_str}")
    except Exception:
        pass

    if rag_chunks:
        ctx = "\n---\n".join(c["text"][:800] for c in rag_chunks)
        parts.append(f"## Relevant Code Context\n{ctx}")

    parts.append("You are Jarvis, a senior software engineer assistant integrated into Neovim. "
                 "Give precise, actionable answers. Prefer code over prose. "
                 "For NixOS: never use cudaPackages (Intel Iris Xe, no NVIDIA).")

    return "\n\n".join(parts)


# ── Code Indexer ──────────────────────────────────────────────────────────────

def index_codebase(root: str) -> dict:
    root_path = Path(root)
    if not root_path.exists():
        return {"error": f"Path does not exist: {root}"}

    INDEX_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(INDEX_DB)
    # Schema 2.0: Parent Chunks + Child Sentences
    con.executescript("""
        CREATE TABLE IF NOT EXISTS chunks (
            chunk_id TEXT PRIMARY KEY, 
            file TEXT, 
            text TEXT, 
            mtime REAL
        );
        CREATE TABLE IF NOT EXISTS sentences (
            sentence_id INTEGER PRIMARY KEY AUTOINCREMENT,
            chunk_id TEXT,
            text TEXT,
            embedding TEXT,
            FOREIGN KEY(chunk_id) REFERENCES chunks(chunk_id)
        );
        CREATE INDEX IF NOT EXISTS idx_sentence_chunk ON sentences(chunk_id);
    """)
    
    # Load existing mtimes
    cursor = con.execute("SELECT chunk_id, mtime FROM chunks")
    existing_mtimes = {row[0]: row[1] for row in cursor.fetchall()}

    indexed_chunks: int = 0
    indexed_sentences: int = 0
    skipped: int = 0
    extensions = {".py", ".rs", ".nix", ".lua", ".toml", ".md", ".go"}
    
    for f in root_path.rglob("*"):
        f_str = str(f)
        if f.suffix not in extensions or ".venv" in f_str or "target/" in f_str or ".git" in f_str:
            continue
        try:
            chunk_id = str(f.relative_to(root_path))
            mtime = os.path.getmtime(f)
            
            if chunk_id in existing_mtimes and existing_mtimes[chunk_id] >= mtime:
                skipped += 1
                continue

            # Clear old sentence data for this chunk
            con.execute("DELETE FROM sentences WHERE chunk_id = ?", (chunk_id,))
            
            text = f.read_text(errors="ignore")
            # Store parent chunk (full file or large block)
            con.execute(
                "INSERT OR REPLACE INTO chunks (chunk_id, file, text, mtime) VALUES (?,?,?,?)",
                (chunk_id, str(f), text, mtime)
            )
            
            # Sentence splitting (simple refined regex)
            raw_sentences = re.split(r'(?<=[.!?])\s+|\n', text)
            for s in raw_sentences:
                s_clean = s.strip()
                if len(s_clean) < 20: 
                    continue
                
                # Embed the "small" sentence for high precision retrieval
                s_trunc = s_clean[:1000]
                emb = embed("embed", s_trunc)
                con.execute(
                    "INSERT INTO sentences (chunk_id, text, embedding) VALUES (?,?,?)",
                    (chunk_id, s_clean, json.dumps(emb))
                )
                indexed_sentences += 1
                
            indexed_chunks += 1
        except Exception:
            continue

    con.commit()
    con.close()
    emit("coding_agent", "index_completed", {"root": root, "chunks": indexed_chunks, "sentences": indexed_sentences})
    return {"chunks": indexed_chunks, "sentences": indexed_sentences, "skipped": skipped}


# ── Request Handler ───────────────────────────────────────────────────────────

class JarvisHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass  # suppress default httpd logs

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        return json.loads(body) if body else {}

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            chunk_count = 0
            try:
                con = sqlite3.connect(INDEX_DB)
                chunk_count = con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
                con.close()
            except Exception:
                pass
            self._send_json({"status": "ok", "ollama": is_healthy(), "chunks_indexed": chunk_count})
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        data = self._read_json()
        t0 = time.time()

        if self.path == "/complete":
            self._handle_complete(data, t0)
        elif self.path == "/chat":
            self._handle_chat(data, t0)
        elif self.path == "/fix":
            self._handle_fix(data, t0)
        elif self.path == "/explain":
            self._handle_explain(data, t0)
        elif self.path == "/index":
            self._handle_index(data)
        elif self.path == "/cancel":
            self._handle_cancel(data)
        elif self.path == "/analyze_error":
            self._handle_analyze_error(data, t0)
        elif self.path == "/summarize_git":
            self._handle_summarize_git(data, t0)
        elif self.path == "/research_manual":
            self._handle_research_manual(data)
        elif self.path == "/prefetch":
            self._handle_prefetch(data)
        else:
            self._send_json({"error": "unknown endpoint"}, 404)



    def _handle_cancel(self, data: dict):
        task_id = data.get("task_id")
        if not task_id:
            self._send_json({"error": "missing task_id"}, 400)
            return

        with tasks_lock:
            if task_id in active_tasks:
                proc = active_tasks[task_id].get("process")
                if proc:
                    proc.terminate()
                    emit("coding_agent", "cancelled", {"task_id": task_id}, level="WARN")
                del active_tasks[task_id]
                self._send_json({"status": "cancelled", "task_id": task_id})
            else:
                self._send_json({"error": "task not found"}, 404)


    def _handle_complete(self, data: dict, t0: float):
        """FIM autocomplete. MUST pass suffix= to Ollama for proper FIM behaviour."""
        prefix = data.get("prefix", "")
        suffix = data.get("suffix", "")  # text AFTER the cursor — required for FIM
        try:
            # CRITICAL: suffix parameter required. Without it, Ollama does regular completion.
            result = generate(
                model_alias=route("complete", privacy=Privacy.PRIVATE).model_alias,
                prompt=prefix,
                suffix=suffix,   # ← THIS IS REQUIRED FOR FIM
                thinking=False,
            )
            emit("coding_agent", "complete", {"latency_ms": int((time.time() - t0) * 1000)})
            self._send_json({"completion": result})
        except OllamaError as e:
            self._send_json({"error": str(e)}, 503)

    def _handle_chat(self, data: dict, t0: float):
        """RAG-augmented chat with BM25+vector hybrid search."""
        query = data.get("query", "")
        messages = data.get("messages", [{"role": "user", "content": query}])

        rag_chunks = retrieve_hybrid(query, top_k=3)
        top_score = rag_chunks[0].get("score", 0.0) if rag_chunks else 0.0

        # Confidence cascade: if top RAG score < 0.65, answer from model knowledge only
        if top_score < 0.65:
            rag_chunks = []

        system = build_system_prompt(rag_chunks)

        try:
            response = ask(
                task="chat",
                privacy=Privacy.PRIVATE,
                messages=messages,
                system=system,
                thinking=False,
            )
            emit("coding_agent", "chat", {"latency_ms": int((time.time() - t0) * 1000), "used_rag": top_score >= 0.65})
            self._send_json({"response": response, "rag_score": top_score})
        except OllamaError as e:
            self._send_json({"error": str(e)}, 503)

    def _handle_fix(self, data: dict, t0: float):
        """Run agent_loop.py for looped fix. Returns a unified diff."""
        task = data.get("task", "fix")
        prompt = data.get("prompt", "")
        max_retries = data.get("max_retries", 3)
        task_id = data.get("task_id", f"fix_{int(t0)}")

        # Write prompt to temp file and invoke agent_loop as subprocess
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as tf:
            tf.write(prompt)
            tf_path = tf.name

        try:
            emit("coding_agent", "starting_fix", {"task_id": task_id, "prompt": prompt[:50] + "..."})
            proc = subprocess.Popen(
                [
                    str(BASE_DIR / ".venv" / "bin" / "python"),
                    str(BASE_DIR / "pipelines" / "agent_loop.py"),
                    "--task", task,
                    "--user-prompt", prompt,
                    "--max-retries", str(max_retries),
                    "--thinking",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={**os.environ, "PYTHONPATH": str(BASE_DIR)},
            )
            
            with tasks_lock:
                active_tasks[task_id] = {"process": proc, "start_time": t0}

            # Wait for process with timeout
            try:
                stdout, stderr = proc.communicate(timeout=600)
                success = proc.returncode == 0
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
                success = False
                emit("coding_agent", "fix_timeout", {"task_id": task_id}, level="ERROR")

            emit("coding_agent", "fix_completed", {
                "task_id": task_id,
                "success": success,
                "latency_ms": int((time.time() - t0) * 1000)
            })
            self._send_json({
                "output": stdout,
                "stderr": stderr,
                "success": success,
                "task_id": task_id
            })
        except Exception as e:
            self._send_json({"error": str(e)}, 500)
        finally:
            with tasks_lock:
                if task_id in active_tasks:
                    del active_tasks[task_id]
            if os.path.exists(tf_path):
                os.unlink(tf_path)


    def _handle_explain(self, data: dict, t0: float):
        """Explain code without RAG — fast path."""
        code = data.get("code", "")
        language = data.get("language", "")
        system = f"You are a senior {language} engineer. Explain this code concisely in plain English. Focus on what it does, not how it looks."
        messages = [{"role": "user", "content": f"```{language}\n{code[:3000]}\n```"}]
        try:
            response = ask(task="chat", privacy=Privacy.PRIVATE, messages=messages, system=system, thinking=False)
            self._send_json({"explanation": response})
        except OllamaError as e:
            self._send_json({"error": str(e)}, 503)

    def _handle_index(self, data: dict):
        root = data.get("root", str(BASE_DIR))
        result = index_codebase(root)
        self._send_json(result)


# ── Main ──────────────────────────────────────────────────────────────────────

    def _handle_summarize_git(self, data: dict, t0: float):
        """Generate a semantic commit message from a git diff."""
        diff = data.get("diff", "")
        if not diff:
            self._send_json({"error": "no diff provided"}, 400)
            return

        system = "You are a senior engineer. Generate a high-quality, semantic commit message following the Conventional Commits spec. Focus on intent. Max 72 chars per line."
        messages = [{"role": "user", "content": f"Summarize this git diff into a commit message:\n\n{diff[:5000]}"}]
        try:
            response = ask(task="summarize", privacy=Privacy.PRIVATE, messages=messages, system=system, thinking=False)
            self._send_json({"summary": response})
            emit("coding_agent", "git_summarize")
        except OllamaError as e:
            self._send_json({"error": str(e)}, 503)

    def _handle_analyze_error(self, data: dict, t0: float):
        """Analyze a compiler error and suggest a fix."""
        error = data.get("error", "")
        context = data.get("context", "")
        language = data.get("language", "")
        
        system = f"You are a senior {language} engineer. Explain this error concisely and suggest a one-line fix."
        prompt = f"Error: {error}\n\nContext:\n```{language}\n{context}\n```"
        messages = [{"role": "user", "content": prompt}]
        
        try:
            response = ask(task="chat", privacy=Privacy.PRIVATE, messages=messages, system=system, thinking=False)
            self._send_json({"analysis": response})
            emit("coding_agent", "analyze_error")
        except OllamaError as e:
            self._send_json({"error": str(e)}, 503)

    def _handle_research_manual(self, data: dict):
        """Invoke research_agent.py for a quick web search."""
        query = data.get("query", "")
        if not query:
            self._send_json({"error": "no query provided"}, 400)
            return

        try:
            # Run research_agent.py with 3 sources for speed
            result = subprocess.run(
                [
                    str(BASE_DIR / ".venv" / "bin" / "python"),
                    str(BASE_DIR / "pipelines" / "research_agent.py"),
                    "--query", query,
                    "--sources", "3"
                ],
                capture_output=True, text=True, timeout=300,
                env={**os.environ, "PYTHONPATH": str(BASE_DIR)},
            )
            
            # Extract path from stderr or stdout where research_agent logs it
            # The research_agent.py prints "Saved to: /path/to/file.md"
            import re
            match = re.search(r"Saved to: (/[^ \n]+)", result.stdout)
            file_path = match.group(1) if match else None

            emit("coding_agent", "research_manual", {"query": query, "file": file_path})
            self._send_json({"status": "research_completed", "query": query, "file": file_path})

        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_prefetch(self, data: dict):
        """Prefetch a model into memory."""
        alias = data.get("model_alias", "chat")
        decision = route(alias, privacy=Privacy.PRIVATE)
        if decision.backend != 'local':
            self._send_json({"status": "skipped", "reason": "Cloud backend does not need prefetching"})
            return
            
        try:
            # Load model by sending a minimal prompt with keep_alive
            # This is non-blocking in the sense that we don't wait for a long response
            ollama_chat(decision.model_alias, [{"role": "user", "content": "hi"}], system="You are a prefetcher. Repl with 'OK' only.", thinking=False)
            emit("coding_agent", "prefetch", {"model": decision.model_alias})
            self._send_json({"status": "prefetched", "model": decision.model_alias})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

def main():


    print(f"[Coding Agent] Starting multi-threaded on http://localhost:{PORT}")
    emit("coding_agent", "started", {"port": PORT})
    server = ThreadingHTTPServer(("localhost", PORT), JarvisHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Coding Agent] Stopped.")
        emit("coding_agent", "stopped", {})


if __name__ == "__main__":
    main()
