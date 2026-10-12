# xtgen

A modern, type-safe Python package for generating skeleton PureData and Max/MSP externals, CLAP/VST3/AUv2 plugins, and VCV Rack modules from YAML or JSON specifications.

## Features

- **Python package** with CLI entry point and library interface

- **Command-line interface** with comprehensive options and validation

- **Generate PureData external projects** with complete build system

- **Generate Max/MSP external projects** with proper SDK structure

- **Generate CLAP plugins** in C, with a CMake build that also produces VST3, and AUv2 on macOS, via [clap-wrapper](https://github.com/free-audio/clap-wrapper)

- **Generate VCV Rack 2 plugins** with one module, a Makefile, and a blank panel

- **Template-based code generation** using Mako templates

- **Type-safe specification parsing** (YAML and JSON formats)

- **Automatic format detection** with intelligent fallback

- **Validation mode** to check specifications without generating

- **Test suite** of 122 tests, including compile-and-run tests of generated CLAP plugins

- **Support for both regular and DSP** (signal processing) externals

- **Bundled resources** (templates, examples, headers included in package)

See [CHANGELOG.md](CHANGELOG.md) for changes.

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
usage: xtgen [-h] [-t {pd,max,clap,vcv}] [-o DIR] [-v] [-q] [-f]
             [--list-examples] [--validate]
             [spec_file]

Generate PureData, Max/MSP, CLAP/VST3/AU and VCV Rack projects from YAML or JSON specifications

positional arguments:
  spec_file             Path to YAML or JSON specification file (default: counter.yml from examples)

options:
  -h, --help            show this help message and exit
  -t, --target {pd,max,clap,vcv}
                        Target platform: 'pd' (PureData), 'max' (Max/MSP),
                        'clap' (CLAP, wrapped as VST3/AUv2 by CMake), 'vcv'
                        (VCV Rack 2) (default: pd)
  -o, --output DIR      Output directory for generated projects (default: build)
  -v, --verbose         Enable verbose output with detailed generation information
  -q, --quiet           Suppress all output except errors
  -f, --force           Overwrite files in an existing, non-empty project directory
  --list-examples       List available example specification files and exit
  --validate            Validate specification file without generating project

Examples:
  xtgen counter.yml                    # Generate PD project from YAML
  xtgen counter.json                   # Generate PD project from JSON
  xtgen -t max counter.yml             # Generate Max/MSP project
  xtgen -t clap gain.yml               # Generate CLAP project (VST3/AU via CMake)
  xtgen -t vcv gain.yml                # Generate VCV Rack plugin
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

- `-t, --target {pd,max,clap,vcv}` - Target platform (default: pd)

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

# Plugin targets; TARGETS maps CLI names to these classes
from xtgen import ClapProject, VcvProject
ClapProject('gain.yml').generate()
VcvProject('gain.yml').generate()
```

### Project Compilation

Generated projects are ready to compile:

```sh
# For PureData projects
make -C build/counter

# For Max/MSP projects (requires Max SDK)
# Follow Max SDK build instructions

# For CLAP projects: builds .clap and .vst3 (+ .component on macOS).
# The first configure downloads CLAP, clap-wrapper and the VST3/AU SDKs.
cmake -S build/gain -B build/gain/build -DCMAKE_BUILD_TYPE=Release
cmake --build build/gain/build --target gain_all

# For VCV Rack projects (requires the Rack SDK)
make -C build/gain RACK_DIR=/path/to/Rack-SDK
```

## Development

### Running Tests

```sh
uv run pytest tests/ -v
```

The CLAP test compiles each generated plugin and runs it in `tests/clap/host.c`, against CLAP headers vendored in `tests/clap/include`. The VCV build test runs only when `RACK_DIR` points to a Rack SDK.

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

### Plugin Targets

`clap` and `vcv` read a subset of the spec. `resources/examples/gain.yml` is a working example.

- Read: `name`, `namespace`, `n_channels`, `meta`, and `params`.

- Rejected with an error: `prefix`, `alias`, `help`, `outlets`, `message_methods`, `type_methods`, and `arg: true` on a param. These have no plugin equivalent.

- Params must be `type: float` and set finite `min` and `max`, with `min < max` and `min <= initial <= max`.

- `name`, `namespace`, and param names must be ASCII identifiers. They become C identifiers, the CLAP id `namespace.name`, and the VCV slugs.

- `inlet: true` adds a CV input for the param in VCV. CLAP ignores it; every CLAP param is automatable.

- A `~` in the spec filename is ignored. Plugins always process audio.

The CLAP `CMakeLists.txt` derives AUv2 four-character codes from `namespace` and `name`. Replace them before shipping an AU.

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

- [x] **CLAP plugin generation**, wrapped as VST3/AUv2 by clap-wrapper

- [x] **VCV Rack 2 plugin generation**

- [x] **Template-based code generation** system using Mako

- [x] **Support for DSP externals** (signal processing)

- [x] **Comprehensive type system** with validation and error handling

- [x] **Test suite** (122 tests, including CLI tests)

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
