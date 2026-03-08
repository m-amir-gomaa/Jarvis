# How to Read the Jarvis Documentation

Jarvis is a complex system with a multi-layered documentation suite. This meta-guide helps you navigate the resources based on your current goal.

---

## 🚦 Choose Your Path

### 1. "I just want to get it running"
Start with the **[Installation Guide](INSTALL.md)**. 
- **Focus**: Prerequisites, NixOS configuration, and the initial `jarvis start`.
- **Next Step**: The **[API Key Guide](API_KEYS.md)** to connect your models.

### 2. "I'm a developer but new to AI"
Start with the **[AI Terminology Guide](AI_TERMINOLOGY.md)**.
- **Focus**: Understanding the "why" behind tokens, embeddings, and RAG without the math.
- **Next Step**: **[Creative Uses](CREATIVE_USES.md)** to see what's possible.

### 3. "I want to master the CLI and IDE"
Head to the **[Usage Guide](USAGE.md)**.
- **Focus**: Command references, Neovim keybindings, and TUI shortcuts.
- **Next Step**: The **[Man Page](jarvis.1)** (run `jarvis man`) for the technical flag reference.

### 4. "I want to contribute or build new features"
Read the **[Developer Guide](DEVELOPER_GUIDE.md)** first.
- **Focus**: Contribution rules, ERS chain tutorials, and AI engineering resources.
- **Next Step**: **[Component Reference](COMPONENTS.md)** for the file-by-file audit.

---

## 🧠 Deep Tech Dives

If you're debugging or refactoring a specific subsystem, use these:

- **Security & Permissions**: **[Architecture Guide](ARCHITECTURE.md)** (Sections 2A & 3).
- **Deep Dive**: **[Technical Internals](DEEP_DIVE.md)** (Low-level audit).
- **RAG & Search**: **[Knowledge Base & RAG](KNOWLEDGE_BASE.md)**.
- **Model Selection**: **[Model Overview](MODELS_OVERVIEW.md)**.
- **Porting**: **[Porting & Decoupling](PORTING_GUIDE.md)** if using Windows or non-Nix Linux.

---

## 🛠️ Documentation Standards

- **Basenames**: Links always use file basenames for clarity.
- **Version Control**: Documentation is versioned with the code. If you see `(V3)`, it matches the current stable reasoning engine.
- **Feedback**: If a guide is unclear, open an issue or ask Jarvis: `jarvis 'how do I [task]?'`.

---
*Tip: When in doubt, start with the root [README](../README.md).*
