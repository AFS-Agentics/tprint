![Cover](cover.png)

# tprint — Terminal Table Printer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)

**tprint** is a CLI tool that pipes in structured data (JSON, CSV, YAML, TOML, Markdown tables) and renders it as a beautiful, colorized, auto-sized terminal table. Think `bat` for tabular data.

![tprint demo](https://raw.githubusercontent.com/AFS-Agentics/tprint/main/docs/demo.gif)

## Features

- 🎨 **Beautiful rendering** — Powered by `rich.Table` with color, alignment, auto-column-width
- 🔍 **Auto-detect format** — Reads JSON, CSV, YAML, TOML, and Markdown tables automatically
- 🎯 **Column selection** — `--cols name,email` shows only the columns you want
- 🔄 **Sorting** — `--sort name` or `--sort-desc age` for ascending/descending sort
- 🔎 **Search/filter** — `--search error` filters rows containing the search term
- 👁️ **Watch mode** — `--watch 5` re-renders every N seconds (like `tail -f`)
- 📤 **Convert formats** — `--out-format json` / `--out-format csv` / `--out-format md` / `--out-format yaml` convert between formats
- 📐 **Expand** — `--expand` shows full cell contents without truncation
- 📁 **Output to file** — `--output file` writes to file instead of stdout
- 🌈 **Color / no-color** — Smart color detection with `--no-color` for scripting

## Installation

### pip (recommended)

```bash
pip install tprint
```

### From source

```bash
git clone https://github.com/AFS-Agentics/tprint.git
cd tprint
pip install -e .
```

### Standalone script

If you don't want to install, you can run directly:

```bash
python -m tprint.cli < data.json
```

Or set up an alias:

```bash
alias tprint='python /path/to/tprint/src/tprint/cli.py'
```

## Usage

### Basic usage

```bash
# Pipe JSON data
cat data.json | tprint

# Read a CSV file directly
tprint data.csv

# Read YAML
tprint data.yaml
```

### Input formats

tprint auto-detects the format of input data. You can also force a specific format:

```bash
# Force JSON parsing
tprint --json data.txt

# Force CSV parsing
cat messy_data | tprint --csv

# Force Markdown table parsing
tprint --md table.md

# Force TOML parsing
tprint --toml config.toml
```

### Column selection

```bash
# Show only specific columns
tprint data.json --cols name,email,role

# Reorder columns
tprint data.csv --cols last_name,first_name,email
```

### Sorting

```bash
# Sort ascending (case-insensitive)
tprint data.json --sort name

# Sort descending
tprint data.csv --sort-desc salary
```

### Filtering

```bash
# Show only rows containing "error"
tprint logs.json --search error

# Case-insensitive search across all columns
tprint data.csv --search "john"
```

### Watch mode (tail -f for tables)

```bash
# Re-render every 5 seconds
tprint data.json --watch 5

# Watch a log file parsed as CSV
tprint --csv --watch 2 <(tail -f app.log)
```

### Format conversion

```bash
# Convert JSON to CSV
tprint data.json --out-format csv

# Convert CSV to Markdown table
tprint data.csv --out-format md

# Convert JSON to YAML
tprint data.json --out-format yaml

# Convert to JSON (pretty-printed)
tprint data.csv --out-format json

# Write to file
tprint data.json --out-format csv --output output.csv
tprint data.json --out-format md --output README_table.md
```

### Full cell content

```bash
# Show all content without truncation
tprint data.json --expand

# Combine with other options
tprint data.json --expand --sort date
```

### No color (for scripting / CI)

```bash
tprint data.json --no-color
tprint data.json --no-color --output result.txt
```

## Examples

### JSON input

```bash
echo '[
  {"name": "Alice", "role": "Engineer", "salary": 95000},
  {"name": "Bob", "role": "Designer", "salary": 82000},
  {"name": "Charlie", "role": "Manager", "salary": 110000}
]' | tprint
```

Output:
```
┏━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
┃ name    ┃ role     ┃ salary ┃
┡━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩
│ Alice   │ Engineer │ 95000  │
│ Bob     │ Designer │ 82000  │
│ Charlie │ Manager  │ 110000 │
└─────────┴──────────┴────────┘
```

### CSV input

```bash
cat << EOF | tprint
Name,Email,Role
Alice Johnson,alice@example.com,Engineer
Bob Smith,bob@example.com,Designer
EOF
```

### YAML input

```bash
cat << EOF | tprint
- name: Server-1
  status: running
  uptime: 45d
- name: Server-2
  status: maintenance
  uptime: 12h
EOF
```

### Markdown table input

```bash
cat << EOF | tprint --md
| Package | Version | Status |
|---------|---------|--------|
| numpy   | 1.24.0  | up-to-date |
| pandas  | 2.0.0   | update available |
| requests| 2.31.0  | up-to-date |
EOF
```

### Real-world pipeline

```bash
# Kubernetes pods
kubectl get pods -o json | jq '.items[] | {name: .metadata.name, status: .status.phase, node: .spec.nodeName}' | tprint --cols name,status,node --sort name

# System processes
ps aux | awk 'NR>1 {print $1","$2","$11}' | tprint --csv --cols user,pid,command --sort-desc pid
```

## API Reference

### Command-line arguments

| Argument | Description |
|----------|-------------|
| `file` | Input file path (reads from stdin if omitted) |
| `--json` | Force JSON input format |
| `--csv` | Force CSV input format |
| `--yaml` | Force YAML input format |
| `--toml` | Force TOML input format |
| `--md`, `--markdown` | Force Markdown table input format |
| `--cols <cols>` | Comma-separated list of columns to display |
| `--sort <col>` | Sort rows by column (ascending) |
| `--sort-desc <col>` | Sort rows by column (descending) |
| `--search <text>` | Show only rows containing the search text |
| `--watch <N>` | Re-render every N seconds (watch mode) |
| `--expand` | Show full cell contents without truncation |
| `--output <file>` | Write output to file instead of stdout |
| `--out-format <fmt>` | Output format: `json`, `csv`, `md`, `yaml` |
| `--no-color` | Disable color output |
| `--version` | Show version and exit |

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error (parse error, file not found, etc.) |
| 130 | Interrupted by Ctrl+C |

### Environment variables

- `TPRINT_DEBUG=1` — Enable debug tracebacks on errors

## Python module usage

```python
from tprint.parsers import detect_and_parse, read_input
from tprint.cli import render_table

# Parse data
data = read_input()  # reads stdin
fmt, records = detect_and_parse(data)

# Filter/sort
from tprint.cli import filter_records, sort_records
records = filter_records(records, cols=["name", "email"], search="alice")
records = sort_records(records, sort_col="name")

# Render
output = render_table(records, expand=True)
print(output)
```

## Development

```bash
# Clone
git clone https://github.com/AFS-Agentics/tprint.git
cd tprint

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run directly
python -m tprint.cli --help
```

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing`)
5. Open a Pull Request

## License

MIT License. See [LICENSE](LICENSE) for details.

## Author

Built by [AFS Agentics](https://github.com/AFS-Agentics).  
Open-source tools for developers, by developers.
