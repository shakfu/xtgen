# TODO

## Critical

## High

## Medium

- [ ] Remove `[tool.uv.sources]` from `pyproject.toml` once gen-dsp 0.6.1 is on PyPI, then run `uv lock`. Until then xtgen resolves gen-dsp from `../gen-dsp`.

## Low

- [ ] Drop the state-type regex in `src/xtgen/dsp.py`. The templates need the graph's state type name to declare `<State> *dsp`. gen-dsp builds it internally (`_to_pascal(name) + "State"`) and does not expose it, so xtgen reads it from the typedef line of the header `compile_graph_header()` returns. That depends on the header's format. Fix in gen-dsp: add a public accessor for the name, or a comment in the header that names the type.


