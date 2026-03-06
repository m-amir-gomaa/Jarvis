# Jarvis Standardized Learning Process

This document outlines the standardized, assisted process for Jarvis to learn a new programming language or tool. This process ensures comprehensive coverage across three knowledge layers: **Core API**, **Official Docs**, and **Theoretical Deep-Dives**.

## The 3-Layer Knowledge System

Jarvis organizes knowledge into three layers to balance execution speed and reasoning depth:

1.  **Layer 1: Core API & Syntax (`_core`)**
    -   Basic syntax, built-in functions, and fundamental paradigms.
    -   Used for quick coding assistance and syntax correction.
2.  **Layer 2: Official Documentation (`_docs`)**
    -   Standard library references, official guides, and best practices.
    -   Used for more complex architectural decisions and library usage.
3.  **Layer 3: Theoretical Deep-Dives & Books (`_theory`)**
    -   Highly-praised books, research papers, and forum-recommended materials.
    -   Used for deep reasoning, optimization, and complex problem-solving.

---

## The Assisted Learning Workflow

The process is designed to be **autonomous yet interactive**, ensuring Jarvis gathers high-quality data while always checking with you before taking significant actions.

### 1. Initiation
Trigger the process with a natural language command:
```bash
jarvis 'learn the Zig programming language'
```

### 2. Documentation Discovery
Jarvis searches for official documentation and high-quality starters.
-   **Action**: Searches SearXNG for "official [language] docs".
-   **Confirmation**: Jarvis will present the found URLs and ask: *"I found these documentation sites. Should I start scraping the official one?"*

### 3. Core & Doc Scraping (Layer 1 & 2)
Jarvis uses `doc_learner.py` to ingest the official site.
-   **Extraction**: It automatically pulls paragraphs, lists, and headers.
-   **Recommendation Engine**: While scraping, it identifies mentions of "books", "guides", or "deep dives" and adds them to your **Inbox**.

### 4. Forum & Community Research
To find the most "highly-praised" resources, Jarvis consults community forums.
-   **Action**: Searches Reddit, StackOverflow, and specialized forums (e.g., "best books for learning Zig reddit").
-   **Synthesis**: The Research Agent summarizes these findings and identifies specific materials (PDFs, eBooks, specific chapters).

### 5. The Inbox & Confirmation
Discovered resources that cannot be automatically scraped (like books or paywalled deep-dives) are placed in the **Inbox**.
-   **Check**: Run `jarvis inbox` to see pending materials.
-   **Decision**: You confirm which materials you have acquired or want Jarvis to focus on.

### 6. Material Ingestion (Layer 3)
Once you have the materials (e.g., a PDF of a recommended book):
-   **Action**: Place the file in `~/Downloads/JarvisMaterials`.
-   **Ingestion**: Jarvis detects the file, converts it to Markdown (using MinerU or Pandoc), and indexes it into **Layer 3**.

---

## Commands Summary

| Command | Purpose |
| :--- | :--- |
| `jarvis 'learn [topic]'` | Starts the assisted learning process. |
| `jarvis inbox` | Lists recommended books and guides found during research. |
| `jarvis knowledge summary` | Shows which languages/layers are currently trained. |
| `jarvis training` | Provides a detailed matrix of language competency. |

---

## Best Practices
-   **Confirm URLs**: Always double-check that Jarvis found the *official* documentation.
-   **Provide PDFs**: For Layer 3, high-quality PDFs are preferred over raw text for better structure conversion.
-   **Use Thumbs Up/Down**: Give feedback after Jarvis uses its new knowledge to help it refine its retrieval strategies.
