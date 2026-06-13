"""
Data format parsers for tprint.
Supports JSON, CSV, YAML, TOML, and Markdown tables.
"""

import csv
import io
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, TextIO, Tuple, Union

import yaml

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]


class ParseError(Exception):
    """Raised when input data cannot be parsed in the detected or specified format."""

    pass


def _normalize_record(record: Dict[str, Any]) -> Dict[str, str]:
    """Convert all values in a record to strings for display."""
    return {k: str(v) if v is not None else "" for k, v in record.items()}


def parse_json(data: str) -> List[Dict[str, str]]:
    """Parse a JSON string into a list of string-keyed records."""
    try:
        parsed = json.loads(data)
    except json.JSONDecodeError as e:
        raise ParseError(f"Invalid JSON: {e}") from e

    if isinstance(parsed, dict):
        # Single dict: wrap in list
        return [_normalize_record(parsed)]
    elif isinstance(parsed, list):
        if not parsed:
            return []
        # If the list contains non-dict items, wrap them
        if isinstance(parsed[0], dict):
            return [_normalize_record(r) for r in parsed]
        else:
            return [{"value": str(item)} for item in parsed]
    else:
        # JSON parsed but isn't a structure
        raise ParseError("JSON did not produce a table-like structure (got a scalar)")


def parse_csv(data: str, delimiter: str = ",") -> List[Dict[str, str]]:
    """Parse a CSV string into a list of dict records."""
    # Quick guard: CSV must have the delimiter in the first line
    first_line = data.strip().split("\n")[0] if data.strip() else ""
    if delimiter not in first_line:
        raise ParseError(f"No '{delimiter}' found in first line — not CSV data")

    try:
        reader = csv.DictReader(io.StringIO(data), delimiter=delimiter)
        records: List[Dict[str, str]] = []
        for row in reader:
            records.append({k.strip(): (v.strip() if v else "") for k, v in row.items()})
        if not records and reader.fieldnames:
            # CSV with headers but no data rows — return empty
            return []
        return records
    except csv.Error as e:
        raise ParseError(f"Invalid CSV: {e}") from e


def parse_yaml(data: str) -> List[Dict[str, str]]:
    """Parse a YAML string into a list of string-keyed records."""
    try:
        parsed = yaml.safe_load(data)
    except yaml.YAMLError as e:
        raise ParseError(f"Invalid YAML: {e}") from e

    if parsed is None:
        return []

    if isinstance(parsed, dict):
        return [_normalize_record(parsed)]
    elif isinstance(parsed, list):
        if not parsed:
            return []
        if isinstance(parsed[0], dict):
            return [_normalize_record(r) for r in parsed]
        else:
            return [{"value": str(item)} for item in parsed]
    else:
        # YAML parsed but isn't a structure — reject to avoid false positives
        raise ParseError("YAML did not produce a table-like structure (got a scalar)")


def parse_toml(data: str) -> List[Dict[str, str]]:
    """Parse a TOML string into a list of string-keyed records."""
    try:
        parsed = tomllib.loads(data)
    except (tomllib.TOMLDecodeError, ValueError) as e:
        raise ParseError(f"Invalid TOML: {e}") from e

    if isinstance(parsed, dict):
        # TOML is always a dict at top level
        # Check if it looks like a table-of-tables
        table_values = [v for v in parsed.values() if isinstance(v, dict)]
        if table_values:
            return [_normalize_record(r) for r in table_values]
        # If there's a single list of dicts under a key, use that
        list_values = [v for v in parsed.values() if isinstance(v, list) and v and isinstance(v[0], dict)]
        if list_values:
            return [_normalize_record(r) for r in list_values[0]]
        # Fall back: treat the whole top-level dict as a single record
        return [_normalize_record(parsed)]

    return []


def parse_markdown_table(data: str) -> List[Dict[str, str]]:
    """Parse a Markdown table into a list of dict records."""
    lines = data.strip().split("\n")
    # Find the first table: lines starting with |
    table_lines = []
    in_table = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            table_lines.append(stripped)
            in_table = True
        elif in_table and not stripped.startswith("|"):
            # Table ended
            break

    if len(table_lines) < 2:
        raise ParseError("Markdown table requires at least a header and separator row")

    # Parse header
    header_line = table_lines[0]
    headers = [h.strip() for h in header_line.strip("|").split("|")]

    # Skip separator row (second line)
    # Parse data rows
    records = []
    for row_line in table_lines[2:]:
        cells = [c.strip() for c in row_line.strip("|").split("|")]
        # Pad with empty strings if needed
        while len(cells) < len(headers):
            cells.append("")
        record = dict(zip(headers, cells[: len(headers)]))
        records.append(record)

    return records


# Detection strategies sorted by priority
DETECTION_ORDER = [
    ("markdown", parse_markdown_table),
    ("json", parse_json),
    ("csv", parse_csv),
    ("yaml", parse_yaml),
    ("toml", parse_toml),
]


def detect_and_parse(data: str) -> Tuple[str, List[Dict[str, str]]]:
    """
    Detect the format of the input data and parse it into records.

    Returns (format_name, records). Raises ParseError if no format matches.
    """
    data_stripped = data.strip()
    if not data_stripped:
        raise ParseError("Empty input — nothing to display")

    errors: Dict[str, str] = {}
    for fmt_name, parser_fn in DETECTION_ORDER:
        try:
            records = parser_fn(data_stripped)
            if records:
                # Sanity check: records should have at least one meaningful key
                keys = list(records[0].keys())
                if keys and all(k.strip() for k in keys):
                    return fmt_name, records
                continue
            # Empty results are acceptable — parser succeeded without error
            return fmt_name, records
        except (ParseError, Exception) as e:
            errors[fmt_name] = str(e)
            continue

    # If we got here, nothing worked
    if errors:
        details = "; ".join(f"{k}: {v}" for k, v in errors.items())
        raise ParseError(f"Could not parse input data as any known format. Attempted: {details}")

    raise ParseError("No parsable data found in input")


def read_input(source: Optional[Union[str, Path, TextIO]] = None) -> str:
    """
    Read input data from a file, stdin, or a string.

    If source is None, read from stdin.
    If source is a Path or string path to a file, read the file.
    If source is a string, return it as-is (treat as raw data).
    """
    if source is None:
        return sys.stdin.read()
    elif isinstance(source, str):
        # Check if it's a file path
        path = Path(source)
        if path.exists() and path.is_file():
            return path.read_text(encoding="utf-8")
        return source
    elif isinstance(source, Path):
        return source.read_text(encoding="utf-8")
    elif hasattr(source, "read"):
        return source.read()
    else:
        return str(source)


def parse_stdin() -> List[Dict[str, str]]:
    """Convenience: read stdin and parse."""
    data = read_input()
    _, records = detect_and_parse(data)
    return records
