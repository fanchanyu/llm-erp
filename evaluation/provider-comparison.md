# LLM-ERP Multi-Provider Comparison

## Overview

| Metric | DeepSeek (cloud) | Gemma4 (local, 8B CPU) |
|--------|:-:|:-:|
| **Overall Accuracy** | 27/30 (90.0%) | **28/30 (93.3%)** |
| **Avg Response Time** | **7.7s** | 8.7s |
| **Cost per query** | ~$0.002 | Free |
| **Data sovereignty** | External API | Fully local |
| **Model size** | Unknown (proprietary) | 8B Q4_K_M (9.6GB) |

## Per-Category Results

| Category | DeepSeek | Gemma4 |
|----------|:--------:|:------:|
| Inventory | 4/5 (80%) | **5/5 (100%)** |
| Purchase | 4/5 (80%) | **5/5 (100%)** |
| BOM | **4/4 (100%)** | 3/4 (75%) |
| Dispatch | 5/5 (100%) | 5/5 (100%) |
| Quality | 4/4 (100%) | 4/4 (100%) |
| Accounting | 5/5 (100%) | 5/5 (100%) |
| Cross-module | 1/2 (50%) | 1/2 (50%) |

## Key Observations

1. **Gemma4 outperformed DeepSeek** on Inventory and Purchase queries — both modules require Chinese keyword matching and simple data retrieval, which Gemma4 handles well.

2. **DeepSeek outperformed Gemma4** on BOM queries — BOM involves multi-level recursive tree operations (explosion, shortage detection), where the larger DeepSeek model demonstrated better reasoning capability.

3. **Intent classification variance**: Gemma4 had 9 intent mismatches vs DeepSeek's 3. However, Gemma4's mismatches often still produced correct data (validation passed), suggesting the model defaults to nearby tools rather than the exact intended one but still retrieves the right information.

4. **Response time**: Gemma4 on CPU (8.7s average) is only 1s slower than DeepSeek's cloud API (7.7s). For a local 8B model running on CPU without GPU acceleration, this is acceptable. With GPU, latency would drop to ~1-3s.

5. **Reliability**: DeepSeek had 3 failed cases (data missing/wrong intent). Gemma4 had 2 failed cases — both were intent classification errors rather than data retrieval failures, suggesting function-calling prompt improvements could further boost accuracy.

## Conclusion

The multi-provider comparison demonstrates that:
- **Cloud LLMs** (DeepSeek) offer better reasoning for complex multi-step queries (BOM explosion)
- **Local LLMs** (Gemma4) are competitive on routine operational queries (inventory, purchase) and provide data sovereignty benefits
- Both providers achieve >90% accuracy, indicating the architecture is provider-agnostic
- A hybrid approach — cloud for complex reasoning, local for routine operations — could optimize both accuracy and cost
