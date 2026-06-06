---
name: plotly
description: Plotly visualisation patterns for evaluation results. Use when creating charts, graphs, and dashboards for RAG pipeline comparison data, metric distributions, and experiment result visualisations.
---

# Plotly Skill

## Overview

Plotly (with Pandas) is the visualisation layer for this RAG Pipeline Evaluation Harness. It generates interactive charts comparing vector store performance, metric distributions, and experiment results.

## Key Patterns

### Bar Chart — Store Comparison

```python
import plotly.express as px
import pandas as pd

df = pd.DataFrame(results)  # columns: store, metric, score
fig = px.bar(
    df,
    x="store",
    y="score",
    color="metric",
    barmode="group",
    title="Retrieval Quality by Vector Store",
    labels={"score": "Contextual Recall Score", "store": "Vector Store"},
)
fig.update_layout(yaxis_range=[0, 1])
fig.show()
```

### Heatmap — Config Comparison Matrix

```python
fig = px.density_heatmap(
    df,
    x="embedder",
    y="store",
    z="score",
    histfunc="avg",
    title="Average Contextual Recall: Embedder × Store",
    color_continuous_scale="Viridis",
)
fig.show()
```

### Line Chart — Phase Progression

```python
fig = px.line(
    df,
    x="phase",
    y="score",
    color="store",
    markers=True,
    title="Retrieval Quality Across Experiment Phases",
)
fig.show()
```

### Box Plot — Score Distribution

```python
fig = px.box(
    df,
    x="store",
    y="score",
    color="chunker",
    title="Score Distribution by Store and Chunker",
)
fig.show()
```

### Saving Static Exports

```python
# HTML (interactive)
fig.write_html("results/comparison.html")

# Static image (requires kaleido)
fig.write_image("results/comparison.png", width=1200, height=600)
```

## Important Notes

- All visualisations should use consistent colour schemes across stores for comparability.
- Use `barmode="group"` for side-by-side comparisons, not stacked bars.
- Include error bars or confidence intervals where sample sizes allow.
- Save both HTML (interactive) and PNG (static) outputs for the results dashboard.
- The harness stores results in SurrealDB — query results first, then visualise.
