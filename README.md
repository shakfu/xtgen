# xtgen

A tool to generate skeleton PureData and Max/MSP external files from YAML or JSON specifications.

## Features

- **Command-line interface** with comprehensive options and validation
- **Generate PureData external projects** with complete build system
- **Generate Max/MSP external projects** with proper SDK structure
- **Template-based code generation** using Mako templates
- **Type-safe specification parsing** (YAML and JSON formats)
- **Automatic format detection** with intelligent fallback
- **Validation mode** to check specifications without generating
- **Comprehensive test coverage** (35 tests)
- **Support for both regular and DSP** (signal processing) externals

## Installation

This project uses uv for dependency management. Install dependencies with:

```bash
uv sync
```

Or install manually with pip:

```bash
pip install mako pyyaml
```

## Usage

### Command Line Interface

The easiest way to use xtgen is through its command-line interface:

```bash
# Generate PureData project (default behavior)
uv run python xtgen.py resources/examples/counter.yml

# Generate Max/MSP project
uv run python xtgen.py -t max resources/examples/counter.json

# Use custom output directory
uv run python xtgen.py -o /tmp/my-externals counter.yml

# Verbose output with detailed information
uv run python xtgen.py -v counter.yml

# Validate specification without generating
uv run python xtgen.py --validate counter.yml

# List available example files
uv run python xtgen.py --list-examples

# Get help
uv run python xtgen.py --help
```

#### CLI Options

- `-t, --target {pd,max}` - Target platform (default: pd)
- `-o, --output DIR` - Output directory (default: build)
- `-v, --verbose` - Enable verbose output
- `-q, --quiet` - Suppress all output except errors
- `-f, --force` - Force overwrite existing directories
- `--validate` - Validate specification file without generating
- `--list-examples` - List available example files

### Python Library Usage

You can also use xtgen as a Python library:

```python
from xtgen import PdProject, MaxProject

# Generate PureData project
project = PdProject('resources/examples/counter.yml')
project.generate()

# Generate Max/MSP project
project = MaxProject('resources/examples/counter.json')
project.generate()
```

### Project Compilation

Generated projects are ready to compile:

```bash
# For PureData projects
make -C build/counter

# For Max/MSP projects (requires Max SDK)
# Follow Max SDK build instructions
```

## Development

### Running Tests

```bash
uv run pytest tests/ -v
```

### Type Checking

```bash
uv run mypy xtgen.py tests/
```

### Linting and Formatting

```bash
uv run ruff check xtgen.py tests/
uv run ruff format xtgen.py tests/
```

## Specification Format

External specifications can be defined in either YAML or JSON format. Both formats support the same structure and features.

### YAML Format

```yaml
externals:
  - namespace: my
    name: counter
    prefix: ctr
    alias: cntr
    help: help-counter
    n_channels: 1
    params:
      - name: step
        type: float
        min: 0.0
        max: 1.0
        initial: 0.5
        arg: true
        inlet: true
        desc: "step size"
    outlets:
      - name: out
        type: float
    message_methods:
      - name: reset
        params: []
        doc: "reset counter to zero"
    type_methods:
      - type: bang
        doc: "increment counter"
    meta:
      desc: "A simple counter external"
      author: "Your Name"
      repo: "https://github.com/yourname/counter"
      features: ["counting", "resettable"]
```

### JSON Format

```json
{
  "externals": [
    {
      "namespace": "my",
      "name": "counter",
      "prefix": "ctr",
      "alias": "cntr",
      "help": "help-counter",
      "n_channels": 1,
      "params": [
        {
          "name": "step",
          "type": "float",
          "min": 0.0,
          "max": 1.0,
          "initial": 0.5,
          "arg": true,
          "inlet": true,
          "desc": "step size"
        }
      ],
      "outlets": [
        {
          "name": "out",
          "type": "float"
        }
      ],
      "message_methods": [
        {
          "name": "reset",
          "params": [],
          "doc": "reset counter to zero"
        }
      ],
      "type_methods": [
        {
          "type": "bang",
          "doc": "increment counter"
        }
      ],
      "meta": {
        "desc": "A simple counter external",
        "author": "Your Name",
        "repo": "https://github.com/yourname/counter",
        "features": ["counting", "resettable"]
      }
    }
  ]
}
```

### File Format Detection

- Files with `.yml` or `.yaml` extensions are parsed as YAML
- Files with `.json` extension are parsed as JSON
- Files with other extensions (or no extension) are automatically detected by trying YAML first, then JSON
- Both formats produce identical results and support all the same features

## Project Status

### Completed Features

- [x] **Command-line interface** with argparse-based argument parsing
- [x] **Complete specification parsing** (YAML and JSON) with validation
- [x] **PureData external project generation** with build system
- [x] **Max/MSP external project generation** with SDK integration
- [x] **Template-based code generation** system using Mako
- [x] **Support for DSP externals** (signal processing)
- [x] **Comprehensive type system** with validation and error handling
- [x] **Full test coverage** (35 tests including CLI tests)
- [x] **Type safety** with mypy validation
- [x] **Code quality** with ruff linting and formatting
- [x] **Validation mode** for specification checking
- [x] **Automatic format detection** with intelligent fallback
- [x] **Inlet and outlet generation** with proper type mapping
- [x] **Parameter handling** with constructor arguments
- [x] **Message method generation** with argument type checking
- [x] **Type method generation** (bang, float, symbol, list, etc.)
- [x] **Build system integration** (Makefiles for PD, project files for Max)
- [x] **Documentation generation** (README files)

### Future Enhancements

- [ ] Hybrid dual Max/PD template
- [ ] Additional DSP utility functions
- [ ] Extended help file generation for PureData
- [ ] Plugin packaging and distribution tools
