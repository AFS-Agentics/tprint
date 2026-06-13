"""
Main CLI entry point and rich table rendering for tprint.
"""

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich import box

from . import __version__
from .parsers import (
    ParseError,
    detect_and_parse,
    parse_csv,
    parse_json,
    parse_markdown_table,
    parse_toml,
    parse_yaml,
    read_input,
)
from .formatters import format_records


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="tprint",
        description="tprint — Terminal Table Printer. "
        "Pipe in structured data (JSON, CSV, YAML, TOML, Markdown) "
        "and render as a beautiful, auto-sized terminal table.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  cat data.json | tprint
  tprint data.csv
  ps aux | tprint --json  (pipe mode: reads stdin, tries --json first)
  cat data.yaml | tprint --sort name
  tprint --cols name,email data.csv
  tprint data.json --watch 5
  tprint data.csv --output table.csv
  tprint data.json --md
  curl -s https://api.example.com/users | tprint --cols id,name,email
        """,
    )

    # Input options
    parser.add_argument(
        "file",
        nargs="?",
        help="Input file (reads from stdin if omitted)",
    )
    parser.add_argument(
        "--json",
        action="store_const",
        dest="input_format",
        const="json",
        help="Force JSON input format",
    )
    parser.add_argument(
        "--csv",
        action="store_const",
        dest="input_format",
        const="csv",
        help="Force CSV input format",
    )
    parser.add_argument(
        "--yaml",
        action="store_const",
        dest="input_format",
        const="yaml",
        help="Force YAML input format",
    )
    parser.add_argument(
        "--toml",
        action="store_const",
        dest="input_format",
        const="toml",
        help="Force TOML input format",
    )
    parser.add_argument(
        "--md",
        "--markdown",
        action="store_const",
        dest="input_format",
        const="markdown",
        help="Force Markdown table input format",
    )

    # Display options
    parser.add_argument(
        "--cols",
        help="Comma-separated list of columns to display",
    )
    parser.add_argument(
        "--sort",
        help="Sort rows by column name (ascending)",
    )
    parser.add_argument(
        "--sort-desc",
        metavar="COLUMN",
        help="Sort rows by column name (descending)",
    )
    parser.add_argument(
        "--search",
        help="Filter rows: show only rows where any cell contains the search string",
    )
    parser.add_argument(
        "--watch",
        type=int,
        metavar="N",
        help="Re-render every N seconds (tail/watch mode)",
    )
    parser.add_argument(
        "--expand",
        action="store_true",
        help="Show full cell contents without truncation",
    )

    # Output options
    parser.add_argument(
        "--output",
        help="Write output to file instead of stdout",
    )
    parser.add_argument(
        "--out-format",
        choices=["json", "csv", "md", "yaml"],
        help="Output format override (e.g., --out-format json renders as JSON)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable color output (forces plain text)",
    )

    # Info
    parser.add_argument(
        "--version",
        action="version",
        version=f"tprint v{__version__}",
    )

    return parser


def _parse_with_format(
    data: str, fmt: Optional[str] = None
) -> Tuple[str, List[Dict[str, str]]]:
    """Parse data with optional format override."""
    if fmt:
        parsers = {
            "json": parse_json,
            "csv": parse_csv,
            "yaml": parse_yaml,
            "toml": parse_toml,
            "markdown": parse_markdown_table,
        }
        parser_fn = parsers.get(fmt)
        if parser_fn is None:
            raise ParseError(f"Unknown input format: {fmt}")
        records = parser_fn(data)
        return fmt, records
    return detect_and_parse(data)


def filter_records(
    records: List[Dict[str, str]], cols: Optional[List[str]] = None, search: Optional[str] = None
) -> List[Dict[str, str]]:
    """Filter records by columns and search string."""
    result = records

    # Filter by search string
    if search:
        search_lower = search.lower()
        result = [
            r
            for r in result
            if any(search_lower in v.lower() for v in r.values())
        ]

    # Filter by columns
    if cols:
        result = [
            {k: r.get(k, "") for k in cols if k in r}
            for r in result
        ]

    return result


def sort_records(
    records: List[Dict[str, str]], sort_col: Optional[str] = None, desc: bool = False
) -> List[Dict[str, str]]:
    """Sort records by a column."""
    if not sort_col:
        return records

    # Case-insensitive sort with fallback
    def sort_key(r: Dict[str, str]) -> str:
        return r.get(sort_col, "").lower()

    try:
        return sorted(records, key=sort_key, reverse=desc)
    except Exception:
        return records


def render_table(
    records: List[Dict[str, str]],
    expand: bool = False,
    no_color: bool = False,
) -> str:
    """
    Render records as a rich terminal table and return the rendered string.

    Args:
        records: List of dict records to display.
        expand: If True, show full cell contents (no max_width truncation).
        no_color: If True, render without color/formatting.

    Returns:
        The rendered table as a plain string (without control characters if no_color).
    """
    if not records:
        console = Console(force_terminal=not no_color, no_color=no_color)
        with console.capture() as capture:
            console.print("[yellow](empty result set)[/yellow]")
        return capture.get()

    headers = list(records[0].keys())

    # When expand is True, use a very wide console to avoid truncation
    expand_width = 9999 if expand else None

    table = Table(
        box=box.HEAVY_HEAD if not no_color else box.ASCII2,
        show_header=True,
        header_style="bold cyan" if not no_color else "",
        title_justify="left",
        collapse_padding=False,
        pad_edge=True,
    )

    # Add columns
    for header in headers:
        table.add_column(
            header,
            header_style="bold cyan" if not no_color else "",
            style="",
            no_wrap=expand,
            max_width=None,
            overflow="ignore" if expand else "fold",
            min_width=4,
        )

    # Add rows
    for record in records:
        row = [record.get(h, "") for h in headers]
        table.add_row(*row)

    console = Console(force_terminal=not no_color, no_color=no_color, width=expand_width)
    with console.capture() as capture:
        console.print(table)

    result = capture.get()

    # When no_color is set, strip ANSI codes if any leaked through
    if no_color:
        import re as _re

        result = _re.sub(r"\x1b\[[0-9;]*m", "", result)

    return result


def strip_markup(text: str) -> str:
    """Strip rich/ANSI markup tags from text."""
    import re
    return re.sub(r'\[/?\w+\]', '', text)


def write_output(content: str, output_path: Optional[str] = None, no_color: bool = False) -> None:
    """Write content to stdout or a file."""
    if no_color:
        content = strip_markup(content)
    if output_path:
        Path(output_path).write_text(content, encoding="utf-8")
    else:
        sys.stdout.write(content)
        # Ensure trailing newline
        if not content.endswith("\n"):
            sys.stdout.write("\n")
        sys.stdout.flush()


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    Main entry point.

    Returns:
        Exit code (0 for success, 1 for errors).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        # Read input
        if args.file:
            path = Path(args.file)
            if path.exists():
                data = path.read_text(encoding="utf-8")
            else:
                # Check if it looks like a path (has slashes, extension, etc.)
                # Otherwise treat as raw data string
                if "/" in args.file or "\\" in args.file or args.file.endswith((".json", ".csv", ".yaml", ".yml", ".toml", ".md")):
                    write_output(f"[red]File not found:[/red] {args.file}\n", args.output, no_color=args.no_color)
                    return 1
                data = args.file
        else:
            # Read from stdin
            data = read_input()

        if not data.strip():
            write_output("[yellow]No input data provided.[/yellow]\n", args.output, no_color=args.no_color)
            return 1

        # Parse
        detected_format, records = _parse_with_format(data, args.input_format)

        # Apply column filter
        cols = None
        if args.cols:
            cols = [c.strip() for c in args.cols.split(",")]

        # Apply search filter
        if args.search:
            records = filter_records(records, cols=None, search=args.search)
            # If cols is also set, apply it after search
            if cols:
                records = filter_records(records, cols=cols)

        elif cols:
            records = filter_records(records, cols=cols)

        # Apply sort
        if args.sort:
            records = sort_records(records, args.sort, desc=False)
        elif args.sort_desc:
            records = sort_records(records, args.sort_desc, desc=True)

        # Watch mode
        if args.watch and args.watch > 0:
            return _watch_loop(
                data_source=args.file or data,
                input_format=args.input_format,
                cols=cols,
                sort_col=args.sort or args.sort_desc,
                sort_desc=bool(args.sort_desc),
                search_term=args.search,
                expand=args.expand,
                no_color=args.no_color,
                output_path=args.output,
                out_format=args.out_format,
                interval=args.watch,
                is_file=bool(args.file),
            )

        # Output format override
        if args.out_format:
            output = format_records(records, args.out_format)
            write_output(output, args.output)
            return 0

        # Render table
        output = render_table(records, expand=args.expand, no_color=args.no_color)
        write_output(output, args.output)
        return 0

    except ParseError as e:
        write_output(f"[red]Parse error:[/red] {e}\n", args.output, no_color=args.no_color)
        return 1
    except FileNotFoundError as e:
        write_output(f"[red]File not found:[/red] {e}\n", args.output, no_color=args.no_color)
        return 1
    except KeyboardInterrupt:
        write_output("\n", None)
        return 130
    except Exception as e:
        write_output(f"[red]Error:[/red] {e}\n", args.output, no_color=args.no_color)
        if os.environ.get("TPRINT_DEBUG"):
            import traceback

            traceback.print_exc()
        return 1


def _watch_loop(
    data_source: str,
    input_format: Optional[str],
    cols: Optional[List[str]],
    sort_col: Optional[str],
    sort_desc: bool,
    search_term: Optional[str],
    expand: bool,
    no_color: bool,
    output_path: Optional[str],
    out_format: Optional[str],
    interval: int,
    is_file: bool,
) -> int:
    """Watch mode: re-read input and re-render every N seconds."""
    import time

    try:
        while True:
            # Re-read data
            if is_file:
                try:
                    data = Path(data_source).read_text(encoding="utf-8")
                except FileNotFoundError:
                    write_output(
                        f"[red]File '{data_source}' not found (removed?)[/red]\n",
                        output_path,
                    )
                    return 1
            else:
                data = data_source

            # Parse
            try:
                _, records = _parse_with_format(data, input_format)
            except ParseError as e:
                write_output(f"[red]Parse error:[/red] {e}\n", output_path)
                time.sleep(interval)
                continue

            # Apply filters
            if search_term:
                records = filter_records(records, cols=None, search=search_term)
                if cols:
                    records = filter_records(records, cols=cols)
            elif cols:
                records = filter_records(records, cols=cols)

            if sort_col:
                records = sort_records(records, sort_col, desc=sort_desc)

            # Render
            if out_format:
                output = format_records(records, out_format)
            else:
                output = render_table(records, expand=expand, no_color=no_color)

            # Clear terminal and print
            sys.stdout.write("\033[2J\033[H")  # Clear screen + move cursor home
            sys.stdout.write(output)
            sys.stdout.flush()

            time.sleep(interval)
    except KeyboardInterrupt:
        return 0


def run() -> None:
    """Entry point for console_scripts."""
    sys.exit(main())
