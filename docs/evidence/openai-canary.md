# OpenAI native canary

2026-10-08 17:28:54 UTC: one real Responses API request using `gpt-4.1-mini-2025-04-14` passed the synthetic commitment task. The shared skill validated the quote, source revision and timestamp. The rubric checked Alice as owner, 2026-10-15 10:00 UTC as due time and an initial active pricing commitment. The same business core then prepared a local proposal and review-required draft. No approvals, CRM writes or email sends occurred.

- Command: `.venv/Scripts/python.exe -m scripts.model_canary --run`
- Model latency: 3345.69 ms; input 417 tokens, output 134 tokens.
- Estimated standard uncached token cost: USD 0.0003812, not a billing receipt. Rates and snapshot verified against the [official model page](https://developers.openai.com/api/docs/models/gpt-4.1-mini): USD 0.40/1M input and USD 1.60/1M output.
- Prompt: extract-v1; schema: extraction-1.0; schema SHA-256: `00c376875a08975947c402e68331ba112533b9f81be54ede443149e891a95ba4`.
- Sanitized synthetic response, source hash and trace retained locally in `local/openai-canary.json`. A persistent exclusive reservation prevents automatic repeats.

N=1 proves this API/profile and synthetic slice worked. It is not a quality benchmark, default-model selection, multi-provider evaluation or connected CRM/mailbox acceptance. App model execution remains disabled in the current local configuration. Claude, Grok, Ollama and Graph access/acceptance remain pending.
