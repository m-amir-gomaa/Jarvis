# Jarvis: Creative Uses & Coding Excellence

Jarvis isn't just a chatbot; it's a system-integrated orchestrator. This guide explores where Jarvis shines in your daily workflow and some creative ways to leverage its power.

---

## 🚀 Where Jarvis Shines in Coding

### 1. Refactoring with Least Privilege
Unlike "Copilot" style tools that might overwrite your whole file, Jarvis excels at surgical refactors.
- **The Edge**: Jarvis can analyze your entire codebase (via Layer 2 indexing) to ensure a rename in `utils.py` doesn't break a hidden dependency in a Nix flake.
- **Usage**: Select a block in Neovim and use `<leader>jr` to refactor with specific constraints.

### 2. Debugging Complex NixOS Build Failures
Nix errors are notoriously opaque. Jarvis has specialized knowledge of the Nix store and flake structures.
- **The Edge**: It doesn't just guess; it can use `file_read` capabilities to inspect your `configuration.nix` and `hardware-configuration.nix` simultaneously to find hardware/software mismatches.
- **Usage**: `jarvis 'validate my nixos config'`

### 3. Automated Documentation & "Living" Wikis
Jarvis can act as a technical writer who actually understands the code.
- **The Edge**: It uses Layer 3 (Theoretical) knowledge to explain *why* a design pattern was used, not just *what* the code does. It then commits these docs directly to your repo.
- **Usage**: `jarvis 'document the security subsystem architecture'`

---

## 🎨 Creative System Uses

### 1. The "Daily Intelligence" Briefing
Set up a systemd timer (see `docs/INSTALL.md`) to have Jarvis run every morning.
- **What it does**: It scans your git logs, your `inbox/` reading list, and your calendar to generate a "Focus Report."
- **Creative Twist**: Have it output to a `MOTD` (Message of the Day) file so you see your AI-prioritized task list every time you open a terminal.

### 2. Autonomous Log Auditor
Running a server? Have Jarvis watch your system logs in the background.
- **What it does**: It can detect anomalous patterns that traditional `fail2ban` might miss, like a slow-brute-force attack or a leaking memory trend in a custom service.
- **Action**: It can trigger an ERS chain to temporarily isolate a service or notify you via a TUI event.

### 3. "Code Janitor" Mode
Schedule Jarvis to run a weekly cleanup.
- **What it does**: It finds unused imports, identifies functions that have grown too complex (high cyclomatic complexity), and suggests modularization strategies.
- **Creative Twist**: It can automatically create "Clean-up" branches in Git and assign them to you for review.

### 4. Interactive Kernel Optimization
On NixOS, Jarvis can suggest kernel tweaks based on your current workload.
- **What it does**: If it detects you're doing heavy LLM inference, it can suggest (or apply with approval) temporary I/O scheduling changes or RAM priority tweaks.
- **Usage**: `jarvis 'optimize system for heavy inference'`

---

## 🛠️ How to Experiment

The best way to find new uses is to look at the **ERS Chains** in `chains/`. 
- **Want to automate something new?** Create a `.yaml` file that combines `shell_exec` and `file_read`. 
- **Example**: A "Dependency Auditor" chain that checks for outdated libraries and reads their changelogs to see if an update is breaking.

Jarvis is a tool that grows with your imagination. If you can describe a logic-driven task, Jarvis can build a chain for it.
