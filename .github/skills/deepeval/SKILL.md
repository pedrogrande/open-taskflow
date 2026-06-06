---
name: deepeval
description: DeepEval evaluation framework for RAG pipeline metrics. Use when writing or running evaluation tests, implementing metric collection, or working with DeepEval test cases and assertions. Covers Contextual Recall, Contextual Precision, Faithfulness, and other retrieval/generation metrics.
---

# DeepEval Skill

## Overview

DeepEval is the evaluation framework for this RAG Pipeline Evaluation Harness. It provides metrics for retrieval quality, generation quality, and operational performance.

## Key Metrics

### Retrieval Metrics

- **Contextual Recall** — measures whether the retrieved context contains all information needed to answer the query. This is the PRIMARY metric for comparing vector stores.
- **Contextual Precision** — measures whether relevant nodes are ranked higher than irrelevant ones.
- **Contextual Relevance** — measures whether the retrieved context is relevant to the query.

### Generation Metrics

- **Faithfulness** — measures whether the generated answer is faithful to the retrieved context.
- **Answer Relevance** — measures whether the generated answer is relevant to the query.

### Operational Metrics

- **Latency** — tracked via timers, not a DeepEval metric per se.
- **Cost** — tracked via OpenAI API usage, not a DeepEval metric.

## Usage Patterns

### Test Case Structure

```python
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.metrics import ContextualRecallMetric

test_case = LLMTestCase(
    input="What is the main contribution of this paper?",
    actual_output="The paper proposes...",
    expected_output="The main contribution is...",
    retrieval_context=["chunk1 text", "chunk2 text"],
)

metric = ContextualRecallMetric()
result = metric.measure(test_case)
```

### Running Evaluations

```bash
# Run all tests
deepeval test run test_file.py

# Run with specific metrics
deepeval test run test_file.py --metrics contextual_recall

# Run a specific test
deepeval test run test_file.py::test_function_name
```

### Integration with Pytest

```python
import pytest
from deepeval import assert_test
from deepeval.metrics import ContextualRecallMetric

@pytest.mark.parametrize("query,expected", test_data)
def test_retrieval_quality(query, expected):
    test_case = LLMTestCase(input=query, ...)
    assert_test(test_case, [ContextualRecallMetric()])
```

## Important Notes

- DeepEval uses OpenAI API for LLM-based metrics. Ensure `OPENAI_API_KEY` is set in `.env`.
- Contextual Recall is the PRIMARY comparison metric across experiment phases.
- All evaluation results must be stored in SurrealDB for reproducibility.
- Use `deepeval test run` for CLI execution, not raw pytest.
