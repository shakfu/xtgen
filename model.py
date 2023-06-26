# models.py
"""
Not used except for sketching the xtgen object model

"""

from typing import Optional, TypeVar, TypeAlias, Union, ForwardRef

from dataclasses import dataclass, asdict

number = TypeVar('number', int, float)
# number: TypeAlias = Union[int, float]


@dataclass
class Param:
    name: str
    type: str
    min: number
    max: number
    initial: number
    arg: bool
    inlet: bool
    desc: Optional[str] = None


@dataclass
class Meta:
    author: str
    repo: str
    desc: str
    features: list[str]


@dataclass
class Inlet:
    name: str
    type: str

@dataclass
class Outlet:
    name: str
    type: str

@dataclass
class MessageMethod:
    name: str
    params: list[Param]
    doc: str

@dataclass
class TypeMethod:
    type: str
    doc: str

@dataclass
class External:
    namespace: str
    name: str
    prefix: str
    alias: str
    params: list[Param]
    meta: Meta
    inlets: list[Inlet]
    outlets: list[Outlet]
    message_methods: list[MessageMethod]
    type_methods: list[TypeMethod]


def test():
    counter = External(
        namespace="my",
        name="counter",
        prefix="ctr",
        alias="cntr",
        params = [
            Param(name="step",  type="float", min=0.0, max=1.0, initial=0.5, arg=True, inlet=True, desc="")
        ],
        meta = Meta(
            desc="An external which counts via a variable step and optionally between two limits.",
            features = ["configurable integer counting", "can count in steps", "an count between a lower and upper bound"],
            author="gpt3",
            repo="https://github.com/gpt3/counter.git"
        ),
        inlets = [
            Inlet(name="bound", type="list"),
        ],
        outlets = [
            Outlet(name="f", type="float"),
        ],
        message_methods = [
            MessageMethod(name="reset", params=[], doc="reset count to zero"),
        ],
        type_methods = [
            TypeMethod(type="bang", doc="each bang increments the counter"),
        ],
    )
    return counter

if __name__ == '__main__':
    c = test()
    d = asdict(c)


