# Proposed bounded local evaluation

User approved this download and bounded native evaluation on 2026-10-10. Runtime/archive checksum and model digest verified;20 real development cases completed, profile failed quality. Server stopped after evaluation; details in ../evidence/phase-6-local-qwen3.json. This explicit approval permits the model download, while Docker/container restrictions remain.

Read-only NVIDIA inventory: RTX4050 Laptop GPU, 6141 MiB total and 5601 MiB free VRAM at observation. Host has about 16 GiB RAM with about 3.73 GiB free in earlier snapshot; other apps remain untouched. This is a feasibility input, not proven model capacity.

Proposed files outside OneDrive: C:/Users/William/.cache/sales-phase6/ollama-v0.40.2 and a dedicated models directory. No PATH change, installer service or startup entry. Standalone CLI release v0.40.2, published 2026-10-08, asset ollama-windows-amd64.zip: 1,468,085,195 bytes; SHA256 e29ad1d5063dd4b54b2492d9b00adab2cff9621bfa654b6c92aa8d6f1fdfe7fc. Source: https://github.com/ollama/ollama/releases/tag/v0.40.2 (GitHub release API checked 2026-10-10).

Candidate qwen3:1.7b Q4_K_M is listed at 1.4GB, manifest prefix 8f68893c685c on https://ollama.com/library/qwen3:1.7b . Approximate total download 2.9GB plus archive extraction storage; reserve 8GB free disk. Capture full local manifest digest before inference, never infer quality from size or marketing. Short published digest is identification only, not a substitute for full content verification.

Runtime proposal: loopback 127.0.0.1:11434, dedicated OLLAMA_MODELS, OLLAMA_NO_CLOUD=1, OLLAMA_NUM_PARALLEL=1, OLLAMA_MAX_LOADED_MODELS=1, OLLAMA_MAX_QUEUE=1. Do not attach to an unknown existing listener. Launch only project-owned native process hidden, retain PID/logs and stop only that process after evaluation. Require at least 4GiB host RAM and 3GiB free VRAM before launch; stop evaluation on memory pressure, unexpected model residency or timeout. Do not close other apps automatically.

One dev case first through shared ModelAdapter, explicit think=false, 4096 context/output bound, temperature0, keep_alive0, no tool execution, no cloud fallback, existing 60s request timeout. Timeout may not immediately unload a running server inference: stop owned process before any next case. Record runtime version/model digest, prompt/schema/dataset hashes, response/usage/latency and real core outputs. Invalid output remains a quality failure. Only expand within resource budget; held-out requires separate local profile freeze and passing development evidence.

Official configuration references checked 2026-10-10: https://docs.ollama.com/windows (standalone archive); https://docs.ollama.com/faq (cloud disable, loopback/concurrency); https://docs.ollama.com/capabilities/thinking (explicit false when supported; verify /api/show). No downloaded source execution or container workaround.
