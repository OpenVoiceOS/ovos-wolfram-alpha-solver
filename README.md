# ovos-wolfram-alpha-plugin

[![PyPI](https://img.shields.io/pypi/v/ovos-wolfram-alpha-plugin)](https://pypi.org/project/ovos-wolfram-alpha-plugin/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue)](https://www.python.org/)

Wolfram Alpha integration for [OpenVoiceOS](https://openvoiceos.org). Provides a **retrieval engine** for RAG pipelines and an **agent toolbox** for tool-using agents, both as standard OPM plugins.

An [API key](https://products.wolframalpha.com/api/) is required. A demo key is bundled for development but is rate-limited and should not be used in production.

---

## Installation

```bash
pip install ovos-wolfram-alpha-plugin
```

---

## OPM Entry Points

| Entry point | Class | Use case |
|---|---|---|
| `opm.agents.retrieval` — `ovos-wolfram-alpha-solver` | `WolframAlphaRetrievalEngine` | Retrieval — returns `(answer, score)` tuples |
| `opm.agents.toolbox` — `ovos-wolfram-alpha-tools` | `WolframAlphaToolbox` | Agent tool use — exposes `search_wolfram_alpha` |
| `opm.plugin.persona` — `Wolfram Alpha` | `WOLFRAMALPHA_PERSONA` | Ready-made persona using the retrieval engine |

---

## Retrieval Engine

`WolframAlphaRetrievalEngine` implements the `RetrievalEngine` OPM interface. It calls the Wolfram Alpha spoken-answer API and translates non-English queries transparently.

```python
from ovos_wolfram_alpha_plugin import WolframAlphaRetrievalEngine

engine = WolframAlphaRetrievalEngine(config={"appid": "YOUR-KEY"})

# RAG interface: List[Tuple[str, float]]  (answer, score)
passages = engine.query("speed of light", lang="en")

# Spoken answer
print(engine.get_spoken_answer("venus", lang="en"))

# Image result (returns local file path)
print(engine.get_image("mercury", lang="en"))

# Full structured pod results
for pod in engine.get_expanded_answer("elon musk", lang="en"):
    print(pod)
```

### Translation

Non-English queries are translated to English before being sent to Wolfram Alpha, and answers are translated back. The translation plugin is loaded from OPM:

```python
engine = WolframAlphaRetrievalEngine(config={
    "appid": "YOUR-KEY",
    "translate_plugin": "ovos-translate-plugin-server",
})
```

---

## Agent Toolbox

`WolframAlphaToolbox` exposes a `search_wolfram_alpha` tool that any OPM-compatible agent loop (e.g. [ovos-agentic-loop](https://github.com/OpenVoiceOS/ovos-agentic-loop)) can discover and call.

### Loading via persona JSON (recommended)

```json
{
  "name": "Wolfram Alpha",
  "solvers": [
    "ovos-react-loop"
  ],
  "ovos-react-loop": {
    "brain": "ovos-chat-openai-plugin",
    "ovos-chat-openai-plugin": {
      "api_url": "http://localhost:11434/v1/chat/completions"
    },
    "toolboxes": [
      "ovos-wolfram-alpha-tools"
    ]
  }
}
```

### Direct usage

```python
from ovos_wolfram_alpha_plugin import WolframAlphaToolbox, SearchWolframAlphaArgs

tb = WolframAlphaToolbox(config={"appid": "YOUR-KEY"})

tools = tb.discover_tools()
# [AgentTool(name="search_wolfram_alpha", ...)]

output = tb.search_wolfram(SearchWolframAlphaArgs(query="France population", units="metric"))
print(output.result)
```

`WolframAlphaToolbox.WOLFRAMALPHA_PROMPT` contains detailed Wolfram usage guidelines (query formatting, unit notation, assumption handling) intended to be embedded in the agent loop's system prompt by the persona or skill that wires everything together.

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
