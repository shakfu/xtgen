# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Releases up to 0.1.2 are recorded only in git history.

## [0.2.0] - 2026-10-13

### Added

- `-t clap` generates a CLAP plugin in C, with params, audio-ports and state extensions. Its `CMakeLists.txt` uses [clap-wrapper](https://github.com/free-audio/clap-wrapper) to build VST3, plus AUv2 on macOS. Wrapping one CLAP replaces separate VST3 and AU templates, which would triple the template code and could not be checked on Linux.

  ```sh
  xtgen -t clap gain.yml
  cmake -S build/gain -B build/gain/build && cmake --build build/gain/build --target gain_all
  ```

- `-t vcv` generates a VCV Rack 2 plugin with one module, a blank panel, and a CV input for each param with `inlet: true`.

- `resources/examples/gain.yml`, a spec valid for both plugin targets.

- `TARGETS` maps CLI target names to generator classes.

### Changed

- `--validate` applies the rules of the target given by `-t`. Before, it always applied the Pd rules.

- Plugin targets reject `prefix`, `alias`, `help`, `outlets`, `message_methods`, `type_methods` and `arg: true`. They do not ignore them. A silently ignored field would generate a plugin missing behaviour the spec asked for. Params must be float, with finite `min < max` and `min <= initial <= max`.
