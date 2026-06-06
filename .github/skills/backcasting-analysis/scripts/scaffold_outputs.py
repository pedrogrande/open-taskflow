#!/usr/bin/env python3
"""Scaffold output specifications from a CAWDP design spec markdown file.

Extracts output specifications from a design spec (D-P00-001.md style) and
produces a JSON array suitable for the backcasting engine's `run_backcasting`
tool.

Usage:
    python scaffold_outputs.py <design_spec.md> [--output outputs.json]

The script looks for sections matching common CAWDP output patterns:
    - "## Outputs" or "## Output Specifications" sections
    - Tables with ID, Name, Description columns
    - Dependency references (internal: O-XXX, external: named inputs)
    - Quality gate markers (is_quality_gate: true)
    - Final deliverable markers (is_final_deliverable: true)

If the design spec doesn't follow these conventions, the script produces
a template that the user can fill in manually.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def extract_outputs_from_markdown(text: str) -> list[dict]:
    """Extract output specifications from a CAWDP design spec markdown file.

    Looks for structured output sections and tables. Falls back to
    generating a template from any headings that look like outputs.
    """
    outputs: list[dict] = []

    # Pattern 1: Table with ID | Name | Description | ... columns
    # Matches markdown tables like:
    # | O-001 | Market Analysis | Final deliverable | ...
    table_pattern = re.compile(
        r"\|\s*(O-\d+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|",
        re.MULTILINE,
    )

    for match in table_pattern.finditer(text):
        output_id = match.group(1).strip()
        name = match.group(2).strip()
        desc = match.group(3).strip()

        # Skip header rows
        if name.lower() in ("name", "output", "id"):
            continue

        is_final = "final" in desc.lower() or "deliverable" in desc.lower()
        is_gate = "gate" in desc.lower() or "quality" in desc.lower()

        outputs.append(
            {
                "id": output_id,
                "name": name,
                "description": desc,
                "is_final_deliverable": is_final,
                "is_quality_gate": is_gate,
                "quality_gate_references": [],
                "dependencies": [],
            }
        )

    # Pattern 2: Headings that look like output specs
    # ### O-001: Market Analysis
    heading_pattern = re.compile(
        r"###?\s*(O-\d+)\s*[:\-–]\s*(.+)",
        re.MULTILINE,
    )

    existing_ids = {o["id"] for o in outputs}

    for match in heading_pattern.finditer(text):
        output_id = match.group(1).strip()
        name = match.group(2).strip()

        if output_id in existing_ids:
            continue

        outputs.append(
            {
                "id": output_id,
                "name": name,
                "description": "",
                "is_final_deliverable": False,
                "is_quality_gate": False,
                "quality_gate_references": [],
                "dependencies": [],
            }
        )

    # Pattern 3: Dependency references in text
    # "depends on O-002" or "requires Market Data"
    dep_pattern = re.compile(
        r"(?:depends?\s+on|requires?|needs?)\s+`?([^`,.\n]+)`?",
        re.IGNORECASE,
    )

    for output in outputs:
        # Search for dependencies near this output's section
        output_section = _find_section_for(text, output["id"])
        if output_section:
            for dep_match in dep_pattern.finditer(output_section):
                dep_target = dep_match.group(1).strip()
                # Classify: O-XXX is internal, everything else is external
                is_internal = bool(re.match(r"O-\d+", dep_target))
                output["dependencies"].append(
                    {
                        "target_id": dep_target,
                        "type": "internal" if is_internal else "external",
                        "criticality": "MEDIUM",
                        "description": "",
                    }
                )

    # If no structured outputs found, generate a template
    if not outputs:
        outputs = _generate_template(text)

    return outputs


def _find_section_for(text: str, output_id: str) -> str:
    """Find the markdown section that describes a specific output."""
    # Look for a heading containing the output ID
    pattern = re.compile(
        rf"(###?\s*{re.escape(output_id)}[^#\n]*\n)(.*?)(?=\n###?\s*(?:O-\d+|\Z)|\Z)",
        re.DOTALL,
    )
    match = pattern.search(text)
    if match:
        return match.group(2)

    # Fallback: look in the 20 lines after the ID appears
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if output_id in line:
            start = i
            end = min(i + 20, len(lines))
            return "\n".join(lines[start:end])

    return ""


def _generate_template(text: str) -> list[dict]:
    """Generate a template output spec from any markdown file.

    Uses top-level headings as output names and creates a skeleton
    that the user can fill in.
    """
    outputs: list[dict] = []

    # Use ## headings as output candidates
    heading_pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)
    for i, match in enumerate(heading_pattern.finditer(text), 1):
        name = match.group(1).strip()
        # Skip common non-output headings
        skip = {"overview", "introduction", "background", "context", "summary", "references"}
        if name.lower() in skip:
            continue

        output_id = f"O-{i:03d}"
        outputs.append(
            {
                "id": output_id,
                "name": name,
                "description": "TODO: Fill in description",
                "is_final_deliverable": False,
                "is_quality_gate": False,
                "quality_gate_references": [],
                "dependencies": [],
            }
        )

    # If still nothing, create a single placeholder
    if not outputs:
        outputs.append(
            {
                "id": "O-001",
                "name": "TODO: Name this output",
                "description": "TODO: Describe what this output contains",
                "is_final_deliverable": False,
                "is_quality_gate": False,
                "quality_gate_references": [],
                "dependencies": [],
            }
        )

    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scaffold output specifications from a CAWDP design spec",
    )
    parser.add_argument(
        "spec_file",
        type=Path,
        help="Path to the design spec markdown file",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output JSON file (default: stdout)",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation (default: 2)",
    )

    args = parser.parse_args()

    if not args.spec_file.exists():
        print(f"Error: File not found: {args.spec_file}", file=sys.stderr)
        sys.exit(1)

    text = args.spec_file.read_text()
    outputs = extract_outputs_from_markdown(text)

    result = json.dumps(outputs, indent=args.indent)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result)
        print(f"Extracted {len(outputs)} output spec(s) to {args.output}", file=sys.stderr)
    else:
        print(result)


if __name__ == "__main__":
    main()
