"""xtgen - Audio external code generator.

A modern, type-safe tool to generate skeleton PureData and Max/MSP external files.
"""

from .core import (
    ScalarType,
    CompoundType,
    External,
    TypeMethod,
    MessageMethod,
    Param,
    Outlet,
    PdProject,
    MaxProject,
    Generator,
    AudioTypeError,
    TypeMapper,
    ArgumentBuilder,
    CodeGenerator,
    main,
    create_argument_parser,
    validate_specification,
    list_examples,
    YAML_AVAILABLE,
)

__version__ = "0.1.1"

__all__ = [
    "ScalarType",
    "CompoundType",
    "External",
    "TypeMethod",
    "MessageMethod",
    "Param",
    "Outlet",
    "PdProject",
    "MaxProject",
    "Generator",
    "AudioTypeError",
    "TypeMapper",
    "ArgumentBuilder",
    "CodeGenerator",
    "main",
    "create_argument_parser",
    "validate_specification",
    "list_examples",
    "YAML_AVAILABLE",
]