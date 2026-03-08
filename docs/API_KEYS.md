# Jarvis API Key Management Guide

Jarvis is local-first, but it can leverage external LLMs for enhanced reasoning. This guide explains how to obtain API keys and securely store them in the Jarvis Vault.

## 1. Obtaining API Keys

### Anthropic (Claude 3.5 Sonnet / Opus)
- **Use Case**: Highest quality reasoning and coding.
- **How to Obtain**:
    1. Go to the [Anthropic Console](https://console.anthropic.com/).
    2. Create an account and add credits.
    3. Navigate to **Get API Keys**.
    4. Create a new key and copy it immediately.

### OpenAI (GPT-4o / o1)
- **Use Case**: Versatile performance and fast responses.
- **How to Obtain**:
    1. Visit the [OpenAI Platform](https://platform.openai.com/).
    2. Create an account and set up billing.
    3. Go to **API Keys** in the dashboard.
    4. Click **Create new secret key**.

### DeepSeek (DeepSeek-V3 / Coder)
- **Use Case**: High-performance, low-cost alternative.
- **How to Obtain**:
    1. Go to the [DeepSeek Platform](https://platform.deepseek.com/).
    2. Register and top up your balance.
    3. Navigate to **API Keys** and generate a new one.

### Groq (Llama 3 / Mixtral)
- **Use Case**: Blazing fast inference speeds.
- **How to Obtain**:
    1. Visit the [Groq Cloud](https://console.groq.com/).
    2. Sign up (currently provides a tiered free quota).
    3. Go to **API Keys** and create a key.

### Google Gemini (Gemini 1.5 Pro / Flash)
- **Use Case**: Large context window (up to 2M tokens) and multimodal tasks.
- **How to Obtain**:
    1. Sign in to [Google AI Studio](https://aistudio.google.com/).
    2. Create a new API Key in the sidebar.
- **Credit Card**: **NOT REQUIRED** for the free tier.

### OpenRouter (Aggregator)
- **Use Case**: Unified API to access hundreds of models (Claude, GPT, Llama, etc.).
- **How to Obtain**:
    1. Visit [OpenRouter.ai](https://openrouter.ai/).
    2. Sign up and browse for "free" models (many are 0 cost).
- **Credit Card**: **NOT REQUIRED** to access free models or use a pre-paid balance.

### Cerebras (Llama 3.1 70B/8B)
- **Use Case**: Extreme low-latency (Llama 3.1 70B at ~450 tokens/sec).
- **How to Obtain**:
    1. Visit [Cerebras Cloud](https://cloud.cerebras.ai/).
    2. Sign up for a free developer account.

---

## 2. Tier Comparison: Free vs. Paid

| Provider | Free Tier (No CC) | Free Trial (With CC) | Quota / Limits |
|----------|-------------------|----------------------|----------------|
| **Google** | Yes (AI Studio) | No | Rate limited (e.g. 15 RPM for 1.5 Pro) |
| **Groq** | Yes | No | Requests Per Minute (RPM) & Tokens Per Day (TPD) |
| **OpenRouter** | Yes (Selected models) | No | Depends on the specific model used |
| **Cerebras** | Yes | No | Generous beta limits |
| **Anthropic** | No | Optional (Free credits) | Requires per-account verification |
| **OpenAI** | No | Optional (Free credits) | Depends on account tier |
| **DeepSeek** | No | No | Pay-as-you-go only (extremely cheap) |

> [!TIP]
> **Privacy Note**: Most free tiers (especially Google AI Studio's free tier) reserve the right to use your data for training. For sensitive code, stick to **Jarvis Local (Ollama)** or paid tiers with explicit Opt-Out.

## 3. Storing Keys Securely

Jarvis does **not** store keys in environment variables or plain text config files. Instead, it uses the `SecretsManager` to store them in the Vault.

### Using the CLI
The easiest way to add a key is via the `jarvis set-key` command:

```bash
# General Syntax
jarvis set-key [PROVIDER] [API_KEY]

# Examples
jarvis set-key anthropic sk-ant-api03-...
jarvis set-key openai sk-...
jarvis set-key deepseek sk-...
jarvis set-key groq gsk_...
```

### Vault Location
Keys are AES-256 encrypted and stored at:
`/THE_VAULT/jarvis/secrets/keyring.db`

Only the Jarvis process (and your user) should have access to the Vault.

## 4. Configuring Usage

Once the keys are set, update your `config/models.toml` to use external providers:

```toml
[aliases]
reason = "external/anthropic/claude-3-5-sonnet-20240620"
fast   = "external/groq/llama-3.1-70b-versatile"
```

Jarvis will automatically enforce the `model:external` capability when these aliases are used.
