# LOCAL JARVIS

MVP Specifications for Coding Agents

10 component MVPs + 1 connecting MVP

Each spec is implementation-ready: file structure, interfaces, acceptance criteria, agent prompts

v3.1 — Updated with Qwen3 models · Ratatui 0.30+ · SearXNG engine config subprocess timeouts · FIM suffix fix · MinerU pipeline install

# HOW TO USE THIS DOCUMENT

Each MVP is a self-contained spec designed to be handed directly to a coding agent (Continue.dev, Claude Code, or any LLM with code tools). The agent prompt at the end of each MVP is the exact text you paste in to kick off implementation. MVPs are ordered by dependency — implement them in sequence. Each one produces working software that the next MVP builds on.

## ⚠️ HARDWARE PERFORMANCE REFERENCE — i7-1165G7 (16 GB DDR4)

All timings below are benchmarked estimates for CPU-only inference via Ollama on this machine.

| Model | Role | Speed | RAM Used | Notes |
|---|---|---|---|---|
| **qwen3:14b-q4_K_M** | chat / fix / diagnose | **3–5 tok/s** | ~9–10 GB | Slow but capable; keep loaded during active coding via keepalive ping |
| **mistral:7b-q4_K_M** | clean / summarize / classify | **6–10 tok/s** | ~5 GB | Unload immediately after background tasks (`keep_alive: 0`) |
| **qwen3:1.7b-q4_K_M** | FIM autocomplete | **25–40 tok/s** | ~1.2 GB | Fast enough for interactive insert-mode completion |
| **nomic-embed-text** | embeddings | instant | ~0.3 GB | Tiny, can always stay loaded |

> **KEY CONSTRAINT**: A 14B model (9GB) + OS overhead + background daemons + Rust compilation spikes can exceed 16GB, triggering SSD swap and freezing the system. The concurrency lock (MVP 1) and RAM-aware keepalive strategy below are **mandatory** on this hardware.

## ⚠️ BREAKING CHANGES FROM RESEARCH

### 1. Delete `local-ai.nix` Immediately

**Status**: On your Dell Vostro 3510 with i7-1165G7 (Intel Iris Xe integrated graphics), CUDA is entirely inoperative. `local-ai.nix` is dead code that causes `nix flake check` errors.

**Action**: 
- Remove `/home/qwerty/NixOSenv/modules/local-ai.nix`
- Remove import line from `configuration.nix`
- Run `nix flake check` — build will be clean

**Why**: You have no NVIDIA GPU. CUDA packages cannot be resolved. Your Jarvis system handles local AI entirely through `services.ollama` + the Python pipeline layer. `local-ai.nix` adds nothing and breaks validation.

### 2. Model Upgrades (From Research Findings)

| Aspect | Old Spec | New Spec | Reason |
|--------|----------|----------|--------|
| **Chat Model** | qwen2.5-coder:14b-instruct-q4_K_M | **qwen3:14b-q4_K_M** | Same file size (~9GB), equivalent to 32B performance. Better STEM, coding, reasoning. |
| **FIM Model** | qwen2.5-coder:1.5b-instruct-q4_K_M | **qwen3:1.7b-q4_K_M** | Marginally larger, significantly smarter. Same speed tier. |
| **Fast Model** | mistral:7b-instruct-q4_K_M | Keep OR try qwen3:8b-q4_K_M | Mistral 7B proven stable. Qwen3-8B option for future. |
| **Embed Model** | nomic-embed-text | ✓ Keep (768-dim, optimal) | No change. Verified production-grade. |

### 3. Qwen3 Thinking Mode Integration

**New Capability**: Qwen3-14B supports a `/think` prefix for extended reasoning and `/no_think` for fast mode.

**MVP Impact**: Update `model_router.py` to accept a `thinking` flag:

```python
def route(task: str, context_chars: int = 0, thinking: bool = False) -> str:
    rules = {
        'fix': 'chat',      # Use thinking=True for complex fixes
        'diagnose': 'chat', # Use thinking=True for NixOS errors
        'chat': 'chat',     # thinking=True for deep reasoning, False for speed
        'complete': 'complete',  # Never use thinking for autocomplete
        'clean': 'fast',
        'summarize': 'fast',
    }
    return rules.get(task, 'chat')

# In ollama_client.py, prepend to user message:
# if thinking: prompt = "/think\n" + prompt
# else: prompt = "/no_think\n" + prompt (for speed-critical tasks)
```

**Usage in MVPs**:
- `route('fix', thinking=True)` — Agent loop for deep problem-solving
- `route('chat', thinking=False)` — RAG chat for quick answers
- `route('clean', thinking=False)` — Document cleaning (speed essential)
- `route('complete', thinking=False)` — FIM autocomplete (never use thinking)

### 4. Ratatui Version Update

**Current Spec**: `ratatui = "0.29"`  
**Updated Spec**: `ratatui = "0.30+"` with `crossterm = "0.29"`

**Why**: v0.30 fixes flicker, improves `StatefulWidget`, matches current Rust TUI ecosystem (2026).

**Action**: Update `Cargo.toml` in MVP 14 before starting.

### 5. SearXNG Configuration Enhancement

**Existing Approach**: ✓ Correct. SearXNG replaces DuckDuckGo API.

**Enhancement**: Configure SearXNG engines in `settings.yml` to prioritize technical queries:

```yaml
# searxng/settings.yml additions
engines:
  - name: github
    engine: github
    disabled: false
  - name: stackoverflow
    engine: stackoverflow
    disabled: false
  - name: arxiv
    engine: arxiv
    disabled: false
```

**MVP 8 Impact**: Research agent will now return:
- GitHub repositories + issues (for code references)
- Stack Overflow answers (for problem-solving)
- arXiv papers (for academic/STEM queries)
- Web results (fallback for general queries)

**No code changes required** — same SearXNG JSON interface.

### 6. Subprocess Safety: Always Add `timeout=`

**Current MVP 5 & 7 Spec**: Correct subprocess list-form usage.

**Enhancement**: Every subprocess call must have `timeout=` parameter.

**MVP 5 (ingest.py)**: 
```python
subprocess.run(['mineru', '-p', file, '-o', tmp_dir, '-b', 'pipeline'],
               timeout=600,  # 10 min for large PDFs
               capture_output=True)
```

**MVP 7 (agent_loop.py)**: 
```python
result = subprocess.run(validate_cmd, 
                       timeout=120,  # Nix flake check can hang
                       capture_output=True)
```

**MVP 9 (git_summarizer.py)**: 
```python
subprocess.run(['git', 'diff', before, after], 
               timeout=30,
               capture_output=True)
```

**Rule**: Default timeout 60s for most operations. Nix/MinerU operations 120-600s.

### 7. MinerU: No Changes, But Know Your Alternatives

**Current Spec**: `subprocess(['mineru', '-p', file, '-o', tmp_dir, '-b', 'pipeline'])`

**Status**: ✓ Correct. `-b pipeline` is CPU-only mode.

**Enhancement**: Optional routing in `ingest.py`:
```python
# For simple academic/text PDFs, use faster alternative
if file.endswith('_research.pdf') or file.size < 5_MB:
    subprocess.run(['marker', '--pdf-path', file], timeout=60)
else:
    subprocess.run(['mineru', ...], timeout=300)  # Complex docs → MinerU
```

**No mandate to change** — MinerU handles everything. Marker is optional for speed.


# Tech Stack

<table><tr><td rowspan=1 colspan=1>Language</td><td rowspan=1 colspan=1>Python 3.12 (available in your NixOS config)</td></tr><tr><td rowspan=1 colspan=1>HTTP</td><td rowspan=1 colspan=1>requests library (pip install requests)</td></tr><tr><td rowspan=1 colspan=1>Async</td><td rowspan=1 colspan=1>asyncio + aiohttp where specified</td></tr><tr><td rowspan=1 colspan=1>Config</td><td rowspan=1 colspan=1>TOML files in /THE_VAULT/jarvis/config/</td></tr><tr><td rowspan=1 colspan=1>Storage</td><td rowspan=1 colspan=1>/THE_VAULT/jarvis/ for all Jarvis data</td></tr></table>

# MVP 1 — Ollama Gateway

Typed Python client for the Ollama API — used by every other MVP. A single Python module that wraps the Ollama REST API with typed functions, error handling, retry logic, and streaming support. All other MVPs import from this module instead of writing raw HTTP calls.

<table><tr><td rowspan=1 colspan=1>Language</td><td rowspan=1 colspan=1>Python 3.12</td></tr><tr><td rowspan=1 colspan=1>Output</td><td rowspan=1 colspan=1>Single module: /THE_VAULT/jarvis/lib/ollama_client.py</td></tr><tr><td rowspan=1 colspan=1>Interface</td><td rowspan=1 colspan=1>Functions: chat(), generate(), embed(), list_models(), is_healthy0, chat_managed()</td></tr><tr><td rowspan=1 colspan=1>Config</td><td rowspan=1 colspan=1>Reads OLLAMA_BASE_URL from env, default htp://localhost:11434</td></tr><tr><td rowspan=1 colspan=1>Error policy</td><td rowspan=1 colspan=1>Retry 3x with exponential backoff on connection errors. Raise OllamaError on modelerrors.</td></tr><tr><td rowspan=1 colspan=1>Streaming</td><td rowspan=1 colspan=1>chat() and generate() accept stream=True, yield tokens as they arrive</td></tr></table>

$\spadesuit$ UPDATED: chat_managed() added for context compression. model_router import added.

# Public Interface

def is_healthy() $- >$ bool # GET /api/tags — returns True if Ollama is reachable   
def list_models() $- >$ list[str] # Returns list of pulled model names   
def chat(model: str, messages: list[dict], system: str $=$ None, stream: bool $=$ False, temperature: float $= ~ 0 . 2$ ) $- >$ str | Generator[str, None, None] # POST /api/chat. stream=True yields token strings.   
def generate(model: str, prompt: str, system: str $=$ None, stream: bool $=$ False, suffix: str $=$ None) $- >$ str | Generator[str, None, None] # POST /api/generate. Single-turn, no history. # NOTE: pass suffix= for FIM autocomplete (required by /complete endpoint in MVP 12)   
def embed(model: str, text: str) $- >$ list[float] # POST /api/embed. Returns embedding vector.   
def chat_managed(model: str, messages: list[dict], system: str $=$ None, max_chars: int $= ~ 5 0 0 0$ ) -> str # Summarises old context before overflow — prevents quality degradation. # If total chars $>$ max_chars and len(messages) $> ~ 6$ , summarises earliest messages.   
class OllamaError(Exception): ...   
class ModelNotFoundError(OllamaError): ...   
class ConnectionError(OllamaError): ...

# models.toml

# [models]

chat $=$ "qwen3:14b-q4_K_M" fast $=$ "mistral:7b-instruct-q4_K_M" complete $=$ "qwen3:1.7b-q4_K_M" embed $=$ "nomic-embed-text"

# upgraded from qwen2.5-coder:14b # upgraded from qwen2.5-coder:1.5b

[model_digests]

# Run: ollama show <model> --modelfile grep FROM copy SHA after pulling # Pinning prevents silent weight updates from breaking your optimised prompts. chat $=$ "sha256:.. # fill after: ollama pull qwen3:14b-q4_K_M fast $=$ "sha256:.. # fill after: ollama pull mistral:7b-instruct-q4_K_M complete $=$ "sha256:.. # fill after: ollama pull qwen3:1.7b-q4_K_M embed $=$ "sha256:... # fill after: ollama pull nomic-embed-text

# Qwen3 Thinking Mode — model_router integration

# lib/model_router.py — route() signature updated def route(task: str, context_chars: int $\qquad = \quad 0$ , thinking: bool $=$ False) $- >$ str: # Returns model alias string # thinking $\bf \tilde { = }$ True injects /think prefix for fix/diagnose/reason tasks # thinking $\bf \tilde { = }$ False injects /no_think for speed-critical tasks (clean, summarize)

# Usage in any MVP:

from lib.model_router import route response $=$ chat(route('fix', thinking $^ { \ast } =$ True), messages) $\# $ qwen3:14b, thinking on response $=$ chat(route('summarize'), messages) # mistral:7b, no thinking response $=$ chat(route('clean'), messages) $\# $ mistral:7b, no thinking

# Acceptance Criteria

$\checkmark$ is_healthy() returns True when Ollama is running, False when it is not   
✓ chat('fast', [{'role':'user','content':'say hello'}]) returns a non-empty string in under 30 seconds   
✓ chat(..., stream $\vDash$ True) yields at least 5 string tokens before completion   
✓ embed('embed', 'hello world') returns a list of floats with length $> 1 0 0$   
✓ Connection failure triggers 3 retries then raises ConnectionError with a message containing the URL   
✓ ModelNotFoundError is raised when an invalid model name is passed   
✓ generate(..., suffix $\smash { \boldsymbol { \mathbf { \ell } } = \frac { 1 } { 2 } \ldots } ^ { \prime }$ ) correctly passes suffix to /api/generate for FIM   
✓ chat_managed() summarises context when total chars $>$ max_chars   
✓ All functions are importable from: from lib.ollama_client import chat, embed, is_healthy

# AGENT PROMPT — paste into Claude Code / Continue.dev

