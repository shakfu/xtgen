# xtgen

A modern, type-safe Python command-line tool and package that generates audio software projects from a specification ("spec"). A `spec` is a YAML or JSON file that describes one audio object: its name, parameters, inputs and outputs, and the messages it handles.

Each run generates a project from the spec for one target, chosen with `-t`:

- `pd`: a PureData external, a compiled object that Pd loads into a patch

- `max`: a Max/MSP external

- `clap`: a CLAP plugin, also built as VST3 and, on macOS, AUv2

- `vcv`: a VCV Rack 2 module

By default, the generated audio code copies its input to its output, which is the part the developer should replace with custom DSP code.

Alternatively, a spec can name a `.gdsp` file: signal processing (oscillators, filters, delays) written in the domain-specific language (DSL) of [gen-dsp](https://github.com/shakfu/gen-dsp). gen-dsp compiles it to C or C++, and the generated project runs it.

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

- **Working DSP from gen-dsp**: a spec's `dsp` field names a `.gdsp` file, which gen-dsp compiles to C99 for the generated Pd, Max, CLAP or VCV code to call (see [DSP Graphs](#dsp-graphs))

- **Built-in examples**, named on the command line (`xtgen -t vcv reslp~`). `--list-examples` shows the targets each one builds for, found by validating it against every target

- **Test suite** of 205 tests. Generated code is compiled and run: Pd externals in real Pd, Max externals in a fake Max runtime, CLAP plugins in a test host, and VCV modules headless against libRack

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

For `dsp` graphs, install the optional dependency. `uv sync` already installs it for development.

```sh
pip install 'xtgen[dsp]'
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

- Optional, for `dsp` graphs: gen-dsp with its graph frontend (`xtgen[dsp]`, which pulls in pydantic). It needs gen-dsp 0.6.0 or later, which adds C output and its header. Until 0.6.0 is on PyPI, `pyproject.toml` installs it from `../gen-dsp`. Specs without `dsp` do not need it.

## Usage

### Command Line Interface

The easiest way to use xtgen is through its command-line interface:

```sh
usage: xtgen [-h] [-t {pd,max,clap,vcv}] [-o DIR] [-v] [-q] [-f]
             [--list-examples] [--validate]
             [spec_file]

Generate PureData, Max/MSP, CLAP/VST3/AU and VCV Rack projects from YAML or JSON specifications

positional arguments:
  spec_file             Path to YAML or JSON specification file, or the name
                        of a built-in example (default: counter)

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
  xtgen --list-examples                # List built-in examples and their targets
  xtgen -t clap lowpass~               # Generate from a built-in example by name
  xtgen -t vcv reslp~                  # Built-in example with gen-dsp DSP (needs xtgen[dsp])

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
uv run xtgen -t max counter.json

# Use custom output directory
uv run xtgen -o /tmp/my-externals counter.yml

# Verbose output with detailed information
uv run xtgen -v counter.yml

# Validate specification without generating
uv run xtgen --validate counter.yml

# List built-in examples and their targets
uv run xtgen --list-examples
```

### Built-in Examples

A spec argument that is not an existing path is looked up among the built-in examples. A bare name prefers `.yml` over `.json`.

| Example | Kind | Targets |
|-|-|-|
| `counter` | control, with outlets and methods | pd, max |
| `gain` | stereo effect | clap, vcv |
| `oscil~` | sine oscillator | pd, max, clap, vcv |
| `lowpass~` | resonant lowpass filter | pd, max, clap, vcv |
| `reslp~` | resonant lowpass with real DSP, from `reslp.gdsp` | pd, max, clap, vcv |

`--list-examples` derives each example's targets by running each target's validator. Without a `dsp` graph, every target emits a pass-through DSP body, so those examples set only names, params and channel count.

### Installed Package Usage

When xtgen is installed as a package, the `xtgen` command is on `PATH`. `python -m xtgen` runs the same CLI.

```sh
# Generate PureData project (default behavior)
xtgen counter

# Generate Max/MSP project
xtgen -t max counter.json

# Use custom output directory
xtgen -o /tmp/my-externals counter.yml
```

#### CLI Options

- `-t, --target {pd,max,clap,vcv}` - Target platform (default: pd)

- `-o, --output DIR` - Output directory (default: build)

- `-v, --verbose` - Enable verbose output

- `-q, --quiet` - Suppress all output except errors

- `-f, --force` - Force overwrite existing directories

- `--validate` - Validate specification file without generating

- `--list-examples` - List built-in examples and the targets each builds for

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

# A spec with a 'dsp' graph also writes <name>_dsp.c and <name>_dsp.h
PdProject('reslp~.yml').generate()
```

### Project Compilation

Generated projects are ready to compile:

```sh
# For PureData projects
make -C build/counter

# For Max/MSP projects (requires Max SDK)
# Follow Max SDK build instructions; with a 'dsp' graph, also compile <name>_dsp.c

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

Generated code is compiled, and where possible run:

- Pd: sources are syntax-checked against a stub `m_pd.h` with `-Wall -Werror`. DSP graph externals are also built with pd-lib-builder and run in Pd's batch mode, which checks their output values. That test finds Pd through `$PD`, `pd` on `PATH`, `/Applications/Pd*.app` or `/Applications/*/Pd*.app`, and is skipped without it.

- Max: sources are syntax-checked against stub SDK headers in `tests/mx`. DSP graph externals are linked with a fake Max runtime (`tests/mx/fake_max.c`) and run through `tests/mx/graph_host.c`.

- CLAP: each plugin is compiled with `-Wall -Wextra -Werror` and run in `tests/clap/host.c`, against CLAP headers vendored in `tests/clap/include`.

- VCV: the build tests run only when `RACK_DIR` points to a Rack SDK. They build with `FLAGS=-Werror`, and DSP graph modules are then run headless against the SDK's `libRack` through `tests/vcv/rack_host.cpp`.

DSP graph tests need gen-dsp (installed by `uv sync`) and are skipped without it.

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

A spec holds one entry under `externals`. In Pd and Max, inlets and outlets are an object's input and output connections in a patch. A spec filename ending in `~` (e.g. `lowpass~.yml`) makes a signal (audio-rate) object for `pd` and `max`; the plugin targets always process audio.

| Field | Meaning |
|-|-|
| `name` | Object name. The Pd class is `name`, or `name~` for a signal object. Required. |
| `namespace` | Group name. The Max class and the CLAP id are `namespace.name`; it is also the VCV plugin slug. Required. |
| `prefix` | Prefix of the C struct, class and function names (default: `name`). Pd still names its setup function after `name`. |
| `alias` | A second name the object can be created by. |
| `help` | Pd only: name of the object's help patch. Max has no call to set one and rejects it. |
| `n_channels` | Number of audio channels: signal inlets and outlets for a `pd` or `max` signal object, ports for CLAP, jacks for VCV. Rejected on a control object. |
| `params` | Parameters. Each has `name`, `type` (`float` or `symbol`), `min`, `max`, `initial` and `desc`. `arg: true` sets it from a creation argument (Pd). `inlet: true` gives it its own inlet (Pd) or CV input (VCV). |
| `outlets` | Message outlets, each with `name` and `type` (`bang`, `float`, `symbol`, `pointer`, `list` or `anything`). |
| `message_methods` | Named messages the object handles, such as `reset`. Each lists its argument types in `params`. Generated as stubs. |
| `type_methods` | Handlers for incoming messages by type (`bang`, `float`, `symbol`, `pointer`, `list` or `anything`). Generated as stubs. Max has no `pointer` messages and rejects that type. A `pd` signal object rejects `float`, because Pd sends floats on its left inlet to the audio input; a graph with no audio inputs has no signal inlet and keeps it. |
| `meta` | `desc`, `features`, `author` and `repo`, copied into comments and the generated README. Required. |
| `dsp` | A `.gdsp` file whose compiled DSP the object runs. See [DSP Graphs](#dsp-graphs). |

Every target rejects, with an error, a field it cannot use, rather than ignore it. For `clap` and `vcv`, see [Plugin Targets](#plugin-targets).

### YAML Format

```yaml
externals:
  - namespace: my
    name: counter
    prefix: ctr
    alias: cntr
    help: help-counter
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

`clap` and `vcv` read a subset of the spec. The built-in `gain`, `oscil~`, `lowpass~` and `reslp~` examples are valid for them.

- Read: `name`, `namespace`, `n_channels`, `meta`, `params`, and `dsp` (see [DSP Graphs](#dsp-graphs)).

- Rejected with an error: `prefix`, `alias`, `help`, `outlets`, `message_methods`, `type_methods`, and `arg: true` on a param. These have no plugin equivalent.

- Params must be `type: float` and set finite `min` and `max`, with `min < max` and `min <= initial <= max`.

- `name`, `namespace`, and param names must be ASCII identifiers. They become C identifiers, the CLAP id `namespace.name`, and the VCV slugs.

- `inlet: true` adds a CV input for the param in VCV. CLAP ignores it; every CLAP param is automatable.

- A `~` in the spec filename is ignored. Plugins always process audio.

The CLAP `CMakeLists.txt` derives AUv2 four-character codes from `namespace` and `name`. Replace them before shipping an AU.

### DSP Graphs

A graph is a `.gdsp` file in the DSL of [gen-dsp](https://github.com/shakfu/gen-dsp). It declares audio inputs and outputs, params with ranges, and the processing between them, built from nodes such as oscillators, filters and delays. `dsp` names one, resolved relative to the spec file. gen-dsp compiles it to C99 as `<name>_dsp.c` and `<name>_dsp.h`, and the generated source calls it instead of copying input to output.

```gdsp
graph reslp {
    in left, right
    out out_l = lp_l
    out out_r = lp_r
    param cutoff 20..20000 = 1000
    param q 0.5..20 = 0.707
    lp_l = svf(left, cutoff, q, mode=lp)
    lp_r = svf(right, cutoff, q, mode=lp)
}
```

```yaml
externals:
  - namespace: my
    name: reslp
    dsp: reslp.gdsp
    meta: {desc: "A resonant lowpass.", features: [], author: me, repo: ""}
```

- Targets: all four. The graph supplies the params (name, min, max, default) and the audio input and output counts; the spec must not set `params` or `n_channels`.

- `pd` and `max` need a `~` spec filename. Each param is set by a `<name> <value>` message, clamped to its range.

- `pd` also renders `outlets`, `message_methods` and `type_methods`, so an object can mix graph DSP with message handling. As on any `pd` signal object, a `float` type method is rejected when the graph has audio inputs. A message method with the same name as a param, or as a built-in method (`dsp`, `dsp64`, `assist`), is also rejected.

- `max` has no generated build file: add `<name>_dsp.c` to the external's sources.

- `vcv` processes mono (channel 0) and scales audio from +-5 V to +-1 and back.

- A graph with no inputs is a generator: no signal inlet or input jack, no CLAP input port. CLAP declares it an `instrument` and the AU type `aumu`, since clap-wrapper v0.16 builds no `augn` (generator) units.

- The dsp state is created at the host's sample rate (Pd and Max `dsp` methods, CLAP `activate`, VCV's first `process`), so a sample-rate change resets it.

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

- [x] **Test suite** (205 tests, including CLI tests and runs of generated code)

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

- [x] **DSP graphs** from gen-dsp, for all four targets

- [x] **Built-in examples** addressable by name

### Future Enhancements

- [x] xtgen to become a python package

- [ ] Hybrid dual Max/PD template

- [ ] Message and type methods in Max DSP graph externals (Pd already has them)

- [ ] Polyphonic VCV modules for DSP graphs (one graph state per voice)

- [ ] Double-precision Pd builds for DSP graphs (the graph code is 32-bit float)

- [ ] Additional DSP utility functions

- [ ] Extended help file generation for PureData

- [ ] Plugin packaging and distribution tools
