# xtgen

A tool to generate skeleton PureData and Max/MSP external files from YAML specifications.

## Features

- Generate PureData external projects with complete build system
- Generate Max/MSP external projects
- Template-based code generation using Mako templates
- Type-safe YAML specification parsing
- Comprehensive test coverage
- Support for both regular and DSP (signal processing) externals

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

### Basic Usage

Generate a PureData external project:

```python
from xtgen import PdProject

project = PdProject('resources/examples/counter.yml')
project.generate()
```

Generate a Max/MSP external project:

```python
from xtgen import MaxProject

project = MaxProject('resources/examples/counter.yml')
project.generate()
```

### Command Line Demo

Run the built-in demo:

```bash
uv run python -c "from xtgen import PdProject; p = PdProject('resources/examples/counter.yml'); p.generate()"
```

This creates a PureData external project in `build/counter/` that is ready to compile:

```bash
make -C build/counter
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

## YAML Specification Format

External specifications are defined in YAML files. Here's the structure:

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

## Project Status

### Completed Features

- [x] Complete YAML specification parsing and validation
- [x] PureData external project generation
- [x] Max/MSP external project generation
- [x] Template-based code generation system
- [x] Support for DSP (signal processing) externals
- [x] Comprehensive type system with validation
- [x] Full test coverage (22 tests)
- [x] Type safety with mypy
- [x] Code quality with ruff linting
- [x] Inlet and outlet generation
- [x] Parameter handling with constructor arguments
- [x] Message method generation
- [x] Type method generation (bang, float, symbol, etc.)
- [x] Build system integration (Makefiles)
- [x] Documentation generation

### Future Enhancements

- [ ] Hybrid dual Max/PD template
- [ ] Additional DSP utility functions
- [ ] Extended help file generation for PureData
- [ ] Plugin packaging and distribution tools
