# AI Terminology & Basics for Developers

Welcome! If you're a seasoned developer but "AI" feels like a black box, this guide is for you. Jarvis uses several core AI concepts that are easy to understand if you relate them to traditional software engineering.

---

## 1. Core Concepts

### LLM (Large Language Model)
Think of an LLM like a **massive, probabilistic autocomplete engine**. It doesn't "know" facts in a database sense; it predicts the next token (word fragment) based on patterns it learned during training.
- **Example**: Qwen3, GPT-4, Llama 3.

### Tokens
LLMs don't read words; they read "tokens." These are chunks of characters (e.g., "orchestrator" might be 2-3 tokens). 
- **Dev Analogy**: Like opcodes in assembly or byte-code. LLMs have a **Context Window** (buffer limit) measured in tokens.

### Inference
This is the process of **running** the model to get an output.
- **Traditional**: Calling a function.
- **AI**: Sending a prompt to the model and getting a completion.

---

## 2. The Jarvis "Brain" (RAG)

### RAG (Retrieval-Augmented Generation)
LLMs have a cutoff date (they don't know what you wrote 5 minutes ago). RAG fixes this by "attaching" a search engine to the LLM.
1. **Search**: Find relevant code/docs in your local database.
2. **Augment**: Paste that code into the prompt.
3. **Generate**: Ask the LLM to answer using that specific context.
- **Dev Analogy**: Like a "Search and Replace" script that feeds a compiler.

### Embeddings and Vector Databases
To search your code semantically (by meaning, not just keywords), we convert text into a list of numbers called a **Vector**.
- **Vector Database**: A specialized DB (Jarvis uses `sqlite-vec`) that finds "nearby" numbers. 
- **Dev Analogy**: Like a fuzzy-search algorithm, but based on mathematical "meaning" rather than string distance.

---

## 3. Engineering Patterns

### Prompt Engineering
The art of writing the input to get the best output. 
- **System Prompt**: The "hidden" instructions defining the AI's identity (e.g., "You are a senior NixOS engineer").
- **User Prompt**: Your specific request.

### Chains (ERS)
A single LLM call often fails at complex logic. An **ERS Chain** breaks a task into steps.
1. Step 1: Analyze the error.
2. Step 2: Search for the fix.
3. Step 3: Apply the fix.
- **Dev Analogy**: Like a CI/CD pipeline or a shell script where each command is an AI call.

### Quantization
Large models are huge (hundreds of GBs). Quantization "compresses" them (e.g., from 16-bit to 4-bit) so they fit on your RAM.
- **Example**: `qwen3:14b-q4_K_M` means it's a 14-billion parameter model compressed to 4 bits.

---

## 4. Why Local-First?

Traditional AI (ChatGPT/Claude) sends your code to a remote server. 
- **Jarvis** prioritize **Local Inference** via **Ollama**.
- Your code stays on your SSD.
- You don't need a subscription to code in a basement without Wi-Fi.

---

## 5. Learning Path for Devs

1. **Understand Git**: You're already here.
2. **Play with Prompts**: Try `jarvis 'how does [file] work?'` and see how it responds.
3. **Internalize RAG**: Read `docs/KNOWLEDGE_BASE.md`.
4. **Build a Chain**: Look at `chains/nixos_verify.yaml` to see how ERS works.
