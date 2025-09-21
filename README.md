# xtgen

A modern, type-safe Python package for generating skeleton PureData and Max/MSP external files from YAML or JSON specifications.

## Features

- **Python package** with CLI entry point and library interface
- **Command-line interface** with comprehensive options and validation
- **Generate PureData external projects** with complete build system
- **Generate Max/MSP external projects** with proper SDK structure
- **Template-based code generation** using Mako templates
- **Type-safe specification parsing** (YAML and JSON formats)
- **Automatic format detection** with intelligent fallback
- **Validation mode** to check specifications without generating
- **Comprehensive test coverage** (38 tests)
- **Support for both regular and DSP** (signal processing) externals
- **Bundled resources** (templates, examples, headers included in package)

## Installation

### From Source

Clone this repository and install with uv:

```sh
git clone <repository-url>
cd xtgen
uv sync
```

### From Wheel

Build and install the package:

```sh
uv build
pip install dist/xtgen-*.whl
```

### Dependencies

The package requires:
- Python 3.13+
- Mako (templating engine)
- PyYAML (YAML parsing)

## Usage

### Command Line Interface

The easiest way to use xtgen is through its command-line interface:

```sh
usage: xtgen [-h] [-t {pd,max}] [-o DIR] [-v] [-q] [-f] [--list-examples]
             [--validate]
             [spec_file]

Generate PureData and Max/MSP external projects from YAML or JSON specifications

positional arguments:
  spec_file             Path to YAML or JSON specification file (default: counter.yml from examples)

options:
  -h, --help            show this help message and exit
  -t, --target {pd,max}
                        Target platform: 'pd' for PureData, 'max' for Max/MSP
                        (default: pd)
  -o, --output DIR      Output directory for generated projects (default: build)
  -v, --verbose         Enable verbose output with detailed generation information
  -q, --quiet           Suppress all output except errors
  -f, --force           Force overwrite existing project directory without warning
  --list-examples       List available example specification files and exit
  --validate            Validate specification file without generating project

Examples:
  xtgen counter.yml                    # Generate PD project from YAML
  xtgen counter.json                   # Generate PD project from JSON
  xtgen -t max counter.yml             # Generate Max/MSP project
  xtgen -o /tmp/build counter.yml      # Custom output directory
  xtgen -v counter.yml                 # Verbose output
  xtgen --list-examples                # List available examples

Supported file formats:
  .yml, .yaml  - YAML specification files
  .json        - JSON specification files
```

### Development Usage

When developing locally with uv:

```sh
# Run with default example (generates PD project)
uv run xtgen

# Generate Max/MSP project
uv run xtgen -t max resources/examples/counter.json

# Use custom output directory
uv run xtgen -o /tmp/my-externals counter.yml

# Verbose output with detailed information
uv run xtgen -v counter.yml

# Validate specification without generating
uv run xtgen --validate counter.yml

# List available example files
uv run xtgen --list-examples
```

### Installed Package Usage

When xtgen is installed as a package:

```sh
# Generate PureData project (default behavior)
python -m xtgen resources/examples/counter.yml

# Generate Max/MSP project
python -m xtgen -t max resources/examples/counter.json

# Use custom output directory
python -m xtgen -o /tmp/my-externals counter.yml
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
from pathlib import Path

# Generate PureData project from your own specification
project = PdProject('my_external.yml')
project.generate()

# Generate Max/MSP project
project = MaxProject('my_external.json')
project.generate()

# Generate with custom output directory
project = PdProject('spec.yml', target_dir='custom_output')
project.generate()
```

### Project Compilation

Generated projects are ready to compile:

```sh
# For PureData projects
make -C build/counter

# For Max/MSP projects (requires Max SDK)
# Follow Max SDK build instructions
```

## Development

### Running Tests

```sh
uv run pytest tests/ -v
```

### Type Checking

```sh
uv run mypy src/xtgen/
```

### Linting and Formatting

```sh
uv run ruff check src/xtgen/
uv run ruff format src/xtgen/
```

### Quick Development Tasks

Use the Makefile for common development tasks:

```sh
make demo        # Generate demo project in build/demo_output/
make test        # Run test suite
make clean       # Clean build artifacts
make help        # Show available targets
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

- [x] xtgen to become a python package
- [ ] Hybrid dual Max/PD template
- [ ] Additional DSP utility functions
- [ ] Extended help file generation for PureData
- [ ] Plugin packaging and distribution tools
