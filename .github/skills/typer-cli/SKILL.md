---
name: typer-cli
description: Typer CLI framework patterns for building command-line interfaces. Use when implementing CLI commands, adding options/arguments, or testing CLI apps in the evaluation harness.
---

# Typer CLI Skill

## Overview

Typer is the CLI framework for this RAG Pipeline Evaluation Harness. It provides a Python-native way to build CLI commands with automatic help generation and type validation.

## Key Patterns

### Basic App Structure

```python
import typer

app = typer.Typer(help="RAG Pipeline Evaluation Harness")

@app.command()
def run(
    config: str = typer.Option(..., help="Pipeline config ID (e.g. 'extractor:docling:chunker:semantic:embedder:openai_small:store:qdrant')"),
    phase: int = typer.Option(1, help="Experiment phase (1-4)"),
    corpus: str = typer.Option("papers", help="Corpus name"),
):
    """Run an evaluation experiment with the given pipeline configuration."""
    ...
```

### Subcommands with Multiple Apps

```python
app = typer.Typer(help="RAG Pipeline Evaluation Harness")
experiments_app = typer.Typer(help="Experiment management")
results_app = typer.Typer(help="Results and visualisation")

app.add_typer(experiments_app, name="experiment")
app.add_typer(results_app, name="results")

@experiments_app.command("run")
def run_experiment(...): ...

@experiments_app.command("list")
def list_experiments(...): ...

@results_app.command("compare")
def compare_results(...): ...
```

### Enum Choices

```python
from enum import Enum

class StoreType(str, Enum):
    pgvector = "pgvector"
    qdrant = "qdrant"
    surrealdb = "surrealdb"
    lancedb = "lancedb"
    chroma = "chroma"

@app.command()
def benchmark(
    store: StoreType = typer.Option(..., help="Vector store to benchmark"),
):
    ...
```

### Testing CLI Commands

```python
from typer.testing import CliRunner

runner = CliRunner()

def test_run_command():
    result = runner.invoke(app, ["run", "--config", "docling:semantic:openai_small:qdrant", "--phase", "1"])
    assert result.exit_code == 0
```

## Important Notes

- Use `typer.Option` for named parameters and `typer.Argument` for positional ones.
- All CLI commands should have clear help text.
- The harness uses a registry pattern — CLI commands should resolve axis IDs from the registry, not hard-code implementations.
- Use `typer.Exit(code=1)` for error exits, not `sys.exit(1)`.
