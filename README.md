# ovos-wolfram-alpha-plugin

[![PyPI](https://img.shields.io/pypi/v/ovos-wolfram-alpha-plugin)](https://pypi.org/project/ovos-wolfram-alpha-plugin/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue)](https://www.python.org/)

[Wolfram Alpha](https://www.wolframalpha.com/) plugin for [OpenVoiceOS](https://openvoiceos.org). Provides a retrieval engine and agent toolbox built on the Wolfram Alpha API.

---

## Installation

```bash
pip install ovos-wolfram-alpha-plugin
```

An [API key](https://products.wolframalpha.com/api/) is required. A demo key is bundled for development but is rate-limited and should not be used in production.

---

## Configuration

Add to `~/.config/mycroft/mycroft.conf`:

```json
{
  "ovos-wolfram-alpha-plugin": {
    "appid": "YOUR-WOLFRAM-API-KEY",
    "units": "metric"
  }
}
```

### Translation

Non-English queries are translated to English before being sent to Wolfram Alpha, and the answer is translated back. Configure the translation plugin:

```json
{
  "language": {
    "translation_module": "ovos-translate-plugin-server"
  }
}
```

---

## OPM plugins

### Retrieval engine (`opm.agents.retrieval`)

`WolframAlphaRetrievalEngine` implements the `RetrievalEngine` interface for use in OVOS agent pipelines.

```python
from ovos_wolfram_alpha_plugin import WolframAlphaRetrievalEngine

engine = WolframAlphaRetrievalEngine(config={"appid": "YOUR-KEY"})
results = engine.query("speed of light", lang="en")
# [("The speed of light has a value of about 3×10^8 m/s", 0.9)]
```

### Agent toolbox (`opm.agents.toolbox`)

`WolframAlphaToolbox` exposes a `search_wolfram_alpha` tool for LLM agent frameworks.

```python
from ovos_wolfram_alpha_plugin import WolframAlphaToolbox

toolbox = WolframAlphaToolbox(config={"appid": "YOUR-KEY"})
tools = toolbox.discover_tools()
```

### Persona (`opm.plugin.persona`)

A `WOLFRAMALPHA_PERSONA` persona config is registered under the key `Wolfram Alpha`.

---

## Direct API usage

```python
from ovos_wolfram_alpha_plugin import WolframAlphaRetrievalEngine

engine = WolframAlphaRetrievalEngine(config={"appid": "YOUR-KEY"})

# Natural language answer
print(engine.get_spoken_answer("venus", lang="en"))

# Image result path
print(engine.get_image("mercury", lang="en"))

# Full structured results
for pod in engine.get_expanded_answer("elon musk", lang="en"):
    print(pod)
```

---

## Agentic loop integration

Use this plugin with [ovos-agentic-loop](https://github.com/OpenVoiceOS/ovos-agentic-loop) to build a Wolfram Alpha persona that reasons with tools before answering.

### Persona JSON

The `WOLFRAMALPHA_PERSONA` registered by this plugin (`opm.plugin.persona` → `Wolfram Alpha`) uses `ovos-wolfram-alpha-solver` as a plain retrieval solver. For a full agentic persona that can use the toolbox and apply the Wolfram usage guidelines as a system prompt, define a custom persona JSON:

```json
{
  "name": "Wolfram Alpha",
  "solvers": ["ovos-react-loop"],
  "ovos-react-loop": {
    "brain": "ovos-chat-openai-plugin",
    "ovos-chat-openai-plugin": {
      "api_url": "http://localhost:11434/v1/chat/completions"
    },
    "toolboxes": ["ovos-wolfram-alpha-tools"],
    "system_prompt": "You are a Wolfram Alpha assistant. Use the search_wolfram_alpha tool to answer factual, mathematical, and scientific questions. Always send queries to Wolfram in English as concise keywords. Translate answers back to the user's language.",
    "max_iterations": 5
  }
}
```

### Using `WOLFRAMALPHA_PROMPT` as the system prompt

`WolframAlphaToolbox.WOLFRAMALPHA_PROMPT` contains detailed Wolfram usage guidelines (query formatting, unit notation, assumption handling). Pass it directly as the system prompt for best results:

```python
from ovos_agentic_loop.react import ReActLoopEngine
from ovos_wolfram_alpha_plugin import WolframAlphaToolbox

toolbox = WolframAlphaToolbox(config={"appid": "YOUR-KEY"})

engine = ReActLoopEngine({
    "brain": "ovos-chat-openai-plugin",
    "ovos-chat-openai-plugin": {
        "api_url": "http://localhost:11434/v1/chat/completions"
    },
    "system_prompt": WolframAlphaToolbox.WOLFRAMALPHA_PROMPT,
    "max_iterations": 5,
})
engine.load_toolboxes([toolbox])
```

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
