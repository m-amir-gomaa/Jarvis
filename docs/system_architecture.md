# Jarvis System Architecture

This document provides a high-level overview of the Jarvis AI Orchestrator's internal structure and data flow.

## UML Component Diagram

```mermaid
graph TD
    subgraph "User Interface"
        CLI["CLI (jarvis.py)"]
        TUI["TUI Dashboard (jarvis-monitor)"]
    end

    subgraph "Orchestration & Pipelines"
        MI["Material Ingestor"]
        RA["Research Agent"]
        DL["Doc Learner"]
        AL["Agent Loop (Self-Improvement)"]
    end

    subgraph "Logic & Tools"
        CONV["Doc Converter (Pandoc/MinerU)"]
        CLEAN["AI Cleaner"]
        CHUNK["Chunker"]
        ROUTER["Model Router"]
    end

    subgraph "Data & Storage (The Vault)"
        KDB[("knowledge.db (RAG)")]
        EDB[("events.db (Episodic)")]
        VENV["Python VENV"]
    end

    subgraph "External Services"
        OLLAMA["Ollama (LLM)"]
        SEARXNG["SearXNG (Search)"]
    end

    %% Interactions
    CLI --> MI
    CLI --> AL
    CLI --> RA
    
    MI --> RA
    MI --> CONV
    MI --> DL
    
    DL --> CHUNK
    DL --> CLEAN
    DL --> KDB
    
    AL --> CLI
    AL --> ROUTER
    
    CLEAN --> ROUTER
    ROUTER --> OLLAMA
    RA --> SEARXNG
    RA --> ROUTER
    
    CLI --> EDB
    TUI --> EDB
```

## Component Descriptions

| Component | Responsibility |
|-----------|----------------|
| **jarvis.py** | Main entry point, intent classification, safety confirmation, and command routing. |
| **Material Ingestor** | Orchestrates research and automated ingestion of coding materials (books/docs). |
| **Doc Learner** | Handles the ingestion of URLs and local files into the knowledge base. |
| **Agent Loop** | A self-correcting orchestrator for complex tasks and autonomous self-improvement. |
| **Doc Converter** | Uses Pandoc and MinerU (magic-pdf) for high-fidelity Markdown extraction. |
| **Knowledge Manager** | Manages the multi-layered SQLite knowledge base for RAG. |
| **Model Router** | Maps specific AI tasks (summarize, reason, clean) to the best-fit local LLM. |
| **The Vault** | High-capacity storage for databases, virtual environments, and intermediate files. |

## Data Flow: Material Indexing
1. User provides a topic via CLI.
2. **Material Ingestor** triggers **Research Agent** to find strategies/sources.
3. User confirms findings.
4. User places files in `~/Downloads/JarvisMaterials`.
5. **Ingestor** detects file type, uses **Doc Converter** if needed, and calls **Doc Learner**.
6. **Doc Learner** chunks, cleans, and stores content in **knowledge.db**.
