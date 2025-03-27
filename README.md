#  Wolfram Alpha Plugin

```python
from ovos_wolfram_alpha_solver import WolframAlphaSolver

s = WolframAlphaSolver()
print(s.spoken_answer("quem é Elon Musk", lang="pt"))
print(s.spoken_answer("venus", lang="en"))
print(s.spoken_answer("elon musk", lang="en"))
print(s.spoken_answer("mercury", lang="en"))

```
