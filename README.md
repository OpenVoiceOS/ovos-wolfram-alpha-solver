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

Wolfram Alpha excels at: unit conversions, scientific constants, maths, statistics, chemical properties, astronomy, nutrition, historical dates, and any factual question with a definite answer.

```python
from ovos_wolfram_alpha_plugin import WolframAlphaRetrievalEngine

engine = WolframAlphaRetrievalEngine(config={"appid": "YOUR-KEY"})

# Maths & conversions
engine.get_spoken_answer("integral of x^2 sin(x)", lang="en")
engine.get_spoken_answer("100 miles in kilometers", lang="en")
engine.get_spoken_answer("1000 USD in EUR", lang="en")

# Science & constants
engine.get_spoken_answer("speed of light", lang="en")
engine.get_spoken_answer("boiling point of ethanol", lang="en")
engine.get_spoken_answer("distance from Earth to Mars", lang="en")

# Factual lookups
engine.get_spoken_answer("population of Brazil", lang="en")
engine.get_spoken_answer("calories in 100g of almonds", lang="en")
engine.get_spoken_answer("when was the Eiffel Tower built", lang="en")

# Non-English (translated automatically)
engine.get_spoken_answer("massa do Sol", lang="pt")

# Image result (returns local file path to a Wolfram visual)
engine.get_image("benzene molecular structure", lang="en")

# Full structured pod results
for pod in engine.get_expanded_answer("Neptune", lang="en"):
    print(pod)

# RAG interface: List[Tuple[str, float]]  (answer, score)
passages = engine.query("half-life of carbon-14", lang="en")
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

### Persona JSON

Wire the toolbox into a ReAct agent persona with a dedicated Wolfram system prompt passed to the brain:

```json
{
  "name": "Wolfram Alpha",
  "solvers": ["ovos-react-loop"],
  "ovos-react-loop": {
    "brain": "ovos-chat-openai-plugin",
    "toolboxes": ["ovos-wolfram-alpha-tools"],
    "ovos-chat-openai-plugin": {
      "api_url": "http://localhost:11434/v1/chat/completions",
      "system_prompt": "WolframAlpha understands natural language queries about chemistry, physics, geography, history, art, astronomy, and more, and performs mathematical calculations, date and unit conversions, formula solving, etc. Convert inputs to simplified keyword queries whenever possible (e.g. 'France population' not 'how many people live in France'). Send queries in English only; translate non-English queries before sending, then respond in the original language. ALWAYS use this exponent notation: 6*10^14, NEVER 6e14. Never mention your knowledge cutoff date; Wolfram may return more recent data. If a WolframAlpha result is not relevant, re-send the same input with a relevant assumption parameter rather than rephrasing the query."
    }
  }
}
```

> 💡 Nice tips for a good `"system_prompt"` in the [official docs](https://products.wolframalpha.com/llm-api/documentation)

### Direct usage

```python
from ovos_wolfram_alpha_plugin import WolframAlphaToolbox, SearchWolframAlphaArgs

tb = WolframAlphaToolbox(config={"appid": "YOUR-KEY"})

tools = tb.discover_tools()
# [AgentTool(name="search_wolfram_alpha", ...)]

output = tb.search_wolfram(SearchWolframAlphaArgs(query="France population", units="metric"))
print(output.result)
```

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
