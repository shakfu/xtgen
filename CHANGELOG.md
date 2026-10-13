# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Releases up to 0.1.2 are recorded only in git history.

## [Unreleased]

### Changed

- Breaking: the spec format is a core plus one block per object model. The top-level `externals` list is gone, and the spec is the one object. `pd` and `max` read the `external` block. `clap` and `vcv` read the `plugin` block. Each target ignores the other's block, so one spec builds for all four targets with no per-target copies. Before, every field sat in one namespace, and plugins rejected the Pd/Max fields. A spec that needed Pd inlets could therefore not build as a plugin. A pre-0.3 spec fails with a migration hint.

  ```yaml
  namespace: my
  name: lowpass
  params: [{name: cutoff, type: float, min: 20, max: 20000, initial: 1000}]
  external: {inlets: [cutoff], args: [cutoff]}
  plugin: {modulated: [cutoff]}
  ```

  Per-param `arg` and `inlet` move into the blocks as lists of param names: `external.args`, `external.inlets` and `plugin.modulated`. Core params are then the same for every target. `counter` now builds as a plugin too.

- Unknown param fields are rejected.

- gen-dsp is installed from PyPI, where 0.6.0 is now published, not from `../gen-dsp`.

- `dsp` needs gen-dsp 0.6.1. Up to 0.6.0, a graph node could reuse the name of one of gen-dsp's generated locals, e.g. node `wt_len` beside Buffer `wt`, and `buf_read` then read past the table in `<name>_dsp.c`. gen-dsp 0.6.1 rejects IDs that would shadow its `perform()` locals; xtgen reports them as `Invalid 'dsp' graph`. Tests compile `_dsp.c` with `-Wshadow`. Until 0.6.1 is on PyPI, `[tool.uv.sources]` resolves gen-dsp from `../gen-dsp` again.

### Added

- `plugin.modulated` makes a CLAP param modulatable. The plugin adds `CLAP_EVENT_PARAM_MOD` amounts to the value DSP reads, clamped to the param's range. This replaces the old behaviour, where CLAP ignored `inlet: true`. For graph DSP, `plugin.modulated` may name graph params, which also gives VCV graph modules CV inputs.

## [0.2.0]

### Added

- `-t clap` generates a CLAP plugin in C, with params, audio-ports and state extensions. Its `CMakeLists.txt` uses [clap-wrapper](https://github.com/free-audio/clap-wrapper) to build VST3, plus AUv2 on macOS. Wrapping one CLAP replaces separate VST3 and AU templates, which would triple the template code and could not be checked on Linux.

  ```sh
  xtgen -t clap gain.yml
  cmake -S build/gain -B build/gain/build && cmake --build build/gain/build --target gain_all
  ```

- `-t vcv` generates a VCV Rack 2 plugin with one module, a blank panel, and a CV input for each param with `inlet: true`.

- `resources/examples/gain.yml`, a spec valid for both plugin targets.

- Built-in examples can be named on the command line, e.g. `xtgen -t vcv lowpass~`. An existing path of the same name takes precedence. `--list-examples` shows the targets each example validates against. The targets are derived from the validators, not declared in the spec, so they cannot drift.

- `oscil~` and `lowpass~` examples, valid for every target.

- `dsp: <file>.gdsp` names a [gen-dsp](https://github.com/shakfu/gen-dsp) graph, signal processing written in gen-dsp's DSL. gen-dsp compiles it to C99, and the generated project calls it instead of copying input to output, for every target. The graph supplies the params and the audio input/output counts, and the spec may not repeat them, so the two cannot disagree. C was chosen over gen-dsp's default C++ because the Pd, Max and CLAP templates are C99; VCV includes it through gen-dsp's `extern "C"` header. gen-dsp 0.6.0 or later is an optional dependency (`xtgen[dsp]`); until 0.6.0 is on PyPI, `pyproject.toml` installs it from `../gen-dsp`. The built-in `reslp~` example uses it.

  ```yaml
  externals:
    - {namespace: my, name: reslp, dsp: reslp.gdsp, meta: {...}}
  ```

- A graph with no audio inputs builds as a CLAP instrument with AU type `aumu`. `augn` (generator) was not used because clap-wrapper v0.16 builds it as a music device while labelling it a generator.

- In Pd, a graph object may also have `outlets`, `message_methods` and `type_methods`.

- `TARGETS` maps CLI target names to generator classes.

- `python -m xtgen` runs the CLI.

### Changed

- The bundled `resources/pd/m_pd.h` is updated from Pd 0.53 to 0.57.

- `pd` and `max` use or reject every spec field, instead of ignoring some. A silently ignored field produced an object without behaviour the spec asked for.
  - `pd` uses `prefix` for its C identifiers; the setup function keeps `name`, which Pd looks up.
  - A `pd` signal object gets `n_channels` signal inlets and outlets.
  - `max` registers `message_methods`, `type_methods` and `alias` (through `class_alias`).
  - Rejected: `n_channels` on a `pd` or `max` control object; a `float` type method on a `pd` signal object with a signal inlet, where Pd replaces it with its own; and on `max`, `help` (the SDK cannot set a help file) and a `pointer` type method.

  The built-in `counter` drops `n_channels`, `help` and its `pointer` method to stay valid for both; `gain` is now valid only for `clap` and `vcv`.

- The README defines its terms and documents every spec field.

- `--validate` applies the rules of the target given by `-t`. Before, it always applied the Pd rules.

- Plugin targets reject `prefix`, `alias`, `help`, `outlets`, `message_methods`, `type_methods` and `arg: true`. They do not ignore them. A silently ignored field would generate a plugin missing behaviour the spec asked for. Params must be float, with finite `min < max` and `min <= initial <= max`.

### Fixed

- Generated READMEs had `\##` or `\\##` headings. The templates escaped Mako's `##` comment marker with a backslash, which Mako does not recognise, so the backslashes were printed. They now write `${'##'}`.

- A Pd spec with no `arg: true` param generated `class_new(..., CLASS_DEFAULT, , 0)` and `class_addcreator(..., , 0)`, which do not compile. The empty type signature was `", 0"`, and the templates already supply the leading comma.
