"""
Output formatters for tprint.
Converts records to JSON, CSV, Markdown, or YAML for --json / --csv / --md / --yaml flags.
"""

import csv
import io
import json
from typing import Callable, Dict, List, Optional

import yaml


def format_json(records: List[Dict[str, str]], pretty: bool = True) -> str:
    """Format records as a JSON array."""
    if pretty:
        return json.dumps(records, indent=2, ensure_ascii=False)
    return json.dumps(records, ensure_ascii=False)


def format_csv(records: List[Dict[str, str]], delimiter: str = ",") -> str:
    """Format records as CSV."""
    if not records:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=list(records[0].keys()),
        delimiter=delimiter,
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(records)
    return output.getvalue()


def format_markdown(records: List[Dict[str, str]]) -> str:
    """Format records as a Markdown table."""
    if not records:
        return ""
    headers = list(records[0].keys())
    lines: List[str] = []

    # Header row
    lines.append("| " + " | ".join(headers) + " |")
    # Separator row
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    # Data rows
    for record in records:
        cells = [record.get(h, "") for h in headers]
        lines.append("| " + " | ".join(cells) + " |")

    return "\n".join(lines) + "\n"


def format_yaml(records: List[Dict[str, str]]) -> str:
    """Format records as YAML."""
    return yaml.dump(records, default_flow_style=False, allow_unicode=True, sort_keys=False)


FORMATTERS: Dict[str, Callable[[List[Dict[str, str]]], str]] = {
    "json": format_json,
    "csv": format_csv,
    "md": format_markdown,
    "markdown": format_markdown,
    "yaml": format_yaml,
}


def format_records(records: List[Dict[str, str]], fmt: str) -> str:
    """Format records in the specified output format."""
    formatter = FORMATTERS.get(fmt.lower())
    if formatter is None:
        raise ValueError(
            f"Unknown output format '{fmt}'. "
            f"Supported: {', '.join(sorted(FORMATTERS.keys()))}"
        )
    return formatter(records)
