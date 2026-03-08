# Jarvis Developer Guide (V3)

Welcome to the Jarvis development community. This guide will help you understand the codebase, contribute new features, and master AI engineering. For a high-level overview of how systems interact, see the **[Architecture Guide](ARCHITECTURE.md)**.

## 1. Contribution Rules

To maintain the quality and security of Jarvis, all contributions must follow these rules:

### Security First
- Never bypass the `SecurityContext`.
- Always request the minimum capability required for a task.
- Ensure all new intents in `jarvis.py` use `_enforce_capability`.

### Testing & Quality
- **Lints**: Run `make lint` before committing.
- **Tests**: All new features must include integration tests in the `tests/` directory.
- **Validation**: `make test-all` must pass on your local NixOS machine.

### Documentation
- Ensure all new components are documented in `docs/COMPONENTS.md`.
- Read the **[AI Terminology Guide](AI_TERMINOLOGY.md)** to understand the core concepts.

## 2. Tutorial: Creating an ERS Chain

ERS chains allow you to define complex reasoning workflows in YAML.

1. **Define the Chain**: Create `chains/my_new_task.yaml`.
2. **Add Steps**: Define sequential or parallel steps with Jinja2 prompts.
3. **Specify Capabilities**: List required capabilities for each step.
4. **Route the Intent**: Add a new match in `jarvis.py:classify_intent` and `route_intent`.

Example Step:
```yaml
- name: analyze_logs
  model: coder
  prompt: "Analyze these logs: {{ input }}"
  capabilities: ["file_read"]
```

## 3. Safe Refactoring with Speculative Execution

For high-risk code changes, use the Speculative Execution pipeline to ensure zero-risk deployments. For the technical deep-dive, see **[Speculative Execution](SPECULATIVE_EXECUTION.md)**.

### Running a Speculative Refactor
Developers should use the `run_speculative` utility in `pipelines/speculative_refactor.py` when automating structural changes.

```python
from pipelines.speculative_refactor import run_speculative

def my_risky_change():
    # perform file edits here
    return True

success = run_speculative(
    task_name="major_rename",
    refactor_func=my_risky_change,
    test_cmd="pytest tests/test_core.py"
)
```

**Workflow Safety**:
1. **Never skip `test_cmd`**: Speculative execution is only as strong as your test suite.
2. **Atomic Changes**: Keep refactor functions focused. Large, multi-component changes are harder to debug even with rollback.
3. **Event Monitoring**: Listen for `speculative_refactor:rollback_initiated` on the Event Bus to debug failed attempts.

## 4. AI Engineering Resources

To master AI engineering and contribute effectively to Jarvis, we recommend the following resources. You can also see **[Creative Uses](CREATIVE_USES.md)** for real-world examples of Jarvis in action.

### 🎓 Foundational Learning
- **Andrej Karpathy's "Zero to Hero"**: The gold standard for understanding LLMs from first principles. [YouTube](https://www.youtube.com/@AndrejKarpathy)
- **Umar Jamil**: Excellent paper walkthroughs and PyTorch implementations. [YouTube](https://www.youtube.com/@umarjamil)
- **DeepLearning.AI**: Specialized courses on Prompt Engineering and AI Agents. [Website](https://www.deeplearning.ai/)

### 📚 Essential Reading
- **"Deep Learning" (Goodfellow, Bengio, Courville)**: The theoretical foundation of the field.
- **"Hands-On Machine Learning" (Aurélien Géron)**: Practical guide for building AI systems.
- **Anthropic/OpenAI Documentation**: Best practices for prompt engineering and model usage.

### 🌐 Key Communities & Tools
- **Hugging Face**: The hub for models, datasets, and the `transformers` library.
- **LangChain / LlamaIndex**: Frameworks for building RAG and agentic workflows.
- **arXiv.org**: Stay updated with the latest research papers (CS.CL, CS.AI).

## 4. Getting Help

- Open an issue on GitHub for bugs or feature requests.
- Join our community discussions (if applicable).
- Consult the **[Architecture Guide](ARCHITECTURE.md)** for deep technical questions.
