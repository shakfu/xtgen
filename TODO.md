# TODO

## Critical

## High

## Medium

- [ ] Raise the gen-dsp floor to the first release after 0.6.1. It is `gen-dsp[graph]>=0.6.0` in `pyproject.toml` and 0.6.0 in `src/xtgen/dsp.py`'s docstring and ImportError message. Up to 0.6.1, a node ID could share a name with a gen-dsp generated local, e.g. node `wt_len` beside Buffer `wt`. `buf_read(wt, ...)` then clamps its index against the node's value, not the table length: a silent out-of-bounds read in `<name>_dsp.c`. Nodes named `n`, `i`, `sr`, `self`, `ins` or `outs` shadow `perform()` locals the same way. See gen-dsp's CHANGELOG, `[Unreleased]` / Fixed.

- [ ] After the bump, add `-Wshadow` to the `_dsp.c` flags in `build_and_run_clap()` and `build_and_run_max()` (`tests/test_xtgen.py`). gen-dsp's compile tests now build every graph with `-Wall -Wextra -Wshadow -Werror`.

- [ ] After the bump, test that `load_graph()` reports a reserved ID as `Invalid 'dsp' graph`. gen-dsp's `compile_graph` now raises `ValueError` for the six names above (a SampleRate node may be `sr`) and for IDs starting with `_` unless they end in `_<digits>`. `load_graph()` already wraps that error; the test pins the message.

## Low

- [ ] Drop the state-type regex in `src/xtgen/dsp.py`. The templates need the graph's state type name to declare `<State> *dsp`. gen-dsp builds it internally (`_to_pascal(name) + "State"`) and does not expose it, so xtgen reads it from the typedef line of the header `compile_graph_header()` returns. That depends on the header's format. Fix in gen-dsp: add a public accessor for the name, or a comment in the header that names the type.