Implement /THE_VAULT/jarvis/lib/ollama_client.py. Wrap the Ollama REST API (base URL from OLLAMA_BASE_URL env, default http://localhost:11434) with: is_healthy(), list_models(), chat(), generate(), embed(), chat_managed().   
Use the requests library. chat() and generate() must support stream=True yielding string tokens. generate() must accept a suffix $\bar { . } \equiv$ parameter for FIM; pass it to /api/generate as {"suffix": suffix}. chat_managed() summarises old context (via chat()) when total message chars $>$ max_chars and len(messages) $>$ 6.   
Retry on connection errors $3 \mathrm { x }$ with exponential backoff (1s, 2s, 4s). Raise OllamaError subclasses on failure.
CRITICAL: Implement a global concurrency lock using `filelock` on `/THE_VAULT/jarvis/logs/ollama.lock` with a 1800s timeout. Read model aliases from   
/THE_VAULT/jarvis/config/models.toml using tomllib. Write a test block at the bottom under if __name_ $\mathbf { \Sigma } = \mathbf { \Sigma } \cdot \mathbf { \Sigma }$ __main__' that calls is_healthy(),   
list_models(), and a short chat() call, printing results.   
No external libraries except requests and tomllib.

CRITICAL — RAM-AWARE KEEP_ALIVE STRATEGY (i7-1165G7, 16 GB RAM):
All `chat()` and `generate()` calls MUST pass `keep_alive` in the JSON body.
- For `route('fix')` and `route('chat')` (qwen3:14b — active coding): pass `keep_alive: '5m'` — keeps the model in RAM during an active session.
- For `route('clean')`, `route('summarize')`, `route('classify')` (mistral:7b — background tasks): pass `keep_alive: 0` — unloads the model IMMEDIATELY after the call to free ~5 GB of RAM.
- For `route('complete')` (qwen3:1.7b — FIM): pass `keep_alive: '10m'` — keep tiny model always loaded since it uses minimal RAM.

# MVP 2 — Document Chunker

Depends on: MVP 1

Split MinerU Markdown output into semantic chunks for RAG indexing. Takes the raw .md file from MinerU and splits it into chunks suitable for embedding. Supports three strategies: by heading, by token count with overlap, or by page break markers. Outputs chunks as individual .md files and a manifest JSON.

<table><tr><td rowspan=1 colspan=1>Language</td><td rowspan=1 colspan=1>Python 3.12</td></tr><tr><td rowspan=1 colspan=1>Input</td><td rowspan=1 colspan=1>Path to a .md file (MinerU output)</td></tr><tr><td rowspan=1 colspan=1>Output</td><td rowspan=1 colspan=1>Directory of chunk files + chunks_manifest,json</td></tr><tr><td rowspan=1 colspan=1>Strategies</td><td rowspan=1 colspan=1>--by-heading (default), -by-tokens N, -by-page</td></tr><tr><td rowspan=1 colspan=1>CLI</td><td rowspan=1 colspan=1>python chunker.py [-strategy] [--overlap N]</td></tr><tr><td rowspan=1 colspan=1>Manifest</td><td rowspan=1 colspan=1>JSON array: [{chunk_id, file, char_start, char_end, heading, token_estimate]]</td></tr></table>

# chunker.toml

# [chunker]

default_strategy $=$ 'heading'   
max_tokens $= ~ 1 5 0 0$   
overlap_tokens $= \ 2 0 0$   
min_chunk_tokens $= ~ 5 0$ # discard chunks smaller than this   
heading_levels = [2, 3] # split on ## and ###

# Acceptance Criteria

✓ A 300-page MinerU .md file produces between 20 and 500 chunk files depending on heading count ✓ Each chunk file is valid UTF-8 Markdown starting with the heading that introduced it ✓ chunks_manifest.json is valid JSON with one entry per chunk file, char_start/char_end are correct ✓ No chunk exceeds max_tokens $\star _ { 6 }$ characters ✓ Chunks with fewer than min_chunk_tokens characters are silently discarded ✓ --by-tokens mode produces chunks of approximately max_tokens tokens with overlap_tokens of overlap ✓ Running chunker.py on the same input twice produces identical output (deterministic)

# AGENT PROMPT — paste into Claude Code / Continue.dev

Implement /THE_VAULT/jarvis/tools/chunker.py. It takes a MinerU .md file and splits it into chunks using three strategies selectable via CLI flag:   
(1) --by-heading splits on ## and ### headings, each chunk starts with its heading and includes all content until the next heading of equal or higher level;   
(2) --by-tokens N splits into chunks of N tokens (estimate: 1 token $\qquad = ~ 4$ chars) with --overlap M chars of overlap;   
(3) --by-page splits on horizontal rules (---) or form-feed characters.   
Read defaults from /THE_VAULT/jarvis/config/chunker.toml using tomllib.   
Output: one .md file per chunk named chunk_0001.md, chunk_0002.md etc., plus chunks_manifest.json with schema [{chunk_id, file, char_start, char_end,   
heading, token_estimate}]. Print a summary line:   
'Split into N chunks, total M chars' on completion.   
No external deps except tomllib.

# MVP 3 — Document Cleaner

Depends on: MVP 1 → MVP 2

Applies the NotebookLM cleaning prompt to each chunk from MVP 2 via the Ollama API, then reassembles the cleaned chunks into a single output file. Reads the cleaning prompt from /THE_VAULT/prompts/notebooklm/best.txt so it can be upgraded by MVP 6 without code changes.

<table><tr><td rowspan=1 colspan=1>Language</td><td rowspan=1 colspan=1>Python 3.12</td></tr><tr><td rowspan=1 colspan=1>Input</td><td rowspan=1 colspan=1>Path to .md file OR path to chunks_manifest.json from MVP 2</td></tr><tr><td rowspan=1 colspan=1>Output</td><td rowspan=1 colspan=1>_clean.md in same directory as input</td></tr><tr><td rowspan=1 colspan=1>Prompt src</td><td rowspan=1 colspan=1>/THE_VAULT/prompts/notebookIm/best.txt (falls back to builtin default)</td></tr><tr><td rowspan=1 colspan=1>Model</td><td rowspan=1 colspan=1>route(&#x27;clean&#x27;) → mistral:7b — speed over quality for cleaning</td></tr><tr><td rowspan=1 colspan=1>CLI</td><td rowspan=1 colspan=1>python cleaner.py [-model MODEL] [-prompt-file PATH]</td></tr><tr><td rowspan=1 colspan=1>Parallelism</td><td rowspan=1 colspan=1>Process chunks sequentially (OLLAMA_NUM_PARALLEL=1 on this machine)</td></tr><tr><td rowspan=1 colspan=1>Progress</td><td rowspan=1 colspan=1>Print&#x27;Cleaning chunk N/Total.&#x27; to stdout with estimated time remaining</td></tr></table>

# Built-in Cleaning Prompt (default.txt)

You are a document preparation assistant. Clean and optimise this Markdown for upload to NotebookLM. NotebookLM is text-only.

REMOVE: image tags ![...](...), dead figure references (Fig. N, See diagram), page number echoes, running headers/footers, orphaned footnote markers, full reference lists at end of document, index sections, TOC pages, repeated copyright boilerplate.

PRESERVE: all prose, headings hierarchy, data tables, inline citations (Author Year), footnote bodies, code blocks, equations.

CONVERT figure captions to plain paragraphs prefixed 'Caption:'.   
Output ONLY the cleaned Markdown. No commentary. No preamble.

# Acceptance Criteria

✓ Output file contains no Markdown image syntax: ![   
✓ Output file is $5 5 \mathrm { - } 9 5 \%$ the length of the input (significant reduction but content preserved)   
$\checkmark$ All ## and ### headings from the input are present in the output   
✓ Running on a manifest.json reassembles chunks in order with no duplicate headings at joins   
✓ If /THE_VAULT/prompts/notebooklm/best.txt exists, it is used instead of default.txt   
✓ Progress output shows chunk N/Total with percentage on each step   
✓ On Ollama connection failure, the cleaner exits with code 1 and prints the failed chunk number

Implement /THE_VAULT/jarvis/tools/cleaner.py. It cleans a MinerU .md file for NotebookLM upload. If given a .md file directly, use MVP 2's chunker to split it first. If given a chunks_manifest.json, load the pre-chunked files. For each chunk: read the cleaning prompt from /THE_VAULT/prompts/notebooklm/best.txt (fall back to bundled default.txt constant if missing), call ollama_client.chat() with the prompt as system message and the chunk as user message, using route('clean') from lib.model_router. Reassemble cleaned chunks into <input_stem>_clean.md, joining on double newline. Print progress: 'Cleaning chunk N/M (X%)...'. Bundle default.txt as a string constant. Import OllamaError and exit with code 1 on failure.
IDEMPOTENCY: Before cleaning each chunk, compute its SHA256 hash and check against cleaned_hashes.txt in the output directory. If already present, skip Ollama call and reuse cached output. This prevents re-cleaning the same 300-page book on repeated runs (which takes 20+ min on CPU).
IDEMPOTENCY: Before cleaning each chunk, compute its SHA256 hash and check against cleaned_hashes.txt in the output directory. If already present, skip Ollama call and reuse cached output. This prevents re-cleaning the same 300-page book on repeated runs (which takes 20+ min on CPU).

# MVP 4 — AnythingLLM Feeder

Depends on: MVP 1

Wraps the AnythingLLM REST API to upload documents to workspaces programmatically. Used by systemd user timers and the document ingestion pipeline to add cleaned Markdown files to the correct workspace without manual UI interaction.

<table><tr><td rowspan=1 colspan=1>Language</td><td rowspan=1 colspan=1>Python 3.12</td></tr><tr><td rowspan=1 colspan=1>Output</td><td rowspan=1 colspan=1>/THE_VAULT/jarvis/lib/anythingllm_client.py</td></tr><tr><td rowspan=1 colspan=1>Interface</td><td rowspan=1 colspan=1>Functions: upload_document), list_workspaces(0, create_workspace(),get_workspace_id()</td></tr><tr><td rowspan=1 colspan=1>Config</td><td rowspan=1 colspan=1>ANYTHINGLLM_BASE_URL (default http://localhost:3001),ANYTHINGLLM_API_KEY from env</td></tr><tr><td rowspan=1 colspan=1>CLI mode</td><td rowspan=1 colspan=1>python anythingllm_client.py upload</td></tr><tr><td rowspan=1 colspan=1>Error</td><td rowspan=1 colspan=1>Raise AnythingLLMError with status code and message on HTTP errors</td></tr></table>

# Public Interface

def list_workspaces() $- >$ list[dict] # GET /api/v1/workspaces — returns [{id, name, slug}]   
def get_workspace_id(name: str) -> str | None # Find workspace by name, return slug or None   
def create_workspace(name: str) -> str # POST /api/v1/workspace/new — returns new workspace slug   
def upload_document(workspace_name: str, file_path: str, create_if_missing: bool $=$ True) $- >$ dict # POST /api/v1/workspace/{slug}/upload # Returns {success, document_id, message}   
def delete_document(workspace_name: str, document_id: str) $- >$ bool # DELETE /api/v1/workspace/{slug}/remove-documents   
class AnythingLLMError(Exception): ...

# Acceptance Criteria

✓ list_workspaces() returns a list (empty list if no workspaces, not an error)   
✓ upload_document('MinerU Output', 'test.md', create_if_missing $\vDash$ True) creates workspace if missing then uploads   
✓ Uploading the same file twice to the same workspace does not create duplicates (idempotent)   
✓ AnythingLLMError is raised with a readable message when the API key is wrong   
✓ CLI: python anythingllm_client.py upload 'Research' /path/to/doc.md prints success/failure   
✓ get_workspace_id('NonExistent') returns None without raising an exception

AGENT PROMPT — paste into Claude Code / Continue.dev

Implement /THE_VAULT/jarvis/lib/anythingllm_client.py. It wraps the   
AnythingLLM REST API. Read ANYTHINGLLM_BASE_URL (default http://localhost:3001) and ANYTHINGLLM_API_KEY from environment variables. Implement:   
list_workspaces() -> list[dict], get_workspace_id(name) -> str|None,   
create_workspace(name) -> str (returns slug),   
upload_document(workspace_name, file_path, create_if_missing $: =$ True) -> dict, delete_document(workspace_name, document_id) $- >$ bool. Use requests library. Send API key as Authorization: Bearer <key> header on all requests.   
upload_document should POST the file as multipart/form-data. Raise   
AnythingLLMError(message, status_code) on HTTP errors. Add CLI entrypoint: if __name_ $= =$ '__main__' parse sys.argv for 'upload <workspace> <file>' and call upload_document, printing result.

# MVP 5 — Document Ingestion Pipeline

Depends on: MVP $\begin{array} { r } { 1  M V P 2  M V P 3  M V P 4 } \end{array}$

A daemon that watches /THE_VAULT/jarvis/inbox/ for new files. On a new .pdf it runs MinerU (CPU pipeline mode), then the cleaner, then uploads the result to AnythingLLM. On a new .md it runs the cleaner then uploads. Maintains a processed log so it never processes the same file twice.

<table><tr><td rowspan=1 colspan=1>Language</td><td rowspan=1 colspan=1>Python 3.12</td></tr><tr><td rowspan=1 colspan=1>Output</td><td rowspan=1 colspan=1>/THE_VAULT/jarvis/pipelines/ingest.py</td></tr><tr><td rowspan=1 colspan=1>Watch dir</td><td rowspan=1 colspan=1>/THE_VAULT/jarvis/inbox/</td></tr><tr><td rowspan=1 colspan=1>Trigger</td><td rowspan=1 colspan=1>File placed in inbox/ (uses inotify via watchdog library or polling fallback)</td></tr><tr><td rowspan=1 colspan=1>Routing</td><td rowspan=1 colspan=1>.pdf → mineru → cleaner → anythingllm |.md → cleaner → anythingllm</td></tr><tr><td rowspan=1 colspan=1>Workspace</td><td rowspan=1 colspan=1>Filename prefix determines workspace (see routing rules below)</td></tr><tr><td rowspan=1 colspan=1>Log</td><td rowspan=1 colspan=1>/THE_VAULT/jarvis/logs/ingestion.jsonl — one JSON line per processed file</td></tr><tr><td rowspan=1 colspan=1>Run mode</td><td rowspan=1 colspan=1>python ingest.py --watch (daemon) I python ingest.py --once (single file)</td></tr><tr><td rowspan=1 colspan=1>MinerU install</td><td rowspan=1 colspan=1>pip instal mineru[pipline] — NOT ineru[ll (avoids plling GPU deps)</td></tr></table>

$\spadesuit$ UPDATED: MinerU installed as mineru[pipeline] only — no GPU deps on i7-1165G7.

# Workspace Routing Rules

PREFIX_MAP $=$ { "research_": "Research", "nixos_": "NixOS Config", "code_": "Codebase", "personal_": "Personal", "mineru_": "MinerU Output", "journal_": "Personal", # journal_YYYY-MM-DD.md auto-indexed   
# Default (no matching prefix) 'MinerU Output'

# Log Entry Schema

{ "timestamp": "2026-03-04T14:30:00Z", "file": "research_transformer_paper.pdf", "workspace": "Research", "status": "success", "steps": ["mineru", "clean", "upload"], "chunks": 42, "duration_seconds": 187, "error": null   
}

# Acceptance Criteria

✓ Dropping a .md file into inbox/ results in it appearing in AnythingLLM within 60 seconds ✓ Dropping a file already processed (same filename, same size) is skipped with status skipped ✓ On MinerU failure the log entry shows status $\underline { { \underline { { \mathbf { \delta \pi } } } } } =$ error; file is moved to failed/ not processed/ $\checkmark$ The daemon survives a restart: files already in processed/ are not re-ingested ✓ --once mode processes one file synchronously, exits 0 on success, 1 on failure

✓ ingestion.jsonl is valid JSONL (one JSON object per line, newline-delimited)

# AGENT PROMPT — paste into Claude Code / Continue.dev

Implement /THE_VAULT/jarvis/pipelines/ingest.py. It watches   
/THE_VAULT/jarvis/inbox/ for new files using the watchdog library with a polling fallback. MinerU is installed as mineru[pipeline] (CPU-only). On a new file: (0) trigger notify-send start notification; (1) determine workspace from PREFIX_MAP; (2) if .pdf, run   
subprocess(['mineru', '-p', file, '-o', tmp_dir, '-b', 'pipeline'],   
timeout $= 6 0 0$ ) — always list-form, never shell $. =$ True;   
(3) run cleaner.py on the .md; (4) upload via anythingllm_client.upload_document(); (5) move original to /THE_VAULT/jarvis/processed/; (6) append JSON log line to ingestion.jsonl; (7) trigger success/fail notify-send. Track processed files by SHA256 hash in processed_hashes.txt. Support --watch and --once <file> CLI modes. Emit events via lib.event_bus. Implement daily cleanup to delete >30 day old files in `processed/`.

# MVP 6 — Prompt Optimizer

Depends on: MVP 1

The self-improving engine. Given a task spec (JSON), generates prompt variants via meta-prompt, evaluates each variant against test inputs using a scoring function, and promotes the best variant. Runs manually or on a schedule. Makes the whole system improve without your involvement.

<table><tr><td rowspan=1 colspan=1>Language</td><td rowspan=1 colspan=1>Python 3.12</td></tr><tr><td rowspan=1 colspan=1>Output</td><td rowspan=1 colspan=1>/THE_VAULT/jarvis/pipelines/optimizer.py</td></tr><tr><td rowspan=1 colspan=1>Input</td><td rowspan=1 colspan=1>/THE_VAULT/prompts//spec.json</td></tr><tr><td rowspan=1 colspan=1>Output files</td><td rowspan=1 colspan=1>/THE_VAULT/prompts//best.txt (winner), runs/ (history)</td></tr><tr><td rowspan=1 colspan=1>CLI</td><td rowspan=1 colspan=1>python optimizer.py [--rounds N] [--variants N]</td></tr><tr><td rowspan=1 colspan=1>Models</td><td rowspan=1 colspan=1>Meta-prompt: route(&#x27;reason&#x27;, thinking=True) | Evaluation: route(&#x27;score&#x27;)</td></tr></table>

$\spadesuit$ UPDATED: Meta-prompt uses route('reason', thinking=True) for Qwen3 deep reasoning.

# spec.json Schema

"task_name": "notebooklm", "task_description": "Clean MinerU Markdown for NotebookLM upload", "test_inputs": ["path/to/test_chunk_1.md", "path/to/test_chunk_2.md"], "quality_rules": [ {"type": "not_contains", "value": "![", "weight": 1.0}, {"type": "length_ratio", "min": 0.55, "max": 0.95, "weight": 0.8}, {"type": "contains_all", "values": ["##"], "weight": 0.7}, {"type": "not_contains", "value": "Figure ", "weight": 0.5} ], "num_variants": 5, "current_best": "prompts/notebooklm/best.txt" }

# Acceptance Criteria

✓ Running optimizer.py notebooklm produces at least 3 candidate prompts and scores each one   
✓ The winning prompt is written to /THE_VAULT/prompts/notebooklm/best.txt   
✓ A run log is written to /THE_VAULT/prompts/notebooklm/runs/.json   
$\checkmark$ If the new winner scores lower than current best.txt, best.txt is NOT overwritten (regression protection)   
✓ Running optimizer.py twice produces different variants (temperature $> 0 . 5$ )   
✓ spec.json validation: exits with a clear error if spec.json is malformed

# AGENT PROMPT — paste into Claude Code / Continue.dev

Implement /THE_VAULT/jarvis/pipelines/optimizer.py. Reads   
/THE_VAULT/prompts/<task>/spec.json, calls ollama_client.chat() with a meta-prompt using route('reason', thinking $: =$ True) asking for num_variants different prompt approaches, parses the JSON array response, then for each variant runs it against each test_input via chat() using route('score'), scores the output using quality_rules   
(implement: not_contains, contains_all, length_ratio, llm_judge),   
computes a weighted total score, saves all results to   
/THE_VAULT/prompts/<task>/runs/<ISO_timestamp>.json.   
Promote the top variant to best.txt ONLY if its score exceeds current best.txt score. Print a results table: variant number, score, whether promoted.   
CLI: optimizer.py <task_name> [--rounds N] [--max-time SECONDS] [--dry-run].
--max-time (default 3600): abort the run if wall-clock time exceeds this value, write partial results, and emit a 'timeout' event. Prevents the Sunday 03:00 systemd timer trigger from still running at 07:00.
--dry-run: generate and print variants only, skip scoring and promotion. Lets you preview what the meta-prompt will produce without locking the CPU for hours.

# MVP 7 — Looped Reasoning Agent

# Depends on: MVP 1

Runs an agentic loop: ask Ollama to produce an output, run a validation command, inject errors back as context if it fails, retry up to N times. Designed for code generation tasks where the validation is a real command (nix flake check, cargo test, python -m py_compile, etc.).

<table><tr><td rowspan=1 colspan=1>Language</td><td rowspan=1 colspan=1>Python 3.12</td></tr><tr><td rowspan=1 colspan=1>Output</td><td rowspan=1 colspan=1>/THE_VAULT/jarvis/pipelines/agent_loop.py</td></tr><tr><td rowspan=1 colspan=1>CLI</td><td rowspan=1 colspan=1>python agent_loop.Py -ask TASK --validate CMD --output FILE [-max-retries N]</td></tr><tr><td rowspan=1 colspan=1>Config</td><td rowspan=1 colspan=1>Task configs in /THE_VAULT/jarvis/config/agent_tasks/</td></tr><tr><td rowspan=1 colspan=1>Escalation</td><td rowspan=1 colspan=1>After max_retries: write to /THE_VAULT/jarvis/review/_.md</td></tr><tr><td rowspan=1 colspan=1>Model</td><td rowspan=1 colspan=1>route(&quot;fix&#x27;, thinking=True) — Qwen3 14B with thinking enabled for agent tasks</td></tr><tr><td rowspan=1 colspan=1>Subprocess</td><td rowspan=1 colspan=1>ALWAYS use list-form subprocess. NEVER shell=True. ALWAYS set timeout=60.</td></tr></table>

$\spadesuit$ UPDATED: route('fix', thinking=True) — Qwen3 thinking mode for better fix quality. timeou $\mathtt { \sigma } = 6 0$ on all subprocess calls.

# Loop Design

context $=$ [system_prompt, user_task]   
for attempt in range(1, max_retries $^ { + } \perp$ ): response $=$ chat_managed(route('fix', thinking $\bf \tilde { = }$ True), context) extracted $=$ extract_code_block(response) write_to_temp_file(extracted) # ALWAYS list-form, NEVER shell $=$ True, ALWAYS timeout= result $=$ subprocess.run( validate_cmd_as_list, # e.g. ['nix', 'flake', 'check', '--no-build'] capture_output $=$ True, timeout $= 6 0$ # required on every subprocess call ) if result.returncode $\qquad = = \quad 0$ : write_to_output_file(extracted) emit('fix', 'completed', {'task': task, 'attempts': attempt}) break else: context.append({'role': 'assistant', 'content': response}) context.append({'role': 'user', 'content': f'That failed. Error:\n{result.stderr}\nFix it.'})

write_escalation_file(task, context, last_response)

# Acceptance Criteria

✓ Given a task 'write a Python function that returns the sum of a list' with validate $: = "$ python -m py_compile {file}', it produces a valid .py file

$\checkmark$ If the first attempt fails validation, the error output is injected into context and a second attempt is made

✓ After max_retries failed attempts, an escalation file is written and the process exits with code 2

✓ The loop prints attempt number and validation result on each iteration

✓ extract_code_block() correctly extracts content from \`\`\`python...\`\`\` and \`\`\`nix...\`\`\` blocks

✓ The output file is only written on validation success, never on failure

✓ All subprocess calls use list-form args and timeout
✓ Subprocess timeout is language-aware: python -m py_compile=30s, cargo check=60s, nix flake check=120s. Validate command timeout is passed as a config key `timeout_seconds` in the agent_tasks/*.toml file — default 60.
✓ Subprocess timeout is language-aware: python -m py_compile=30s, cargo check=60s, nix flake check=120s. Validate command timeout is passed as a config key `timeout_seconds` in the agent_tasks/*.toml file — default 60. $\mathtt { - 6 0 }$

# AGENT PROMPT — paste into Claude Code / Continue.dev

Implement /THE_VAULT/jarvis/pipelines/agent_loop.py. CLI: --task TASK   
--user-prompt TEXT --output FILE [--max-retries N default 5].   
Load task config from /THE_VAULT/jarvis/config/agent_tasks/<task>.toml using tomllib. Build conversation: system prompt from config, then user-prompt as first user message. Each round: call chat_managed(route('fix', thinking=True), messages) from ollama_client, extract first fenced code block using regex $\therefore \overrightarrow { \vert } \cdot \overrightarrow { \vert } \cdot \sin ( [ \overrightarrow { \vert } \cdot \overrightarrow { \vert } ] + \overrightarrow { \vert } \cdot \overrightarrow { \vert } ) \cdot \overrightarrow { \vert } \cdot \overrightarrow { \vert }$ , write to temp file, run validate command as list-form subprocess (replace {output_file} with temp path), subprocess.run(..., capture_output $=$ True, timeout $= 6 0$ ). On returncode $\scriptstyle = = 0$ : display the code diff and prompt interactively `[Y/n]` to approve. If yes, copy to --output, emit $\operatorname { \mathbb { E } } \dot { \bot } \mathbf { x }$ completed event, print SUCCESS, exit 0. On failure: append error to conversation, retry. After max_retries: write full conversation to review/<task>_<timestamp>.md, emit fix escalated event, exit 2.

# MVP 8 — Research Agent

Depends on: MVP 1 → MVP 4

Runs a research workflow: takes a topic query, searches SearXNG (self-hosted, no API key), fetches the top N pages, chunks and summarizes each one via Ollama, and uploads the summaries to the Research workspace in AnythingLLM. Triggered from CLI or by systemd timer.

<table><tr><td rowspan=1 colspan=1>Language</td><td rowspan=1 colspan=1>Python 3.12</td></tr><tr><td rowspan=1 colspan=1>Output</td><td rowspan=1 colspan=1>/THE_VAULT/jarvis/pipelines/research_agent.py</td></tr><tr><td rowspan=1 colspan=1>Search</td><td rowspan=1 colspan=1>SearXNG at http://localhost:8888 — self-hosted, full results, no rate limits</td></tr><tr><td rowspan=1 colspan=1>Fetch</td><td rowspan=1 colspan=1>requests.get() with 10s timeout and User-Agent header. Skip if fetch fails.</td></tr><tr><td rowspan=1 colspan=1>Parse</td><td rowspan=1 colspan=1>Extract visible text from HTML using html.parser (stdlib). Strip scripts/styles.</td></tr><tr><td rowspan=1 colspan=1>Summarize</td><td rowspan=1 colspan=1>Each page: call Ollama with summarization prompt, max 300 words</td></tr><tr><td rowspan=1 colspan=1>Output</td><td rowspan=1 colspan=1>One .md file per source: /THE_VAULTjarvis/research/.md</td></tr><tr><td rowspan=1 colspan=1>CLI</td><td rowspan=1 colspan=1>python research_agent.py --query &#x27;transformer architecture&#x27;[-sources N default 5]</td></tr></table>

$\spadesuit$ UPDATED: Uses SearXNG (localhost:8888) instead of DuckDuckGo. Configure SearXNG settings.yml to enable Stack Overflow, GitHub, and arXiv engines for better technical results.

# SearXNG Engine Configuration (settings.yml)

# Add to SearXNG settings.yml engines section for best technical results: # Stack Overflow, GitHub, and arXiv give dramatically better signal # for technical queries than web-only search.   
#   
# docker run -d --name searxng --restart unless-stopped \   
# -p 127.0.0.1:8888:8080 \   
# -v \~/searxng/settings.yml:/etc/searxng/settings.yml \   
# searxng/searxng   
#   
# In settings.yml, ensure these engines are enabled:   
# - stackoverflow   
# - github   
# - arxiv   
# - google (or bing as fallback)   
#   
# research_agent.py query:   
results $=$ requests.get(   
'http://localhost:8888/search',   
params $=$ {'q': query, 'format': 'json'},   
timeout ${ } _ { , = \bot 0 }$   
).json()   
urls = [r['url'] for r in results.get('results', [])]

# Acceptance Criteria

✓ Given --query 'nixos flakes tutorial', produces at least 3 .md summary files in the research directory   
✓ Each summary file begins with: # Source: followed by the summarized content   
✓ Each summary is 100-400 words   
✓ All summary files are uploaded to the 'Research' workspace in AnythingLLM   
✓ A failing URL fetch is skipped silently with a printed warning, not a crash   
✓ Running the same query twice does not upload duplicate documents

Total runtime for 5 sources is under 10 minutes on the target hardware

# AGENT PROMPT — paste into Claude Code / Continue.dev

Implement /THE_VAULT/jarvis/pipelines/research_agent.py. CLI: --query TEXT -sources N (default 5).   
Step 1: Search SearXNG at http://localhost:8888/search?q={query}&format=json, extract results[].url (up to $\mathbb { N } ^ { \star 2 }$ candidates).   
Step 2: For each URL (up to N): requests.get(url, timeout ${ } = \beth 0$ ,   
headers={'User-Agent': 'Mozilla/5.0'}), skip on exception.   
Parse HTML with html.parser stripping <script> and <style>, extract text. SMART EXTRACTION: attempt to find content in <main>, <article>, <div role="main"> or <div class="content|post|entry"> before falling back to full <body> — this skips navbars, footers, and cookie banners which dominate the first 3000 chars of most pages. SMART EXTRACTION: attempt to find content in <main>, <article>, <div role="main"> or <div class="content|post|entry"> before falling back to full <body> — this skips navbars, footers, and cookie banners which dominate the first 3000 chars of most pages. Step 3: Call ollama_client.chat() with route('summarize') and the extracted text (truncated to 3000 chars) as user message. System: 'Summarize in 200-300 words, plain prose, focus on factual content.'   
Step 4: Write to /THE_VAULT/jarvis/research/<slug>/<domain>.md with header '# Source: $< \mathtt { u r l } > \backslash \mathtt { n } \backslash \mathtt { n } ^ { \prime }$ .   
Step 5: Call anythingllm_client.upload_document('Research', filepath).   
Emit research events via lib.event_bus. Slugify with re.sub(r'[^a-z0-9]+','_',s).

# MVP 9 — Git Monitor & Summarizer

Depends on: MVP 1, MVP 13

A background daemon that polls the local NixOS configuration repository for new commits. When a change is detected, it extracts the git diff, calls Ollama to summarize the changes in plain English, and emits the summary to the Event Bus.

<table><tr><td rowspan=1 colspan=1>Language</td><td rowspan=1 colspan=1>Python 3.12</td></tr><tr><td rowspan=1 colspan=1>Output</td><td rowspan=1 colspan=1>/THE_VAULT/jarvis/services/git_monitor.py & /THE_VAULT/jarvis/lib/git_summarizer.py</td></tr><tr><td rowspan=1 colspan=1>Architecture</td><td rowspan=1 colspan=1>Polling Daemon (NixOS User Service)</td></tr><tr><td rowspan=1 colspan=1>Interval</td><td rowspan=1 colspan=1>1 hour (configurable)</td></tr><tr><td rowspan=1 colspan=1>Observability</td><td rowspan=1 colspan=1>Emits 'git_monitor.summary_generated' to events.db</td></tr><tr><td rowspan=1 colspan=1>Git</td><td rowspan=1 colspan=1>subprocess(['git', 'diff', before, after], timeout=30)</td></tr><tr><td rowspan=1 colspan=1>Run</td><td rowspan=1 colspan=1>python services/git_monitor.py</td></tr></table>

$\spadesuit$ UPDATED: subprocess timeou $\yen 30$ on git diff call. All subprocess calls use list-form.

# CHANGELOG Entry Format

## 2026-03-04 $\mathbb { 1 4 : 3 2 }$ — commit abc1234 \*\*Author:\*\* qwerty \*\*Branch:\*\* main

Changed the Ollama client to add retry logic with exponential backoff. Added ModelNotFoundError exception class. Updated models.toml to include the qwen3 model aliases. Tests in the __main__ block now cover the error paths.

# Acceptance Criteria

✓ Server starts and responds 200 to GET /health ✓ A valid Gitea webhook POST with correct HMAC signature triggers diff extraction and Ollama call ✓ A POST with incorrect HMAC signature returns 403 and logs the rejection ✓ CHANGELOG.md entry is appended within 30 seconds of the webhook arriving ✓ Diffs larger than 4000 characters are truncated with '[diff truncated to 4000 chars]' ✓ If the repository path does not exist, the webhook returns 404 with the repo name in the message

# AGENT PROMPT — paste into Claude Code / Continue.dev

Implement /THE_VAULT/jarvis/services/git_summarizer.py. HTTP server using   
http.server stdlib on localhost:7001. POST /webhook: validate X-Gitea-Signature header (HMAC-SHA256 of request body using GITEA_WEBHOOK_SECRET env var, return 403 if invalid). Parse JSON body to get repository.full_name, commits[0].id, commits[-1].id. Find repo clone at --repos-dir/<repo_full_name>. Run   
subprocess(['git', '-C', repo_path, 'diff', before, after],   
capture_output $, =$ True, timeout $= 3 0$ ). Truncate diff to 4000 chars. Call   
ollama_client.chat() with route('summarize') and diff as user message. Append CHANGELOG entry (see spec format). Return 200 {status: ok}. GET /health returns 200. Emit events via lib.event_bus. Run as:   
python git_summarizer.py --port 7001 --repos-dir /THE_VAULT/gitea/repos.

# MVP 10 — NixOS Config Validator Agent

Depends on: MVP 1 → MVP 7, MVP 9

Integrates with the Git Monitor. When a change to the NixOSenv repository is detected, it runs `nix flake check`. If it fails, feeds the error output to Ollama for diagnosis, generates a suggested fix, and writes a review file.

<table><tr><td rowspan=1 colspan=1>Language</td><td rowspan=1 colspan=1>Python 3.12</td></tr><tr><td rowspan=1 colspan=1>Output</td><td rowspan=1 colspan=1>/THE_VAULT/jarvis/lib/nix_validator.py</td></tr><tr><td rowspan=1 colspan=1>Trigger</td><td rowspan=1 colspan=1>Called by git_monitor OR CLI: python nix_validator.py <file></td></tr><tr><td rowspan=1 colspan=1>Validate</td><td rowspan=1 colspan=1>subprocess(['nix', 'flake', 'check', '--no-build'], timeout=120)</td></tr><tr><td rowspan=1 colspan=1>On fail</td><td rowspan=1 colspan=1>Expert prompt → diagnosis → review file</td></tr><tr><td rowspan=1 colspan=1>Output</td><td rowspan=1 colspan=1>/THE_VAULT/jarvis/review/nixos_report.md</td></tr></table>

$\spadesuit$ UPDATED: local-ai.nix: DELETE this file. Your hardware (i7-1165G7, Intel Iris Xe) has no NVIDIA GPU — CUDA is inoperative. The Jarvis Ollama stack fully replaces it.

# Review File Format

# NixOS Config Validation Failure — 2026-03-04 15:00 ## Error Output error: undefined variable 'cudaPackages' at /home/qwerty/NixOSenv/modules/local-ai.nix:88:5 ## AI Diagnosis The attribute 'cudaPackages' is not in scope at line 88. In NixOS 26.05, CUDA packages are accessed via 'pkgs.cudaPackages' not 'cudaPackages' directly. (Note: if local-ai.nix has been deleted as recommended, this error will not occur.)

## Suggested Fix

\`\`\`nix

# Remove local-ai.nix from configuration.nix imports entirely.   
# The Jarvis Ollama stack replaces all functionality it provided.

# Acceptance Criteria

✓ On a clean NixOSenv repo (without local-ai.nix), nix flake check passes and script exits 0 ✓ On an introduced error (undefined variable), the script generates a review file with the error quoted ✓ AI diagnosis correctly identifies the error type in at least 3 out of 5 common NixOS error types ✓ --auto-fix mode invokes agent_loop.py and writes result to a separate auto_fix/ directory ✓ Review files are never overwritten — each run creates a new timestamped file

# AGENT PROMPT — paste into Claude Code / Continue.dev

Implement /THE_VAULT/jarvis/pipelines/nixos_validator.py. CLI: --repo PATH [--auto-fix]. Run subprocess(['nix', 'flake', 'check', '--no-build'], cwd=repo_path, capture_output $=$ True, timeout $= \pm 2 0$ ). If returncode ${ \bf \omega } = = 0$ : emit validate completed event, print 'Validation passed', exit 0. If returncode! ${ } = 0$ : call ollama_client.chat() with route('diagnose', thinking=True) and system $= ^ { \prime }$ You are a NixOS expert. Diagnose this nix flake check error and suggest a minimal fix. Be specific about file and line numbers.' Write /THE_VAULT/jarvis/review/nixos_<ISO_timestamp>.md with error output in a code block, ## AI Diagnosis section, ## Suggested Fix section extracting any \`\`\`nix blocks. Emit validate failed event. If --auto-fix: call agent_loop.py subprocess. Because of MVP 7's safety prompt, this will require interactive approval before modifying Nix files. Print 'Review written to: <path>' and exit 1.

# MVP 12 — Neovim IDE $\pmb { + }$ Coding Agent

Depends on: MVP $1  M V P 2  M V P 7  M V P 8$

A complete IDE inside Neovim. Language servers declared in home.nix (not mason.nvim — mason downloads runtime binaries incompatible with the Nix store). The coding agent HTTP server provides FIM autocomplete, BM25+vector hybrid RAG chat, looped fix via MVP 7, and explicit web research via MVP 8. DAP debugging via lldb (Rust/C) and debugpy (Python).

# Why Not mason.nvim on NixOS

mason.nvim downloads pre-compiled ELF binaries at runtime into \~/.local/share/mason/. These reference /lib/ld-linux.so — a path that does not exist on NixOS. They do not survive garbage collection.

home-manager puts every tool in the Nix store and symlinks it to \~/.nix-profile/bin/. nvim-lspconfig finds them on PATH automatically.

<table><tr><td rowspan=1 colspan=1>Server</td><td rowspan=1 colspan=1>coding_agent.py —http.server (stdlib) on localhost:7002</td></tr><tr><td rowspan=1 colspan=1>LSP install</td><td rowspan=1 colspan=1>home-manager home.packages — tools on PATH, nvim-lspconfig finds them</td></tr><tr><td rowspan=1 colspan=1>Autocomplete</td><td rowspan=1 colspan=1>blink.cmp: source 1 LSP · source 2 /complete FIM (Qwen3-1.7B, debounce 800ms — raised from 300ms to prevent stale request queuing on CPU)</td></tr><tr><td rowspan=1 colspan=1>RAG</td><td rowspan=1 colspan=1>BM25 + vector hybrid (code_rag.py): score = 0.7×vector + 0.3×BM25</td></tr><tr><td rowspan=1 colspan=1>Research</td><td rowspan=1 colspan=1>Cascade: local RAG (score&gt;0.65) → docs index → MVP 8 SearXNG web search</td></tr><tr><td rowspan=1 colspan=1>Fix loop</td><td rowspan=1 colspan=1>MVP 7 agent_loop.py with route(fix&#x27;, thinking=True) and language validator</td></tr><tr><td rowspan=1 colspan=1>Memory</td><td rowspan=1 colspan=1>Four-tier: working (session) · episodic (events.db) · semantic (SQLite) · procedural(prompts/)</td></tr><tr><td rowspan=1 colspan=1>DAP</td><td rowspan=1 colspan=1>nvim-dap: ldb for Rust/C · debugpy for Python · F5/F10/F11/b</td></tr><tr><td rowspan=1 colspan=1>Elite Features</td><td rowspan=1 colspan=1>Togglable Suggestions · Agentic Refactoring · Diagnostic Lens · Project Awareness</td></tr></table>

UPDATED: FIM uses Qwen3-1.7B. /complete endpoint MUST pass suffix $: =$ parameter to Ollama /api/generate — failure to do so degrades FIM to regular completion. See code below.

# FIM Suffix Parameter — Critical Fix

# coding_agent.py — /complete endpoint (CORRECT implementation)   
def handle_complete(self, data): prefix $=$ data.get('prefix', '') suffix $=$ data.get('suffix', '') # text AFTER the cursor model $=$ route('complete') # qwen3:1.7b-q4_K_M # MUST pass suffix $\displaystyle . =$ to generate() — Ollama uses <|fim_suffix|> tokens result $=$ generate( model $=$ model, prompt $=$ prefix, suffix $. =$ suffix, # $\gets$ THIS IS REQUIRED FOR FIM stream $_ { 1 } =$ False ) return {'completion': result}

# If suffix is omitted, the model performs regular completion, not FIM. # Your acceptance criteria (LSP $^ +$ FIM in insert mode within 3s) will # catch this bug immediately — output will be inserted AT cursor, # not intelligently spliced into surrounding code.

# BM25 $^ +$ Vector Hybrid Search (code_rag.py)

# pip install rank-bm25 (add to .venv requirements) from rank_bm25 import BM25Okapi

def retrieve_hybrid(query, db_path, top_k $^ { \circ 3 }$ , alpha $= 0 . 7$ ): $\dots 1 0 . 7 ^ { \star }$ vector_score $^ +$ 0.3\*BM25_score — covers semantic and exact lookups. Use for all /chat requests. retrieve() kept for backward compatibility.''' vec $=$ retrieve(query, db_path, top_k $. =$ top_k $^ { \star 2 }$ ) all_chunks $=$ load_all_chunks(db_path) bm25 $=$ BM25Okapi([c['text'].lower().split() for c in all_chunks]) bm25_scores $=$ bm25.get_scores(query.lower().split()) # Normalise both score ranges to [0,1], merge by chunk id, sort, take top_k return merged[:top_k]

# home.nix — All Dev Tools (home-manager)

home.packages $=$ with pkgs; [ # LSP servers — installed via home-manager, NOT mason.nvim rust-analyzer pyright nil clang-tools gopls nodePackages.typescript-language-server lua-language-server nodePackages.bash-language-server taplo yaml-language-server # Formatters rustfmt black ruff alejandra stylua shfmt # Debug adapters lldb python313Packages.debugpy   
];   
# Verify: which rust-analyzer # must return /nix/store/... path

# Elite Neovim Features (The "Antigravity" Layer)

To compensate for the i7-1165G7 hardware, JARVIS implements high-level reasoning loops that outperform raw inference speed.

### 1. Togglable Suggestions
Syncs the `blink.cmp` state with the `coding_agent.py` backend.
- `:JarvisToggleSuggestions`: Toggles the background FIM completion. When OFF, the 1.7B model stops polling, saving 1.2GB of RAM and CPU cycles for heavy synthesis.

### 2. Agentic Refactoring
A multi-file reasoning loop triggered by `:JarvisRefactor`.
- Takes a description (e.g., "Extract event_bus into a separate package").
- **Loop:** Analyze `git ls-tree` → Search symbols → Draft plan → Edit files → Run `make test` → Fix errors.
- Uses `route('reason', thinking=True)` for architectural integrity.

### 3. Diagnostic Lens (Smart Gutter)
Virtual text annotations next to compiler errors.
- Hovering or dwelling on an error triggers a 100-word explanation of *why* it failed and a suggested fix based on your local `prompts/best.txt`.

### 4. Project Awareness
Every request to the coding agent is prefixed with a "Global Context" block:
- Current File Structure (`tree -L 2`).
- Recently edited files (last 5 entries in `events.db`).
- Active LSP symbols in the current buffer.

# Acceptance Criteria

✓ LSP: gd, gr, K, rn, f all work in a Rust file with Ollama stopped   
✓ FIM completions appear in insert mode within 3s — suffix parameter confirmed in /complete   
✓ retrieve_hybrid('OllamaError', db) returns the exact definition chunk in top-1   
✓ retrieve_hybrid('async error handling', db) returns semantically relevant chunks   
✓ /chat system prompt includes user_context.md $^ +$ today's episodic summary $^ +$ RAG chunks   
✓ /fix with a cargo check error produces a passing fix via agent_loop.py   
✓ F5 starts a Rust debug session via lldb; b toggles breakpoint   
✓ POST /index on 5000-line repo completes in $< 3$ min (chunks_indexed $> 3 0$ )   
✓ Plugin loads with require('jarvis').setup() without error when server stopped

# AGENT PROMPT — paste into Claude Code / Continue.dev

Implement MVP 12. (1) code_rag.py: existing retrieve() plus retrieve_hybrid(query, db_path,top_k,alpha $\varpi \cdot 7$ ) using rank_bm25.BM25Okapi, normalised scores combined as alpha\*vec+(1-alpha)\*bm25. (2) coding_agent.py HTTP server :7002. /complete: FIM via generate(route('complete'), prefix, suffix $: =$ suffix_text) — suffix parameter is REQUIRED for proper FIM behaviour. /chat: build_system_prompt() reading user_context.md, querying events.db for today's events, calling retrieve_hybrid, reading preference.py style context, calling chat_managed(route('chat'), messages). Confidence cascade: if top hybrid score $<$ 0.65 try AnythingLLM workspace, if empty call research_agent.py subprocess. /fix: agent_loop.py subprocess with route('fix', thinking=True), return unified diff. /explain: route('chat') no RAG. /index: code_indexer. /health: Ollama check $^ +$ DB row count. (3) lua/jarvis/: lsp.lua wires nvim-lspconfig servers via on_attach — NO mason. complete.lua: blink.cmp LSP+jarvis sources. agent.lua: jc/jf/je/ji/jr/js. dap.lua: lldb adapter for Rust, debugpy for Python, F5/F10/F11/b/dr. All gracefully degrade when server unreachable.

CRITICAL — ASYNC NEOVIM PLUGIN (i7-1165G7 constraint): CPU inference at 3-5 tok/s means a /fix or /chat call can take 30-90 seconds. ALL HTTP calls from Lua to `coding_agent.py` MUST be asynchronous using `plenary.curl` with a callback — NEVER use synchronous `vim.fn.system()` or blocking `curl`. Show a spinner via `vim.notify('Jarvis thinking...')` while in-flight. Use `vim.schedule()` to update buffers from the async callback.

# MVP 13 — Infrastructure Layer

Depends on: MVP $1  B i g$ MVP

Four components that make the system observable and self-reporting. The event bus is the foundation — every other component reads from it. None require Ollama to be running to function (health_monitor and digest use it opportunistically but fall back if it is offline).

<table><tr><td rowspan=1 colspan=1>event_bus</td><td rowspan=1 colspan=1>lib/event_bus.py— SQLite events.db — 3 lines to add to any MVP</td></tr><tr><td rowspan=1 colspan=1>model_router</td><td rowspan=1 colspan=1>lib/model_router.py — single source of truth for model selection</td></tr><tr><td rowspan=1 colspan=1>health_mon</td><td rowspan=1 colspan=1>services/health_monitor.py — poll all services every 30s → metrics.db</td></tr><tr><td rowspan=1 colspan=1>daily_digest</td><td rowspan=1 colspan=1>services/daily_digest.py — 06:00 cron via systemd timer → events.db → Ollama → notify</td></tr><tr><td rowspan=1 colspan=1>weekly_report</td><td rowspan=1 colspan=1>services/weekly_report.py — Sunday 23:00 via systemd timer → week summary</td></tr><tr><td rowspan=1 colspan=1>Outputs</td><td rowspan=1 colspan=1>logs/events.db · logs/metrics.db · logs/daily_digest.md · logs/weekly_report.md</td></tr></table>

# event_bus.py

import sqlite3, json   
from datetime import datetime, timezone   
DB $=$ '/THE_VAULT/jarvis/logs/events.db'   
def emit(source: str, event: str, details: dict $=$ None, level $= "$ INFO'): # 3 lines to add to any MVP: # from lib.event_bus import emit # emit('ingest', 'completed', {'file': 'paper.pdf', 'chunks': 42}) con $=$ sqlite3.connect(DB) con.execute('INSERT INTO events (ts,source,event,details,level) VALUES (?,?,?,?,?)', (datetime.now(timezone.utc).isoformat(), source, event, json.dumps(details or {}), level)) con.commit(); con.close()   
def query_today() $- >$ list[dict]: con $=$ sqlite3.connect(DB) rows $=$ con.execute( "SELECT source,event,details FROM events WHERE ts $>$ date('now')").fetchall() con.close() return [{'source':r[0],'event':r[1],'details':json.loads $( x [ 2 ] )$ } for r in rows]

# model_router.py

<table><tr><td colspan="4">def route(task: str, context_chars: int = 0, thinking: bool = False) -&gt; str: rules = {</td></tr><tr><td></td><td>&#x27;embed&#x27;: &#x27;embed&#x27;,</td><td></td><td># nomic-embed-text always</td></tr><tr><td></td><td>&#x27;complete&#x27;:&#x27;complete&#x27;,</td><td></td><td># qwen3:1.7b-q4_K_M - FIM, speed critical</td></tr><tr><td></td><td>&#x27;classify&#x27;:&#x27;fast&#x27;,</td><td></td><td># intent detection (mistral:7b)</td></tr><tr><td>&#x27;clean&#x27;:</td><td>&#x27;fast&#x27;,</td><td></td><td># document cleaning (mistral:7b)</td></tr><tr><td></td><td>&#x27;summarize&#x27;:&#x27;fast&#x27;,</td><td></td><td># summaries, digest (mistral:7b)</td></tr><tr><td>&#x27;score&#x27;:</td><td>&#x27;fast&#x27;,</td><td></td><td># prompt scoring (mistral:7b)</td></tr><tr><td>&#x27;chat&#x27;</td><td>&#x27;chat&#x27;,</td><td></td><td># RAG chat (qwen3:14b)</td></tr><tr><td>&#x27;fix&#x27;:</td><td>&#x27;chat&#x27;,</td><td></td><td># agent loop (qwen3:14b)</td></tr><tr><td></td><td>&#x27;diagnose&#x27;:&#x27;chat&#x27;,</td><td></td><td># Nixos validator (qwen3:14b)</td></tr><tr><td></td><td>&#x27;reason&#x27;: &#x27;chat&#x27;,</td><td></td><td># multi-step tasks (qwen3:14b)</td></tr><tr><td>}</td><td></td><td></td><td></td></tr><tr><td></td><td># Safety: large context → downgrade non-critical tasks</td><td></td><td></td></tr><tr><td></td><td></td><td></td><td>if context_chars &gt; 5000 and task not in (&#x27;fix&#x27;,&#x27;diagnose&#x27;,&#x27;reason&#x27;):</td></tr><tr><td></td><td>return &#x27;fast&#x27; alias = rules.get(task, &#x27;chat&#x27;)</td><td></td><td></td></tr><tr><td></td><td></td><td></td><td></td></tr><tr><td></td><td></td><td></td><td># Qwen3 thinking mode: prepend /think or /no_think to first user message</td></tr><tr><td>return alias</td><td></td><td></td><td># (handled by caller - route() returns alias only, thinking flag is advisory)</td></tr></table>

# Acceptance Criteria

✓ emit('ingest', 'completed', {'file':'x.pdf'}) writes a row to events.db within 100ms ✓ route('fix') returns 'chat'; route('summarize') returns 'fast'; route('embed') returns 'embed' ✓ health_monitor polls all 6 services every 30s and writes rows to metrics.db $\checkmark$ jarvis status reads metrics.db (not live HTTP pings) and shows recent latency ✓ jarvis status --short outputs a single line $\scriptstyle < = 4 0$ chars suitable for Waybar ✓ daily_digest.py produces a $\scriptstyle < = 2 0 0$ -word summary in logs/daily_digest.md ✓ All 12 existing MVPs emit at least one event per operation after being retrofitted

# AGENT PROMPT — paste into Claude Code / Continue.dev

Implement MVP 13 as four files. (1) lib/event_bus.py: SQLite events.db with emit(source, event, details, level) and query_today(). (2) lib/model_router.py: route(task, context_chars, thinking=False) as specified — thinking flag is advisory, returned alias is used by caller. (3) services/health_monitor.py: loop every 30s, requests.get each service URL with 2s timeout, write (ts, service, 'ok'|'down', latency_ms) to metrics.db. Add --short flag: query metrics WHERE ts $>$ datetime('now','-2 minutes'), format as 'N/6 | inbox:M | review:K'. (4) services/daily_digest.py: query events.db for yesterday, format as bullet list, call chat(route('summarize'), ...) to summarise in $< = ~ \pm 5 0$ words, append to logs/daily_digest.md, call notify-send. (5) services/weekly_report.py: same for 7 days, include feedback.jsonl stats. Retrofit emit() into all MVPs.

# MVP 14 — Jarvis TUI Dashboard

Depends on: MVP 13

A full-screen terminal dashboard in Rust via Ratatui. Lives in one tmux pane while Neovim fills the other. This is your Phase 7 Rust project: it forces tokio async, mpsc channels, structs, traits, and real I/O.

<table><tr><td rowspan=1 colspan=1>Language</td><td rowspan=1 colspan=1>Rust (edition 2021)</td></tr><tr><td rowspan=1 colspan=1>Crates</td><td rowspan=1 colspan=1>ratatui 0.30+ · tokio · rusqlite · reqwest · crossterm 0.29</td></tr><tr><td rowspan=1 colspan=1>Binary</td><td rowspan=1 colspan=1>/THE_VAULTjarvis/binjarvis-monitor (cargo build --release)</td></tr><tr><td rowspan=1 colspan=1>Data</td><td rowspan=1 colspan=1>Reads from metrics.db (health) and events.db (activity) — no HTTP polling</td></tr><tr><td rowspan=1 colspan=1>Refresh</td><td rowspan=1 colspan=1>500ms tick via tokio::time:interval — events streamed via mpsc channel</td></tr><tr><td rowspan=1 colspan=1>Layout</td><td rowspan=1 colspan=1>Four panes: services · active task/progress · recent events · RAG activity</td></tr></table>

UPDATED: Ratatui upgraded from 0.29 to $\pmb { 0 . 3 0 + }$ . Use crossterm 0.29. TEA architecture recommended. 0.30 fixes flicker and improves StatefulWidget ergonomics.

# Cargo.toml Dependencies

[dependencies]   
ratatui $\mathbf { \Sigma } = \mathbf { \Sigma } " 0 . 3 0 \mathbf { \Sigma } ^ { \mathrm {  n } }$ # upgraded from 0.29 — flicker fixes, better StatefulWidget   
crossterm $\mathbf { \Sigma } = \mathbf { \Sigma } " 0 . 2 9 \mathbf { \Sigma } ^ { \mathrm { ~ } \mathrm { ~ } }$   
tokio $=$ { version $=$ "1", features $=$ ["full"] }   
rusqlite $=$ { version $=$ "0.32", features $=$ ["bundled"] }   
reqwest $= \begin{array} { r c l } { \{ }  \end{array}$ version $=$ "0.12", features $=$ ["json"] }

# Rust Architecture

// src/main.rs structure mod app; // App state struct — services, events, metrics mod ui; // Ratatui widget rendering — four-pane layout mod data; // rusqlite queries for events.db and metrics.db mod events; // crossterm key event handling (q, j, k, r, e)

// tokio runtime — two tasks: // task 1: data poller ( $5 0 0 \mathrm { m s }$ ) reads DB sends App update via mpsc::Sender // task 2: render loop receives update ratatui terminal.draw()

struct ServiceStatus { name: String, up: bool, latency_ms: u64, history: Vec<u64> } struct Event ts: String, source: String, event: String, details: String struct App { services: Vec<ServiceStatus>, events: Vec<Event>, scroll_offset: usize, active_task: Option<String> }

# Acceptance Criteria

✓ cargo build --release produces a binary that starts and renders the four-pane layout ✓ Services pane refreshes every 500ms from metrics.db — not from live HTTP pings ✓ Events pane scrolls with $\mathrm { j } / \kappa ;$ most recent event always visible at top ✓ Ollama latency sparkline shows last 20 samples as unicode block-character graph ✓ Pressing 'e' on an escalated event opens the review file in \$EDITOR (nvim) ✓ RAM and disk usage shown as percentage bars updated each tick ✓ Dashboard starts in under ${ 2 0 0 } \mathsf { m s }$ ; no visible flicker during refresh ✓ Runs correctly in Alacritty $^ +$ tmux on Hyprland

# AGENT PROMPT — paste into Claude Code / Continue.dev

Implement MVP 14: Rust binary using ratatui 0.30 $^ +$ tokio $^ +$ rusqlite $^ +$ crossterm 0.29. cargo new jarvis-monitor in /THE_VAULT/jarvis/. App struct: services (Vec with name/up/latency_ms/history Vec), events (Vec from events.db, newest first), rag_activity (Vec with query/score/used_web), scroll_offset. Tokio runtime with two tasks: data task polls metrics.db and events.db every 500ms via rusqlite, sends AppUpdate via mpsc channel; render task receives update, calls terminal.draw() with ratatui layout. Layout: top-left pane services (Table: name, up/down, latency, sparkline via unicode block chars); top-right active task (Gauge for indexing progress $^ +$ last 5 events as List); bottom-left RAM/disk Gauge widgets; bottom-right RAG Activity table. Key handler: $\mathbf { q } =$ quit, j/k $. =$ scroll events, $\mathbf { \nabla } \mathbf { r } =$ force refresh, $\ e =$ open escalation via std::process::Command nvim. Binary symlinked to /usr/local/bin/jarvis-monitor.

# MVP BIG — jarvis — The Unified CLI

# Depends on: All 10 MVPs

The top-level CLI that unifies all MVPs into a single natural-language interface. You type a command in plain English and jarvis routes it to the right pipeline. Also includes continuous mode: watches your machine and triggers pipelines automatically.

<table><tr><td rowspan=1 colspan=1>Language</td><td rowspan=1 colspan=1>Python 3.12</td></tr><tr><td rowspan=1 colspan=1>Output</td><td rowspan=1 colspan=1>/THE_VAULT/jarvis/jarvis.py + symlink: /usr/local/bin/jarvis</td></tr><tr><td rowspan=1 colspan=1>Interface</td><td rowspan=1 colspan=1>Natural language CLI: jarvis &#x27;clean this pdf for notebookIm&#x27;</td></tr><tr><td rowspan=1 colspan=1>Routing</td><td rowspan=1 colspan=1>Intent classifier: call Ollama with intent detection prompt → map to pipeline</td></tr><tr><td rowspan=1 colspan=1>Services</td><td rowspan=1 colspan=1> jarvis start — starts all background services (ingest daemon, webhook server)</td></tr><tr><td rowspan=1 colspan=1>Status</td><td rowspan=1 colspan=1> jarvis status — shows health of all components (reads metrics.db)</td></tr><tr><td rowspan=1 colspan=1>History</td><td rowspan=1 colspan=1>Allcommands and results logged to /THE_VAULT/jarvis/logs/history.jsonl</td></tr><tr><td rowspan=1 colspan=1>Feedback</td><td rowspan=1 colspan=1> jarvis thumbs-up /jarvis thumbs-down → appends to feedback.jsonl</td></tr></table>

# Command Routing Table

<table><tr><td rowspan=1 colspan=1> Natural Language Input</td><td rowspan=1 colspan=1>Intent</td><td rowspan=1 colspan=1>Pipeline Called</td></tr><tr><td rowspan=1 colspan=1>clean this pdf for notebooklm</td><td rowspan=1 colspan=1>clean_document</td><td rowspan=1 colspan=1>MVP 3: cleaner.py</td></tr><tr><td rowspan=1 colspan=1>research transformer attentionmechanisms</td><td rowspan=1 colspan=1>research</td><td rowspan=1 colspan=1>MVP 8: research_agent.py</td></tr><tr><td rowspan=1 colspan=1>add this file to my knowledge base</td><td rowspan=1 colspan=1>ingest</td><td rowspan=1 colspan=1>MVP 5: ingest.py --once</td></tr><tr><td rowspan=1 colspan=1>write a nix module for</td><td rowspan=1 colspan=1>generate_nix</td><td rowspan=1 colspan=1>MVP 7: agent_loop.py</td></tr><tr><td rowspan=1 colspan=1>optimize the notebooklm prompt</td><td rowspan=1 colspan=1>optimize_prompt</td><td rowspan=1 colspan=1>MVP 6: optimizer.py</td></tr><tr><td rowspan=1 colspan=1>validate my nixos config</td><td rowspan=1 colspan=1>validate_nixos</td><td rowspan=1 colspan=1>MVP 10: nixos_validator.py</td></tr><tr><td rowspan=1 colspan=1>what happened today</td><td rowspan=1 colspan=1>query_events</td><td rowspan=1 colspan=1>MVP 13: query events.db → summarise</td></tr><tr><td rowspan=1 colspan=1>open dashboard</td><td rowspan=1 colspan=1>open_dashboard</td><td rowspan=1 colspan=1>subprocess jarvis-monitor (MVP 14)</td></tr><tr><td rowspan=1 colspan=1>start all services</td><td rowspan=1 colspan=1>start_services</td><td rowspan=1 colspan=1>MVP 5 daemon + MVP 9 + MVP 13</td></tr><tr><td rowspan=1 colspan=1>status</td><td rowspan=1 colspan=1>health_check</td><td rowspan=1 colspan=1>Read metrics.db — allservices</td></tr></table>

# Acceptance Criteria

✓ jarvis 'clean /THE_VAULT/inbox/test.pdf' runs MVP 3 and prints the output path   
✓ jarvis 'research local LLM inference optimization' runs MVP 8 and reports files created   
$\checkmark$ jarvis status shows correct running/stopped state for each service (reads metrics.db)   
$\checkmark$ jarvis start launches all services as background processes, prints their PIDs   
$\checkmark$ jarvis thumbs-up / jarvis thumbs-down appends to feedback.jsonl with last command context   
✓ An unrecognized command returns 3 suggestions from Ollama   
✓ jarvis help lists all available intents with one-line descriptions and example commands   
✓ All commands logged to history.jsonl with timestamp, parsed intent, args, and status   
$\checkmark$ jarvis --version prints the version from jarvis.toml

# AGENT PROMPT — paste into Claude Code / Continue.dev

Implement /THE_VAULT/jarvis/jarvis.py. Takes a natural language command as its first argument (or reads from stdin). Use chat(route('classify'), ...) with the intent detection prompt to classify into one of: clean_document, research, ingest, generate_nix, optimize_prompt, validate_nixos, git_summary, query_knowledge, query_events, open_dashboard, start_services, health_check, unknown. Parse JSON response to get intent and args. Route to the correct pipeline by importing or subprocess. 'jarvis status' reads metrics.db WHERE ts $>$ datetime('now','-5 minutes') and formats a status table. 'jarvis start' launches ingest.py, git_summarizer.py, health_monitor.py, coding_agent.py as background subprocess.Popen, saving PIDs to logs/pids.json. 'jarvis thumbs-up/down' appends last history.jsonl entry $^ +$ rating to feedback.jsonl. 'open dashboard' subprocess jarvis-monitor. Log every command to history.jsonl. For unknown intent, call Ollama to suggest 3 similar commands. Install symlink: ln -sf /THE_VAULT/jarvis/jarvis.py /usr/local/bin/jarvis.

CRITICAL — SYSTEMD-NATIVE LIFECYCLE (i7-1165G7 constraint): Do NOT use subprocess.Popen to start background services — orphaned processes eat RAM and are invisible to the user. Implement `jarvis start` and `jarvis stop` by calling `subprocess.run(['systemctl', '--user', 'start', 'jarvis-ingest.service'])` etc. for each service. Implement `jarvis status` by running `systemctl --user is-active <service>` for each service — no pids.json needed. The systemd unit definitions live in modules/jarvis.nix. `jarvis start` is a thin frontend to `systemctl --user`.


# MVP 15 — user_context.md Auto-Updater

Depends on: MVP 1 → MVP 13

Keeps the `user_context.md` file (injected into every /chat system prompt as "who you are") fresh automatically. Runs weekly via systemd timer, queries `events.db` for the past 7 days of activity, asks Qwen3-14B to synthesize a short "what has qwerty been working on" paragraph, and appends a dated entry. Without this, user_context.md goes stale and the AI stops knowing what you're actually doing.

| | |
|---|---|
| Language | Python 3.12 |
| Output | /THE_VAULT/jarvis/services/context_updater.py |
| Source | events.db — last 7 days of emit() records |
| Destination | /THE_VAULT/jarvis/config/user_context.md — append, never overwrite |
| Model | route('summarize') — mistral:7b, keep_alive=0 |
| Schedule | Sunday 22:00 via systemd timer (before weekly report at 23:00) |
| Format | Appended block: `## Week of YYYY-MM-DD\n<summary paragraph>` |

# Acceptance Criteria

✓ Running context_updater.py with no events in the last 7 days produces no output and exits 0
✓ After 7 days of activity, appends a 50-150 word summary paragraph to user_context.md
✓ Never truncates or overwrites existing user_context.md content — only appends
✓ Appended block is correctly formatted Markdown with the dated heading
✓ Emits a 'context_updated' event via lib.event_bus on success

# AGENT PROMPT — paste into Claude Code / Continue.dev

Implement /THE_VAULT/jarvis/services/context_updater.py. Query events.db for all rows where ts > datetime('now', '-7 days'). Format them as a bullet list: "- [source] event: details". Call ollama_client.chat() with route('summarize', keep_alive=0) and system prompt: 'You are summarizing a developer\'s week from their system activity log. Write a single paragraph (50-150 words) describing what they worked on and accomplished. Be specific about tools and projects. Write in third person: \"This week, qwerty...\"'. Append result to /THE_VAULT/jarvis/config/user_context.md under a heading `## Week of <ISO_date>`. Emit event via lib.event_bus. Exit 0 on success, 1 on failure.

# MVP 16 — Makefile Test Harness (Build MVP 0)

Depends on: All MVPs

The glue that validates the entire system. Should be built first (it defines "done" for every MVP) but specified last since it tests all of them. Without this, you have no way to verify a change to MVP 1 didn't silently break MVP 5. Each MVP has its own test target. `make test` runs all of them. `make status` shows which services are running.

| | |
|---|---|
| Output | /THE_VAULT/jarvis/Makefile |
| Language | GNU Make + shell commands |
| Test runner | Calls each MVP's `__main__` block or a dedicated test_*.py script |
| CI gate | `make test` must pass before any PR to the Jarvis repo |

# Makefile Design

```makefile
.PHONY: setup test test-all status lint clean

VENV = /THE_VAULT/jarvis/.venv
PY = $(VENV)/bin/python

setup:
	python -m venv $(VENV)
	$(VENV)/bin/pip install requests numpy watchdog aiohttp rank-bm25 filelock
	pip install 'mineru[pipeline]'

test-mvp1:
	$(PY) lib/ollama_client.py          # calls __main__ block

test-mvp2:
	$(PY) tools/chunker.py test_data/sample.md --by-heading

test-mvp3:
	$(PY) tools/cleaner.py test_data/sample.md

test-mvp5:
	$(PY) pipelines/ingest.py --once test_data/sample.md

test-mvp7:
	$(PY) pipelines/agent_loop.py --task python_sum --user-prompt "sum a list" --output /tmp/out.py

test-mvp8:
	$(PY) pipelines/research_agent.py --query "nixos flakes" --sources 2

test-mvp9:
	curl -s http://localhost:7001/health | grep ok

test-mvp12:
	curl -s http://localhost:7002/health | grep ok

test-mvp13:
	$(PY) -c "from lib.event_bus import emit; emit('test','ok',{}); print('event_bus OK')"
	$(PY) -c "from lib.model_router import route; assert route('fix')=='chat'; print('model_router OK')"

test-all: test-mvp1 test-mvp2 test-mvp3 test-mvp5 test-mvp7 test-mvp8 test-mvp9 test-mvp12 test-mvp13
	@echo "All MVP tests passed"

status:
	@systemctl --user is-active jarvis-ingest || echo "ingest: stopped"
	@systemctl --user is-active jarvis-coding-agent || echo "coding-agent: stopped"
	@systemctl --user is-active jarvis-health-monitor || echo "health-monitor: stopped"
	@systemctl --user is-active jarvis-git-summarizer || echo "git-summarizer: stopped"

lint:
	$(VENV)/bin/python -m py_compile lib/ollama_client.py lib/event_bus.py lib/model_router.py
	@echo "Lint passed"

clean:
	find /THE_VAULT/jarvis/logs/ -name "*.lock" -delete
	find /THE_VAULT/jarvis/inbox/ -name "*.tmp" -delete
```

# Acceptance Criteria

✓ `make setup` creates .venv and installs all required packages
✓ `make test-mvp1` passes when Ollama is running
✓ `make test-all` passes when all services are healthy; exits non-zero if any test fails
✓ `make status` outputs one line per service showing running/stopped
✓ `make lint` exits 0 when all library files are syntactically valid Python

# AGENT PROMPT — paste into Claude Code / Continue.dev

Implement /THE_VAULT/jarvis/Makefile exactly as specified in the Makefile Design section above. Add a `test_data/` directory with: `sample.md` (a 500-word Markdown file with ## headings), `sample.pdf` (any small PDF). Each test target should exit non-zero on failure. `make test-all` depends on all individual targets. `make status` uses `systemctl --user is-active` for each service name. Do NOT add any external test framework — pure Make + Python __main__ blocks + curl.

# MVP 17 — Secrets & Environment Manager

Depends on: MVP 1

A tiny validation layer run at startup by every service and pipeline. Checks that all required environment variables are present, gives a clear human-readable error if any are missing (instead of a cryptic `KeyError` 30 seconds into a processing run), and optionally loads from a `.env` file for development. This is especially important when services are launched by systemd — env injection into systemd user units is non-obvious and errors surface as silent failures.

| | |
|---|---|
| Language | Python 3.12 |
| Output | /THE_VAULT/jarvis/lib/env_manager.py |
| Used by | Every MVP at startup (3-line import) |
| Dev fallback | Loads /THE_VAULT/jarvis/config/.env if env vars not already set |
| Validation | Checks all required vars, prints table of missing ones, exits 1 |

# Public Interface

```python
# lib/env_manager.py
REQUIRED_VARS = {
    'OLLAMA_BASE_URL':       ('http://localhost:11434', 'Ollama REST API endpoint'),
    'ANYTHINGLLM_BASE_URL':  ('http://localhost:3001',  'AnythingLLM REST API endpoint'),
    'ANYTHINGLLM_API_KEY':   (None,                     'AnythingLLM authentication key'),
    'GITEA_WEBHOOK_SECRET':  (None,                     'HMAC secret for Gitea webhooks'),
}

def load(required: list[str] = None) -> dict:
    # 1. Load /THE_VAULT/jarvis/config/.env if it exists (KEY=VALUE format, # comments)
    # 2. Check each required var (or all REQUIRED_VARS if required=None)
    # 3. Use default if provided, else raise with helpful message
    # 4. Return dict of all resolved values
    ...

def validate_or_exit(required: list[str] = None):
    # Calls load(), prints a missing-vars table, exits 1 if any are missing
    # Call this at the top of every service's main() block
    ...
```

# Usage in Every MVP (3 lines)

```python
from lib.env_manager import validate_or_exit
validate_or_exit(['OLLAMA_BASE_URL', 'ANYTHINGLLM_API_KEY'])
# proceeds only if all listed vars are set
```

# .env File (for development — NOT committed to git)

```bash
# /THE_VAULT/jarvis/config/.env
OLLAMA_BASE_URL=http://localhost:11434
ANYTHINGLLM_BASE_URL=http://localhost:3001
ANYTHINGLLM_API_KEY=your-key-here
GITEA_WEBHOOK_SECRET=your-secret-here
```

# Acceptance Criteria

✓ `validate_or_exit(['ANYTHINGLLM_API_KEY'])` exits 0 when the var is set
✓ `validate_or_exit(['ANYTHINGLLM_API_KEY'])` prints a clear error and exits 1 when the var is missing
✓ `load()` reads from .env file when environment variable is not already set
✓ Vars explicitly set in environment always take precedence over .env file
✓ `load()` returns defaults for vars with defaults defined; never exits for those
✓ The .env template is documented in config/env.example with all REQUIRED_VARS and descriptions

# AGENT PROMPT — paste into Claude Code / Continue.dev

Implement /THE_VAULT/jarvis/lib/env_manager.py. Define REQUIRED_VARS dict as shown. `load(required=None)`: read /THE_VAULT/jarvis/config/.env if it exists (parse KEY=VALUE lines, skip # comments, strip whitespace), set any missing os.environ keys from it (env takes priority), then resolve each requested var: use os.environ value if set, else default if defined, else add to missing list. `validate_or_exit(required=None)`: call load(), if any vars are missing print a table of NAME / DESCRIPTION / STATUS for all required vars and call sys.exit(1). Also write config/env.example listing all REQUIRED_VARS with their descriptions. No external dependencies.


# MVP 15 — user_context.md Auto-Updater

Depends on: MVP 1 → MVP 13

Keeps the `user_context.md` file (injected into every /chat system prompt as "who you are") fresh automatically. Runs weekly via systemd timer, queries `events.db` for the past 7 days of activity, asks Qwen3-14B to synthesize a short "what has qwerty been working on" paragraph, and appends a dated entry. Without this, user_context.md goes stale and the AI stops knowing what you're actually doing.

| | |
|---|---|
| Language | Python 3.12 |
| Output | /THE_VAULT/jarvis/services/context_updater.py |
| Source | events.db — last 7 days of emit() records |
| Destination | /THE_VAULT/jarvis/config/user_context.md — append, never overwrite |
| Model | route('summarize') — mistral:7b, keep_alive=0 |
| Schedule | Sunday 22:00 via systemd timer (before weekly report at 23:00) |
| Format | Appended block: `## Week of YYYY-MM-DD\n<summary paragraph>` |

# Acceptance Criteria

✓ Running context_updater.py with no events in the last 7 days produces no output and exits 0
✓ After 7 days of activity, appends a 50-150 word summary paragraph to user_context.md
✓ Never truncates or overwrites existing user_context.md content — only appends
✓ Appended block is correctly formatted Markdown with the dated heading
✓ Emits a 'context_updated' event via lib.event_bus on success

# AGENT PROMPT — paste into Claude Code / Continue.dev

Implement /THE_VAULT/jarvis/services/context_updater.py. Query events.db for all rows where ts > datetime('now', '-7 days'). Format them as a bullet list: "- [source] event: details". Call ollama_client.chat() with route('summarize', keep_alive=0) and system prompt: 'You are summarizing a developer\'s week from their system activity log. Write a single paragraph (50-150 words) describing what they worked on and accomplished. Be specific about tools and projects. Write in third person: \"This week, qwerty...\"'. Append result to /THE_VAULT/jarvis/config/user_context.md under a heading `## Week of <ISO_date>`. Emit event via lib.event_bus. Exit 0 on success, 1 on failure.

# MVP 16 — Makefile Test Harness (Build MVP 0)

Depends on: All MVPs

The glue that validates the entire system. Should be built first (it defines "done" for every MVP) but specified last since it tests all of them. Without this, you have no way to verify a change to MVP 1 didn't silently break MVP 5. Each MVP has its own test target. `make test` runs all of them. `make status` shows which services are running.

| | |
|---|---|
| Output | /THE_VAULT/jarvis/Makefile |
| Language | GNU Make + shell commands |
| Test runner | Calls each MVP's `__main__` block or a dedicated test_*.py script |
| CI gate | `make test` must pass before any PR to the Jarvis repo |

# Makefile Design

```makefile
.PHONY: setup test test-all status lint clean

VENV = /THE_VAULT/jarvis/.venv
PY = $(VENV)/bin/python

setup:
	python -m venv $(VENV)
	$(VENV)/bin/pip install requests numpy watchdog aiohttp rank-bm25 filelock
	pip install 'mineru[pipeline]'

test-mvp1:
	$(PY) lib/ollama_client.py          # calls __main__ block

test-mvp2:
	$(PY) tools/chunker.py test_data/sample.md --by-heading

test-mvp3:
	$(PY) tools/cleaner.py test_data/sample.md

test-mvp5:
	$(PY) pipelines/ingest.py --once test_data/sample.md

test-mvp7:
	$(PY) pipelines/agent_loop.py --task python_sum --user-prompt "sum a list" --output /tmp/out.py

test-mvp8:
	$(PY) pipelines/research_agent.py --query "nixos flakes" --sources 2

test-mvp9:
	curl -s http://localhost:7001/health | grep ok

test-mvp12:
	curl -s http://localhost:7002/health | grep ok

test-mvp13:
	$(PY) -c "from lib.event_bus import emit; emit('test','ok',{}); print('event_bus OK')"
	$(PY) -c "from lib.model_router import route; assert route('fix')=='chat'; print('model_router OK')"

test-all: test-mvp1 test-mvp2 test-mvp3 test-mvp5 test-mvp7 test-mvp8 test-mvp9 test-mvp12 test-mvp13
	@echo "All MVP tests passed"

status:
	@systemctl --user is-active jarvis-ingest || echo "ingest: stopped"
	@systemctl --user is-active jarvis-coding-agent || echo "coding-agent: stopped"
	@systemctl --user is-active jarvis-health-monitor || echo "health-monitor: stopped"
	@systemctl --user is-active jarvis-git-summarizer || echo "git-summarizer: stopped"

lint:
	$(VENV)/bin/python -m py_compile lib/ollama_client.py lib/event_bus.py lib/model_router.py
	@echo "Lint passed"

clean:
	find /THE_VAULT/jarvis/logs/ -name "*.lock" -delete
	find /THE_VAULT/jarvis/inbox/ -name "*.tmp" -delete
```

# Acceptance Criteria

✓ `make setup` creates .venv and installs all required packages
✓ `make test-mvp1` passes when Ollama is running
✓ `make test-all` passes when all services are healthy; exits non-zero if any test fails
✓ `make status` outputs one line per service showing running/stopped
✓ `make lint` exits 0 when all library files are syntactically valid Python

# AGENT PROMPT — paste into Claude Code / Continue.dev

Implement /THE_VAULT/jarvis/Makefile exactly as specified in the Makefile Design section above. Add a `test_data/` directory with: `sample.md` (a 500-word Markdown file with ## headings), `sample.pdf` (any small PDF). Each test target should exit non-zero on failure. `make test-all` depends on all individual targets. `make status` uses `systemctl --user is-active` for each service name. Do NOT add any external test framework — pure Make + Python __main__ blocks + curl.

# MVP 17 — Secrets & Environment Manager

Depends on: MVP 1

A tiny validation layer run at startup by every service and pipeline. Checks that all required environment variables are present, gives a clear human-readable error if any are missing (instead of a cryptic `KeyError` 30 seconds into a processing run), and optionally loads from a `.env` file for development. This is especially important when services are launched by systemd — env injection into systemd user units is non-obvious and errors surface as silent failures.

| | |
|---|---|
| Language | Python 3.12 |
| Output | /THE_VAULT/jarvis/lib/env_manager.py |
| Used by | Every MVP at startup (3-line import) |
| Dev fallback | Loads /THE_VAULT/jarvis/config/.env if env vars not already set |
| Validation | Checks all required vars, prints table of missing ones, exits 1 |

# Public Interface

```python
# lib/env_manager.py
REQUIRED_VARS = {
    'OLLAMA_BASE_URL':       ('http://localhost:11434', 'Ollama REST API endpoint'),
    'ANYTHINGLLM_BASE_URL':  ('http://localhost:3001',  'AnythingLLM REST API endpoint'),
    'ANYTHINGLLM_API_KEY':   (None,                     'AnythingLLM authentication key'),
    'GITEA_WEBHOOK_SECRET':  (None,                     'HMAC secret for Gitea webhooks'),
}

def load(required: list[str] = None) -> dict:
    # 1. Load /THE_VAULT/jarvis/config/.env if it exists (KEY=VALUE format, # comments)
    # 2. Check each required var (or all REQUIRED_VARS if required=None)
    # 3. Use default if provided, else raise with helpful message
    # 4. Return dict of all resolved values
    ...

def validate_or_exit(required: list[str] = None):
    # Calls load(), prints a missing-vars table, exits 1 if any are missing
    # Call this at the top of every service's main() block
    ...
```

# Usage in Every MVP (3 lines)

```python
from lib.env_manager import validate_or_exit
validate_or_exit(['OLLAMA_BASE_URL', 'ANYTHINGLLM_API_KEY'])
# proceeds only if all listed vars are set
```

# .env File (for development — NOT committed to git)

```bash
# /THE_VAULT/jarvis/config/.env
OLLAMA_BASE_URL=http://localhost:11434
ANYTHINGLLM_BASE_URL=http://localhost:3001
ANYTHINGLLM_API_KEY=your-key-here
GITEA_WEBHOOK_SECRET=your-secret-here
```

# Acceptance Criteria

✓ `validate_or_exit(['ANYTHINGLLM_API_KEY'])` exits 0 when the var is set
✓ `validate_or_exit(['ANYTHINGLLM_API_KEY'])` prints a clear error and exits 1 when the var is missing
✓ `load()` reads from .env file when environment variable is not already set
✓ Vars explicitly set in environment always take precedence over .env file
✓ `load()` returns defaults for vars with defaults defined; never exits for those
✓ The .env template is documented in config/env.example with all REQUIRED_VARS and descriptions

# AGENT PROMPT — paste into Claude Code / Continue.dev

Implement /THE_VAULT/jarvis/lib/env_manager.py. Define REQUIRED_VARS dict as shown. `load(required=None)`: read /THE_VAULT/jarvis/config/.env if it exists (parse KEY=VALUE lines, skip # comments, strip whitespace), set any missing os.environ keys from it (env takes priority), then resolve each requested var: use os.environ value if set, else default if defined, else add to missing list. `validate_or_exit(required=None)`: call load(), if any vars are missing print a table of NAME / DESCRIPTION / STATUS for all required vars and call sys.exit(1). Also write config/env.example listing all REQUIRED_VARS with their descriptions. No external dependencies.

# MVP 18 — Universal PDF Converter (Round-Tripper)

Depends on: MVP 5
Allows the system to convert any indexed Markdown or text document back into a standardized PDF format. This is used to "round-trip" legacy or poorly formatted notes through the high-fidelity MinerU pipeline for consistent semantic cleaning and layout extraction.

| | |
|---|---|
| Language | Python 3.12 |
| Output | /THE_VAULT/jarvis/tools/pdf_converter.py |
| Tooling | Pandoc + WeasyPrint |
| Capability | Convert .md / .txt / .html -> .pdf for MinerU re-processing |

### Implementation Logic:
1. Receives a path to an existing indexed file.
2. Uses **Pandoc** to convert the content into a temporary HTML intermediate (applying a standard technical CSS stylesheet).
3. Uses **WeasyPrint** to render the PDF.
4. Drops the result into `/THE_VAULT/jarvis/inbox/`, triggering MVP 5 (Ingest) to run the MinerU/Cleaner pipeline.

# Complete Jarvis File Structure

![](images/84b203035200bd1b9078ce087bcea1a4608820e401a26974504f8a364d817706.jpg)

# Summary of Changes — v3 → v3.1

<table><tr><td>Area</td><td>Before (v3)</td><td>After (v3.1)</td><td>Impact</td></tr><tr><td colspan="1" rowspan="1">Chat model</td><td colspan="1" rowspan="1">qwen2.5-coder:14b</td><td colspan="1" rowspan="1">qwen3:14b-q4_K_M</td><td colspan="1" rowspan="1">Better reasoning, thinking mode</td></tr><tr><td colspan="1" rowspan="1">FIM model</td><td colspan="1" rowspan="1">qwen2.5-coder:1.5b</td><td colspan="1" rowspan="1">qwen3:1.7b</td><td colspan="1" rowspan="1">Smarter completions, samespeed</td></tr><tr><td colspan="1" rowspan="1">model_router</td><td colspan="1" rowspan="1">No thinking flag</td><td colspan="1" rowspan="1">thinking=True/False</td><td colspan="1" rowspan="1">Qwen3 /think toggle per task</td></tr><tr><td colspan="1" rowspan="1">FIM endpoint</td><td colspan="1" rowspan="1">No suffix param</td><td colspan="1" rowspan="1">suffix= required</td><td colspan="1" rowspan="1">Proper FIM, not degradedcompletion</td></tr><tr><td colspan="1" rowspan="1">Search</td><td colspan="1" rowspan="1">DuckDuckGo API</td><td colspan="1" rowspan="1">SearXNG:8888</td><td colspan="1" rowspan="1">Fullresults, SO/GitHub/arXivengines</td></tr><tr><td colspan="1" rowspan="1">Ratatui</td><td colspan="1" rowspan="1">0.29</td><td colspan="1" rowspan="1">0.30+</td><td colspan="1" rowspan="1">Flicker fix, better StatefulWidget</td></tr><tr><td colspan="1" rowspan="1">MinerU install</td><td colspan="1" rowspan="1">mineru[all</td><td colspan="1" rowspan="1">mineru[pipeline]</td><td colspan="1" rowspan="1">No GPU deps on CPU-onlymachine</td></tr><tr><td colspan="1" rowspan="1">Subprocess</td><td colspan="1" rowspan="1">No timeout</td><td colspan="1" rowspan="1">timeout=60 (all)</td><td colspan="1" rowspan="1">Prevents hangs on nix eval errors</td></tr><tr><td colspan="1" rowspan="1">local-ai.nix</td><td colspan="1" rowspan="1">Exists (broken)</td><td colspan="1" rowspan="1">DELETE IT</td><td colspan="1" rowspan="1">No NVIDIA GPU on i7-1165G7</td></tr></table>

# LOCAL JARVIS

Full-Stack Local AI Engineering Roadmap

Dell Vostro 3510 · i7-1165G7 · 16 GB DDR4 · 800 GB /THE_VAULT

# 0. The Core Philosophy — Specificity Over Scale

Large AI labs win with scale: trillion-parameter models, data centers, billions in compute. You cannot compete on that axis. You win on a completely different axis: specificity, context, and automation depth.

A 14B model with perfect context — your codebase fully indexed, your NixOS config embedded, your past decisions remembered, your workflows automated — outperforms a general 70B model that knows nothing about you. You are not building a general intelligence. You are building a deeply specialised one that knows exactly one person's environment, goals, and style.

KEY INSIGHT  

<table><tr><td rowspan=1 colspan=1> What big models have that you don&#x27;t</td><td rowspan=1 colspan=1>What you have that big models don&#x27;t</td></tr><tr><td rowspan=1 colspan=1>Trillion parameters</td><td rowspan=1 colspan=1>Your exact codebase in the vector index (BM25+vectorhybrid)</td></tr><tr><td rowspan=1 colspan=1>Massive training data</td><td rowspan=1 colspan=1>Your NixOS config as RAG context</td></tr><tr><td rowspan=1 colspan=1>Cloud compute</td><td rowspan=1 colspan=1>user_context.md —your identity injected every call</td></tr><tr><td rowspan=1 colspan=1>General world knowledge</td><td rowspan=1 colspan=1>Four-tier memory: working, episodic, semantic,procedural</td></tr><tr><td rowspan=1 colspan=1>Broad capability</td><td rowspan=1 colspan=1>Fully automated self-improving pipelines with feedbackloops</td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Daily digest + weekly report — compound growth madevisible</td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Zero latency · Zero privacy risk · Ratatui dashboard to seeit all</td></tr></table>

Prompt engineering $^ +$ RAG $^ +$ agents $^ +$ automation $=$ artificial general intelligence for your specific domain. You don't need GPT-4. You need GPT-4-for-qwerty. The system compounds over time. Every indexed document makes retrieval sharper. Every prompt cycle makes outputs better. Every Rust rewrite makes pipelines faster. The daily digest makes the compounding visible. The weekly report tells you which parts are worth extending.

# 1. Merged System Architecture

Every node in the system maps onto a concrete local tool. Key changes in v3.1: Qwen3-14B replaces Qwen2.5-Coder-14B, Qwen3-1.7B replaces Qwen2.5-Coder-1.5B, SearXNG replaces DuckDuckGo API, Ratatui ${ 0 . 3 0 + }$ replaces 0.29, model_router gains thinking mode flag, FIM /complete endpoint requires suffix $\equiv$ parameter.

<table><tr><td rowspan=1 colspan=1>Layer</td><td rowspan=1 colspan=1>Tool /Tech</td><td rowspan=1 colspan=1>Role in Jarvis</td><td rowspan=1 colspan=1>Runs on</td></tr><tr><td rowspan=1 colspan=1>LLM Engine</td><td rowspan=1 colspan=1>Ollama</td><td rowspan=1 colspan=1>Qwen3-14B (chat/fix/diagnose — thinking=True), Qwen3-1.7B(FIM autocomplete), Mistral-7B (clean/summarize). Keepaliveping from coding_agent prevents 5-min idle unload.</td><td rowspan=1 colspan=1>CPU·RAM·/THE_VAULT</td></tr><tr><td rowspan=1 colspan=1>RAG</td><td rowspan=1 colspan=1>code_rag.py (MVP 12)</td><td rowspan=1 colspan=1>SQLite + BM25+vector hybrid. 0.7×vector + 0.3×BM25. One .dbper domain. No external service.</td><td rowspan=1 colspan=1>/THE_VAULT/jarvis/index/</td></tr><tr><td rowspan=1 colspan=1>Memory</td><td rowspan=1 colspan=1>Four tiers</td><td rowspan=1 colspan=1>Working (chat_managed, 20-msg cap) · Episodic (events.db) .Semantic (SQLite hybrid) · Procedural (prompts/best.txt).</td><td rowspan=1 colspan=1>RAM + SQLite</td></tr><tr><td rowspan=1 colspan=1>Event Bus</td><td rowspan=1 colspan=1>event_bus.py (MVP13)</td><td rowspan=1 colspan=1>emit(source, event, details) writes to events.db. 3 lines per MVP.Enables TUl, daily digest, episodic memory.</td><td rowspan=1 colspan=1>logs/events.db</td></tr><tr><td rowspan=1 colspan=1>Observability</td><td rowspan=1 colspan=1>health_monitor +Ratatui TUI (MVPs13,14)</td><td rowspan=1 colspan=1>health_monitor polls every 30s → metrics.db. Ratatui 0.30 TUIshows 4-pane live dashboard.</td><td rowspan=1 colspan=1>localhost / tmux</td></tr><tr><td rowspan=1 colspan=1>Coding Agent</td><td rowspan=1 colspan=1>coding_agent.py (MVP12)</td><td rowspan=1 colspan=1>HTTP :7002. FIM (Qwen3-1.7B, suffix= required), BM25+vectorRAG chat, looped fix (MVP 7 + thinking=True), web research(MVP 8).</td><td rowspan=1 colspan=1>localhost:7002</td></tr><tr><td rowspan=1 colspan=1>IDE</td><td rowspan=1 colspan=1>Neovim + LSP + DAP</td><td rowspan=1 colspan=1>home-manager (NOT mason.nvim). nvim-lspconfig finds tools onPATH. blink.cmp: LSP + FIM sources. nvim-dap: Ilb, debugpy.</td><td rowspan=1 colspan=1>~1.config/nvim/</td></tr><tr><td rowspan=1 colspan=1>Research</td><td rowspan=1 colspan=1>research_agent +SearXNG (MVP 8)</td><td rowspan=1 colspan=1>SearXNG self-hosted :888. Enable SO/GitHub/arXiv engines.Results auto-indexed to research.db.</td><td rowspan=1 colspan=1>localhost:8888</td></tr><tr><td rowspan=1 colspan=1>Self-improve</td><td rowspan=1 colspan=1>MVP 6 + preference.py</td><td rowspan=1 colspan=1>Generates/scores/promotes prompts weekly. Uses route(&#x27;reason&#x27;,thinking=True). preference.py injects rated responses.</td><td rowspan=1 colspan=1>/THE_VAULTjarvis/prompts/</td></tr><tr><td rowspan=1 colspan=1>Automation</td><td rowspan=1 colspan=1>systemd timers</td><td rowspan=1 colspan=1>06:00 daily digest, Sunday 23:00 weekly report, Sunday 03:00 prompt optimizer, git webhooks.</td><td rowspan=1 colspan=1>systemd user timers</td></tr><tr><td rowspan=1 colspan=1>Git</td><td rowspan=1 colspan=1>git_summarizer (MVP9)</td><td rowspan=1 colspan=1>Webhook :7001. Push → dif → Ollama → CHANGELOG.md. AIlsubprocess calls with timeout=30.</td><td rowspan=1 colspan=1>localhost:7001</td></tr><tr><td rowspan=1 colspan=1>Jarvis CLI</td><td rowspan=1 colspan=1> jarvis.py (Big MVP)</td><td rowspan=1 colspan=1>Natural language → intent →&gt; pipeline. thumbs-up/down, -shortfor Waybar,&#x27;open dashboard&#x27;→ jarvis-monitor.</td><td rowspan=1 colspan=1>/THE_VAULT/jarvis/</td></tr><tr><td rowspan=1 colspan=1>PDF Conversion</td><td rowspan=1 colspan=1>pdf_converter.py (MVP 18)</td><td rowspan=1 colspan=1>Converts legacy notes/docs to PDF to re-trigger MinerU high-fidelity cleaning.</td><td rowspan=1 colspan=1>Pandoc / WeasyPrint</td></tr>
</table>

# HARDWARE NOTE

i7-1165G7 · 16 GB DDR4: Qwen3-14B runs at ${ \sim } 3 { \cdot } 4 ~ \mathrm { t o k } / \mathsf { s }$ , Mistral-7B at ${ \sim } 8 { \cdot } 1 2 \ \mathrm { t o k } / \mathsf s$ , Qwen3-1.7B at $\sim 3 0 +$ tok/s. coding_agent sends a keepalive ping every 4 minutes so the model stays loaded. Cold start after 5-min idle takes 30s — the ping prevents this. There is NO NVIDIA GPU on this machine — delete local-ai.nix from your NixOS config.

# 2. Complete Tool Stack Reference

2.1 Inference — Ollama $\scriptstyle +$ Model Router

UPDATED: Models upgraded to Qwen3. model_router.route() gains thinking= flag.

<table><tr><td rowspan=1 colspan=1>qwen3:14b-q4_K_M</td><td rowspan=1 colspan=1>task:&#x27;chat&#x27;, &#x27;fix&#x27;, &#x27;diagnose&#x27;, &#x27;reason&#x27;. ~3-4 tok/s. Use thinking=True for fix/diagnose.</td></tr><tr><td rowspan=1 colspan=1>qwen3:1.7b</td><td rowspan=1 colspan=1>task: &#x27;complete&#x27; (FIM only). ~30+ tok/s. Requires suffix= parameter in generate().</td></tr><tr><td rowspan=1 colspan=1>mistral:7b-instruct-q4_K_M</td><td rowspan=1 colspan=1>task:&#x27;clean&#x27;,&#x27;summarize&#x27;,&#x27;classify&#x27;,&#x27;score&#x27;. ~8-12 tok/s. No thinking mode needed.</td></tr><tr><td rowspan=1 colspan=1>nomic-embed-text</td><td rowspan=1 colspan=1>task: &#x27;embed&#x27;. 768-dim float32 vectors for all RAG.</td></tr></table>

# model_router.route() — Updated Signature

route(task: str, context_chars: int $\qquad = \quad 0$ , thinking: bool $=$ False) $- >$ str: # thinking=True: prepend /think to first user message (Qwen3 extended reasoning) # thinking=False: prepend /no_think (faster, better for cleaning/summarising) # # Use thinking $\bf \tilde { = }$ True for: fix, diagnose, reason, optimize (meta-prompt) # Use default (False) for: clean, summarize, classify, score, complete

# Usage:

response $=$ chat(route('fix', thinking $: =$ True), messages) # qwen3:14b, thinking on response $=$ chat(route('clean'), messages) # mistral:7b, /no_think response $=$ generate(route('complete'), prefix, suffi $\scriptstyle . \mathtt { x } = \mathtt { s f } \mathtt { x }$ ) # qwen3:1.7b-q4_K_M, FIM

# Model Digest Pinning

# After ollama pull, run: ollama show <model> --modelfile | grep FROM # Copy the sha256:... hash into models.toml [model_digests]. # Ollama sometimes silently updates weights behind the same tag. # Your optimised prompts may break. Pinning makes this diagnosable.

[model_digests]

chat $=$ "sha256:. # captured after: ollama pull qwen3:14b-q4_K_M fast $=$ "sha256:. " # captured after: ollama pull mistral:7b-instruct-q4_K_M complete $=$ "sha256:..." # captured after: ollama pull qwen3:1.7b-q4_K_M

# 2.2 RAG — SQLite BM $\pmb { 2 5 + }$ Vector Hybrid

retrieve_hybrid() combines cosine similarity (semantic) with BM25 (keyword precision). score $= 0 . 7$ ×vector + $0 . 3 { \times } \mathsf { B } \mathsf { M } 2 5$ . Use hybrid by default in /chat — it handles both 'how does async error handling work' and 'find OllamaError definition'.

<table><tr><td rowspan=1 colspan=1>Semantic query</td><td rowspan=1 colspan=1>retrieve() or retrieve_hybrid()</td></tr><tr><td rowspan=1 colspan=1>Exact identifier</td><td rowspan=1 colspan=1>retrieve_hybrid) — BM25 component excels here</td></tr><tr><td rowspan=1 colspan=1>Conceptual + code</td><td rowspan=1 colspan=1>retrieve_hybridl) — covers full spectrum</td></tr><tr><td rowspan=1 colspan=1>Web research</td><td rowspan=1 colspan=1>MVP 8 SearXNG (localhost:8888)</td></tr></table>

# 2.3 Four-Tier Memory

<table><tr><td>Working</td><td>RAM list · capped at 20 msgs · chat_managed() auto-summarises at 5000 chars</td></tr><tr><td>Episodic</td><td>events.db · query_today() injected into every /chat system prompt</td></tr><tr><td>Semantic</td><td>SQLite .db files · hybrid BM25+vector retrieval</td></tr><tr><td>Procedural</td><td>prompts/best.txt + successful agent outputs</td></tr></table>

# 2.4 IDE — Neovim $\mathbf { + }$ home-manager

<table><tr><td rowspan=1 colspan=1>rust-analyzer</td><td rowspan=1 colspan=1>Rust LSP — inline borrow checker errors</td></tr><tr><td rowspan=1 colspan=1>pyright</td><td rowspan=1 colspan=1>Python LSP — type inference, import resolution</td></tr><tr><td rowspan=1 colspan=1>nil</td><td rowspan=1 colspan=1>Nix LSP — attribute completion, module option docs</td></tr><tr><td rowspan=1 colspan=1>clang-tools</td><td rowspan=1 colspan=1>C/C++ (clangd)</td></tr><tr><td rowspan=1 colspan=1>gopls · ts_Is · lua_Is · bashls · taplo</td><td rowspan=1 colspan=1>Go, TypeScript, Lua, Bash, TOML LSPs</td></tr><tr><td rowspan=1 colspan=1>rustfmt · black · ruff · alejandra · stylua· shfmt</td><td rowspan=1 colspan=1>Formatters (f in any buffer)</td></tr><tr><td rowspan=1 colspan=1>Ildb · python313Packages.debugpy</td><td rowspan=1 colspan=1>Debug adapters: F5 debug session, b breakpoint</td></tr></table>

# 2.5 Web Research — SearXNG

$\spadesuit$ UPDATED: SearXNG replaces DuckDuckGo. Configure settings.yml to add SO/GitHub/arXiv engines.

SearXNG is a self-hosted meta-search aggregator: full results from Google/Bing/DDG and dozens of niche providers, no API key, no rate limits, fully private, runs on localhost:8888. The DuckDuckGo Instant Answer API returns zero results for technical queries and is increasingly unreliable for automated use.

# Run SearXNG:  
docker run -d --name searxng --restart unless-stopped \-p 127.0.0.1:8888:8080 \-v \~/searxng/settings.yml:/etc/searxng/settings.yml \searxng/searxng

# Critical: add these engines to settings.yml for technical queries: # stackoverflow, github, arxiv, google (or bing) # These give dramatically better signal than web-only results.

# MVP 8 query: results $=$ requests.get('http $\therefore$ //localhost:8888/search', params $=$ {'q': query, 'format': 'json'}, timeout ${ \tt = } 1 0$ ).json() urls $=$ [r['url'] for r in results.get('results', [])]

# 2.6 Self-Improving Pipeline

$\spadesuit$ UPDATED: Meta-prompt step uses route('reason', thinking=True) for deeper variant generation.

<table><tr><td rowspan=1 colspan=1>Step</td><td rowspan=1 colspan=1>What happens</td></tr><tr><td rowspan=1 colspan=1>1.Spec</td><td rowspan=1 colspan=1>spec.json: task_description, test_inputs, quality_rules (not_contains, length_ratio, lm_judge)</td></tr><tr><td rowspan=1 colspan=1>2. Generate</td><td rowspan=1 colspan=1>route(&#x27;reason&#x27;, thinking=True) meta-prompt → 5 variants: strict, examples, chain-of-thought, role,negative-constraints</td></tr><tr><td rowspan=1 colspan=1>3.Score</td><td rowspan=1 colspan=1>Each variant × each test input → weighted score. Regression protection: only promote if score &gt; currentbest.</td></tr><tr><td rowspan=1 colspan=1>4. Promote</td><td rowspan=1 colspan=1>Winner →&gt;prompts//best.txt. Previous archived in runs/. Never deleted.</td></tr><tr><td rowspan=1 colspan=1>5. Feedback</td><td rowspan=1 colspan=1> jarvis thumbs-up / thumbs-down → feedback.jsonl. preference.py injects best/worst rated responses.</td></tr><tr><td rowspan=1 colspan=1>6. Weekly</td><td rowspan=1 colspan=1>systemd timer Sunday 03:00: adds 2-3 real usage examples from feedback.jsonl → re-run loop.</td></tr></table>

# 2.7 Subprocess Safety — Critical Rules

■ NEVER use shell=True with model output. ALWAYS set timeout= on every subprocess call.

# CORRECT: list-form $^ +$ timeout   
result $=$ subprocess.run( ['cargo', 'check', '--manifest-path', manifest], capture_output $=$ True, timeout $_ { = 6 0 }$ # $\gets$ required on EVERY subprocess call; 120 for nix flake check   
# WRONG — shell injection risk if model output contains ; \` \$() etc.   
result $=$ subprocess.run(f'cargo check {user_input}', shell $=$ True) # NEVER

# Default timeouts by command type: # git diff: timeout $= 3 0$ # nix flake check: timeout $= \mathtt { 1 2 0 }$ # cargo check: timeout $= 6 0$ # python compile: timeout $= 3 0$ # general: timeout $_ { = 6 0 }$

# 3. Learning Roadmap — 8 Phases

Background: CS:APP done, C competent, JS/Go surface level, Linux strong, Python zero, Rust zero. Each phase produces working software. Theory follows from building.

<table><tr><td rowspan=1 colspan=1>#</td><td rowspan=1 colspan=1>Phase</td><td rowspan=1 colspan=1>What You Build</td><td rowspan=1 colspan=1>What You Learn</td></tr><tr><td rowspan=1 colspan=1>P1</td><td rowspan=2 colspan=1>Foundation (2-4wks)</td><td rowspan=2 colspan=1>Ollama running · Open WebUI verified · LSP tools viahome-manager (which rust-analyzer returns /nix/store path) ./THE_VAULT mounted · models downloaded (qwen3:14bovernight, 9GB) · tmux jarvis session layout · MVP 1implemented and tested. DELETE local-ai.nix fromconfiguration.nix — it references CUDA packages unavailableon your i7-1165G7.</td><td rowspan=2 colspan=1>Ollama internals · transformer inference ·NixOS home-manager · LSP protocol .FIM autocomplete · tmux sessionmanagement · why local-ai.nix must go.</td></tr><tr><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>P2</td><td rowspan=1 colspan=1>RAG Core (3-5wks)</td><td rowspan=1 colspan=1>code_rag.py with 3 SQLite indexes (nixosenv.db, codebase.db,documents.db). code_indexer.py CLI. retrieve() andretrieve_hybrid() (BM25+vector) tested. user_context.mdwritten. Model digest SHA values pinned in models.toml.Journal folder started.</td><td rowspan=1 colspan=1>Vector embeddings · cosine similarity ·BM25 keyword search · hybrid scoring ·SQLite BLOB storage · numpy linearalgebra.</td></tr><tr><td rowspan=1 colspan=1>P3</td><td rowspan=1 colspan=1>Python (3-4wks)</td><td rowspan=1 colspan=1>MVPs 1-5 implemented and passing acceptance criteria.event_bus.py and model_router.py in lib/. emit() retrofitted intoall 5 MVPs. Makefile with make test passing. chat_managed()added. mineru[pipeline] installed (NOT mineru[all).</td><td rowspan=1 colspan=1>Python fil /O · HTTP requests · JSON .subprocess list-form with timeout= .argparse · tomlib · SQLite · Makefile astest harness.</td></tr><tr><td rowspan=1 colspan=1>P4</td><td rowspan=1 colspan=1>Automation(4-6 wks)</td><td rowspan=1 colspan=1>systemd timers running · SearXNG running with SO/GitHub/arXiv enginesconfigured · MVP 6 optimizer with route(&#x27;reason&#x27;,thinking=True) · MVP 7 agent loop with thinking=True · MVP 8research agent · health_monitor.py running · daily_digest.pyworking · jarvis status -short wired to Waybar ·thumbs-up/down added to jarvis CLl · model_router.route()used in all MVPs.</td><td rowspan=1 colspan=1>systemd timer scheduling · webhook triggers · Qwen3 thinking mode·observability patterns ·libnotifyintegration.</td></tr><tr><td rowspan=1 colspan=1>P5</td><td rowspan=1 colspan=1>Full Agent (4-6wks)</td><td rowspan=1 colspan=1>MVPs 8-10 + Big MVP implemented. jarvis CLI routes all intents. NixOS jarvis.nix module written. preference.py working(50+ feedback.jsonl entries). make test passes all 10 MVPs.MVP 12 coding agent on :7002 with FIM suffix= fix confirmed.</td><td rowspan=1 colspan=1>Agent design patterns · ReAct loop .validation-driven generation · systemduser services · subprocess safety · shellinjection prevention.</td></tr><tr><td rowspan=1 colspan=1>P6</td><td rowspan=1 colspan=1>Neovim IDE(3-4 wks)</td><td rowspan=1 colspan=1>MVP 12 fully wired: Ilsp.lua (all servers), complete.lua(blink.cmp with FIM suffix=), agent.lua (all j* keybinds), dap.lua(F5/F10/b working in Rust). Four-tier memory fully active.BM25+vector hybrid in use. Web fallback rate tracked in weeklyreport.</td><td rowspan=1 colspan=1>nvim-lspconfig internals · blink.cmpsource API · Lua plugin development -DAP protocol ·Ildb adapter · FIM tokenformat · four-tier context construction.</td></tr><tr><td rowspan=1 colspan=1>P7</td><td rowspan=1 colspan=1>Rust — RatatuiTUI (6-8 wks)</td><td rowspan=1 colspan=1>MVP 14 jarvis-monitor implemented with Ratatui 0.30+ (NOT0.29). Four-pane layout. Async data polling via tokio mpsc.Also: MVP 1 Ollama client rewritten in Rust as first CLI project.</td><td rowspan=1 colspan=1>Rust chapters 1-10 · ownership ·borrowing · lifetimes · tokio async · mpscchannels · ratatui 0.30 widget API .rusqlite · structs · traits.</td></tr><tr><td rowspan=1 colspan=1>P8</td><td rowspan=1 colspan=1>Full Jarvis +Scaling(ongoing)</td><td rowspan=1 colspan=1>GraphRAG optional layer. sqlite-vss for scalable vector search.MVP 6 prompt scorer rewritten in Rust. All 14 MVPs + Big MVPrunning. Prompts self-optimising weekly. Compound growthvisible in weekly reports.</td><td rowspan=1 colspan=1>GraphRAG · knowledge graph traversal .sqlite-vss·approximatenearest-neighbour search · Rust profiling ·WASM.</td></tr></table>

# 4. Python Fast Track

You have zero Python but strong C. Python is C with memory management removed and a standard library that does everything. You only need a focused subset.

# VENV FIRST — BEFORE ANYTHING ELSE

python -m venv /THE_VAULT/jarvis/.venv source /THE_VAULT/jarvis/.venv/bin/activate pip install requests numpy watchdog aiohttp rank-bm25 # Or: cd /THE_VAULT/jarvis && make setup

# MinerU: install pipeline backend ONLY (no GPU deps on i7-1165G7) pip install 'mineru[pipeline]' # NOT mineru[all]

# Week 1 — Syntax and Files

Learn: variables, functions, loops, list/dict, f-strings, file I/O, pathlib. First real script: MVP 2 chunker — split a MinerU .md by ## headings into files.

# Week 2 — HTTP and JSON

Learn: requests, JSON parsing, environment variables, try/except. First real script: MVP 1 Ollama client — call the API, stream response to file. model_router.route() goes here too.

# Week 3 — Subprocess and OS Integration

Learn: subprocess.run() as list, os.path, shutil, argparse.

# SECURITY — NEVER shell=True WITH MODEL OUTPUT

subprocess.run(['cargo','check'], capture_output $=$ True, timeout $= 6 0$ ) $\gets$ correct subprocess.run(f'cargo check {user_input}', shell $. =$ True) $\gets$ shell injection risk Model-generated content can contain semicolons, backticks, \$() — these execute if shell $= ^ { \prime }$ True is used. Always use list-form subprocess. Always set timeout $=$ .

# Week 4 — Async

Learn: asyncio, async/await, aiohttp. Needed for agent scripts. event_bus.py uses async writes.   
daily_digest.py uses aiohttp if fetching multiple sources.

# 5. Rust Learning Track

CS:APP background makes Rust significantly easier than for most people. You already understand stack vs heap, pointer arithmetic, and why memory safety matters. Rust's ownership model is the compiler enforcing what you already know you should do in C.

# 5.1 C to Rust Mental Model

<table><tr><td rowspan=1 colspan=1>Rust concept</td><td rowspan=1 colspan=1>Your CS:APP mental model</td></tr><tr><td rowspan=1 colspan=1>Ownership</td><td rowspan=1 colspan=1>Every value has exactly one owner. Goes out of scope → freed. This is &#x27;who calls free(&#x27; enforcedby the compiler.</td></tr><tr><td rowspan=1 colspan=1>Borrowing</td><td rowspan=1 colspan=1>&amp;T; read-only · &amp;mut; T mutable · one mutable borrow at a time. Prevents data races at compiletime.</td></tr><tr><td rowspan=1 colspan=1>Lifetimes</td><td rowspan=1 colspan=1>Compiler tracks how long references are valid. Prevents use-after-free — the exact bug CS:APPtaught you to fear, now a compile error.</td></tr><tr><td rowspan=1 colspan=1>Result</td><td rowspan=1 colspan=1>Explicit error handling. Forces you to handle every failure path — like checking errno in C, butcompiler-enforced.</td></tr></table>

# 5.2 Rust Project Sequence

<table><tr><td rowspan=1 colspan=1>P7 first</td><td rowspan=1 colspan=1>MVP 1 Ollama client in Rust — first CLI project</td></tr><tr><td rowspan=1 colspan=1>P7 main</td><td rowspan=1 colspan=1>MVP 14 Ratatui TUI (jarvis-monitor) — use ratatui 0.30, NOT 0.29</td></tr><tr><td rowspan=1 colspan=1>P8</td><td rowspan=1 colspan=1>MVP 6 prompt scorer in Rust</td></tr><tr><td rowspan=1 colspan=1>P8</td><td rowspan=1 colspan=1>code_rag.py retrieval in Rust</td></tr><tr><td rowspan=1 colspan=1>P8+</td><td rowspan=1 colspan=1>coding_agent.py HTTP server in Rust (axum)</td></tr></table>

$\spadesuit$ UPDATED: MVP 14 must use ratatui ${ \mathfrak { o } } . 3 0 +$ and crossterm 0.29. 0.30 fixes flicker and improves StatefulWidget ergonomics vs 0.29.

# 6. NixOS — System Configuration

# 6.0 Delete local-ai.nix

■ DELETE local-ai.nix from your NixOS config and remove it from configuration.nix imports.

Your local-ai.nix module references CUDA packages (cudaPackages) that are completely inoperative on your hardware. The Dell Vostro 3510's i7-1165G7 has Intel Iris Xe integrated graphics — there is no NVIDIA GPU. The module is broken dead code that will cause nix flake check errors. Everything it was trying to do is fully replaced by the Jarvis Ollama CPU inference stack.

# Steps to remove:   
# 1. Delete the file:   
rm \~/NixOSenv/modules/local-ai.nix   
# 2. Remove from configuration.nix imports:   
# imports $=$ [ ./modules/local-ai.nix ]; $\gets$ delete this line   
# 3. Run MVP 10 validator to confirm clean:   
python /THE_VAULT/jarvis/pipelines/nixos_validator.py --repo \~/NixOSenv   
# Expected: 'Validation passed', exit 0

# 6.1 home.nix — Dev Tools (home-manager, not mason.nvim)

home.packages $=$ with pkgs; [ # LSP servers — home-manager only, NOT mason.nvim rust-analyzer pyright nil clang-tools gopls nodePackages.typescript-language-server lua-language-server nodePackages.bash-language-server taplo yaml-language-server # Formatters $^ +$ linters rustfmt black ruff alejandra stylua shfmt shellcheck # Debug adapters lldb python313Packages.debugpy # rank-bm25 installed in .venv, not here   
];   
# Verify: which rust-analyzer # must return /nix/store/... path

# 6.2 modules/jarvis.nix — Services on Boot (Phase $5 +$

{ config, pkgs, ... }: { systemd.user.services $=$ let py $=$ "/THE_VAULT/jarvis/.venv/bin/python"; jd $=$ "/THE_VAULT/jarvis"; in { jarvis-ingest $\begin{array} { r c l } { \displaystyle = } & { \displaystyle \left\{ \begin{array} { r c l } \end{array} \right. } \end{array}$ serviceConfig.ExecStart $=$ "\${py} \${jd}/pipelines/ingest.py --watch"; serviceConfig.Restart $=$ "on-failure"; wantedBy $=$ [ "default.target" ]; }; jarvis-coding-agent = { serviceConfig.ExecStart $=$ "\${py} \${jd}/services/coding_agent.py"; serviceConfig.Restart $=$ "on-failure"; }; jarvis-health-monitor $=$ { serviceConfig.ExecStart $=$ "\${py} \${jd}/services/health_monitor.py"; serviceConfig.Restart $=$ "on-failure"; }; jarvis-git-summarizer $=$ { serviceConfig.ExecStart $=$ "\${py} \${jd}/services/git_summarizer.py"; serviceConfig.Restart $=$ "on-failure"; }; };   
}

# 6.3 Waybar Widget

"custom/jarvis": { "exec": "/THE_VAULT/jarvis/.venv/bin/python /THE_VAULT/jarvis/jarvis.py status --short", "interval": 30, "format": " {}"   
}   
# Output: '✓5/6 | inbox:2 | review:1' or '✗Ollama | inbox:0'

# 7. Self-Improvement — Detailed Design

Four interlocking loops that make the system improve without your involvement. Each loop feeds the next.

<table><tr><td rowspan=1 colspan=1>Feedback accumulation</td><td rowspan=1 colspan=1>Continuous — jarvis thumbs-up / thumbs-down</td></tr><tr><td rowspan=1 colspan=1>Preference model</td><td rowspan=1 colspan=1>Every /chat call— injects best/worst rated past response</td></tr><tr><td rowspan=1 colspan=1>Prompt optimization</td><td rowspan=1 colspan=1>Weekly — Sunday 03:00 via systemd timer · uses route(&#x27;reason&#x27;, thinking=True)</td></tr><tr><td rowspan=1 colspan=1>Compound reporting</td><td rowspan=1 colspan=1>Daily 06:00 + Sunday 23:00</td></tr></table>

# Looped Reasoning Agent (MVP 7) — Why Smaller Models Work

# The loop — correct structure   
for attempt in range(1, max_retries $^ { + } \perp$ ): response $=$ chat_managed(route('fix', thinking $: = "$ True), context) code $=$ extract_code_block(response) write_to_temp(code) # ALWAYS list-form, NEVER shell $=$ True, ALWAYS timeout= result $=$ subprocess.run( ['cargo', 'check', '--manifest-path', manifest], capture_output $=$ True, timeout $= 6 0$ ) if result.returncode $\qquad = = \quad 0$ : write_output(code) emit( $^ { 1 } \pm \mathtt { i x }$ ', 'completed', {'attempts': attempt}) subprocess.run(['notify-send', 'Jarvis', f'Fixed in {attempt} attempt(s)']) break emit('fix', 'failed', {'attempt': attempt, 'stderr': result.stderr[:200]}) context $+ =$ [ {'role': 'assistant', 'content': response}, {'role': 'user', 'content': f'Failed:\n{result.stderr}\nFix it.'} ]   
else: write_escalation(task, context) emit('fix', 'escalated', {'task': task, 'attempts': max_retries}, level $= "$ WARN') subprocess.run(['notify-send', 'Jarvis', 'Agent loop escalated — see review/'])

# 8. Getting Started — Ordered Steps

# Phase 1 — This Week

1. Mount /THE_VAULT: lsblk $\mathbf { - } \mathbf { \nabla } \mathbf { f } $ copy sda2 UUID verify in configuration.nix fileSystems.

2. Pull models: ollama pull nomic-embed-text && ollama pull qwen3:1.7b-q4_K_M && ollama pull mistral:7b-instruct-q4_K_M. Pull qwen3:14b overnight (\~9 GB).

3. Install dev tools via home-manager: add rust-analyzer, pyright, nil, clang-tools, lldb, debugpy to home.packages $ \mathsf { h m } $ verify: which rust-analyzer.

4. DELETE local-ai.nix: rm \~/NixOSenv/modules/local-ai.nix and remove its import from configuration.nix.   
Run nixos-rebuild to confirm clean.

5. Create Jarvis structure: mkdir -p /THE_VAULT/jarvis/{lib,tools,services,pipelines,config,index,prompts,inb ox,logs,review,outputs,journal,jarvis-monitor}

6. Create venv: cd /THE_VAULT/jarvis && python -m venv .venv && .venv/bin/pip install requests numpy watchdog aiohttp rank-bm25 && pip install 'mineru[pipeline]'

7. Write user_context.md: 200-300 words — NixOS user, learning Rust, active projects, coding conventions, preferred response patterns. Save to /THE_VAULT/jarvis/config/user_context.md.

8. Set up tmux layout: left pane Neovim, right pane 'watch -n2 python jarvis.py status'. Alias 'jdev' to restore.

9. Implement MVP 1: paste agent prompt into Claude Code. Test: python lib/ollama_client.py prints model list.

# Phase 2 — Next 2 Weeks

1. Implement MVPs 2-4 and event_bus.py: chunker, cleaner, document feeder. Add emit() to each. make test should pass.

2. Index NixOSenv: python tools/code_indexer.py \~/NixOSenv. Test: retrieve_hybrid('flatpak-theming', 'index/nixosenv.db') returns relevant chunk in top-1.

3. Pin model digests: ollama show qwen3:14b-q4_K_M --modelfile | grep FROM copy SHA paste into models.toml [model_digests]. Repeat for fast and complete.

4. Start journaling: write /THE_VAULT/journal/personal_\$(date +%Y-%m-%d).md — copy to inbox/ auto-indexed. Write one paragraph daily.

5. Install SearXNG: docker run -d --name searxng -p 127.0.0.1:8888:8080 searxng/searxng. Configure settings.yml to enable stackoverflow, github, arxiv engines. Test: curl 'http://localhost:8888/search?q=rust+lifetimes&format; $=$ json' | jq '.results[0].url'

6. Configure systemd timer and implement MVP 5 ingest pipeline. Drop test.md in inbox/ verify it appears in AnythingLLM within 60s.

7. Implement MVP 12 coding agent: python services/coding_agent.py curl http://localhost:7002/health {status:ok}. Verify FIM in a Rust file — suffix $=$ parameter must be confirmed working.

# 9. Hyper-Optimization Roadmap (Squeezing 16GB RAM)

### 9.1 NixOS Level Efficiency
- **Kernel Tuning:** Set `boot.kernel.sysctl = { "vm.swappiness" = 10; };` in `configuration.nix`. Prevents thrashing during LLM spikes.
- **Process Priority:** Run Ollama and `coding_agent.py` with `Nice=-10` in systemd units to prioritize inference over background indexing.

### 9.2 Context Window Squeezing
- **RAG Reranking:** Fetch `top_k=15`, then use a lightweight BM25 re-ranker to pick the `top_3`. Smaller, higher-quality context = faster inference.
- **Prompt Compaction:** `chat_managed()` triggers Mistral-7B summarization early (at 3000 chars) to keep Qwen3's prompt evaluation phase under 30 seconds.

### 9.4 Resource Management (CPU Priority)
- **SIGSTOP/SIGCONT**: `jarvis pause` sends `SIGSTOP` to all Ollama processes to immediately free CPU; `jarvis resume` sends `SIGCONT`.
- **Systemd Priority**: background services run with `Nice=15` and `CPUSchedulingPolicy=idle`.
- **Pause Warning**: `health_monitor.py` triggers `notify-send` if the system is paused for > 5 minutes to prevent session hang.

### 9.5 Zero-Bloat Automation
- n8n is officially removed. All background automation resides in NixOS-managed systemd user services (daemons). Zero idle RAM footprint outside of Python processing cycles.