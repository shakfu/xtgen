"""Compile a gen-dsp graph (.gdsp) to C99 for a target to embed.

A spec's ``dsp`` field names the graph. The graph supplies the params and the
audio input/output counts; the target calls its ``create``, ``perform`` and
``set_param`` functions. Requires the optional ``gen-dsp[graph]`` dependency,
version 0.6.0 or later (``lang="c"`` and ``compile_graph_header``).
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

# Selectors Pd or Max dispatch themselves; a param method with one of these names would shadow it.
RESERVED_PARAM_NAMES = frozenset({
    "dsp", "signal", "bang", "float", "symbol", "list", "anything", "pointer",  # Pd
    "dsp64", "assist", "int",  # Max
})


@dataclass(frozen=True)
class DspGraph:
    """A graph compiled to C, with the metadata a template needs."""

    prefix: str  # C symbol prefix of the compiled functions, e.g. "lowpass_dsp"
    state_type: str  # opaque state struct, e.g. "LowpassDspState"
    source: str  # the .gdsp file, for comments
    c_code: str
    header: str  # from gen-dsp; declares the functions inside extern "C"
    params: List[Dict[str, Any]]  # in spec form: name, type, min, max, initial
    n_inputs: int
    n_outputs: int


def load_graph(path: Path, prefix: str) -> DspGraph:
    """Parse a .gdsp file and compile it to C with symbols named ``<prefix>_*``.

    Raises:
        ValueError: If gen-dsp is missing or too old, or the graph is invalid
    """
    try:
        from gen_dsp.graph.compile import compile_graph, compile_graph_header
        from gen_dsp.graph.dsl import parse_file
    except ImportError as e:
        raise ValueError(
            f"'dsp' needs gen-dsp 0.6.0 or later with its graph frontend ({e}); "
            "install it with: pip install 'xtgen[dsp]'"
        )
    if not path.is_file():
        raise ValueError(f"'dsp' graph not found: {path}")

    try:
        graph = parse_file(path)
        assert not isinstance(graph, dict)  # multi=False returns the last graph
        # Renamed so the compiled symbols cannot collide with the target's own.
        graph = graph.model_copy(update={"name": prefix})
    except Exception as e:
        raise ValueError(f"Invalid 'dsp' graph {path}: {e}")
    try:
        c_code = compile_graph(graph, lang="c")
        header = compile_graph_header(graph)
    except ValueError as e:
        raise ValueError(f"Invalid 'dsp' graph {path}: {e}")

    # gen-dsp has no public accessor for the state type; its header's typedef names it.
    match = re.search(r"^typedef struct (\w+) \1;$", header, re.M)
    if match is None:
        raise ValueError("Unexpected gen-dsp header: no state struct typedef")
    if not graph.outputs:
        raise ValueError(f"'dsp' graph {path} has no audio outputs")
    for p in graph.params:
        if p.name in RESERVED_PARAM_NAMES:
            raise ValueError(f"'dsp' graph param {p.name!r} shadows a built-in method name")

    return DspGraph(
        prefix=prefix,
        state_type=match.group(1),
        source=path.name,
        c_code=c_code,
        header=header,
        params=[
            {"name": p.name, "type": "float", "min": p.min, "max": p.max, "initial": p.default}
            for p in graph.params
        ],
        n_inputs=len(graph.inputs),
        n_outputs=len(graph.outputs),
    )
