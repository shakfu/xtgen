"""xtgen - Audio external code generator.

A modern, type-safe tool to generate skeleton PureData and Max/MSP external files.
"""

# Import from new modular structure
from .models import (
    ScalarType,
    CompoundType,
    External,
    TypeMethod,
    MessageMethod,
    Param,
    Outlet,
    AudioTypeError,
)
from .generators import (
    TypeMapper,
    ArgumentBuilder,
    CodeGenerator,
)
from .templates import (
    Generator,
    PdProject,
    MaxProject,
    YAML_AVAILABLE,
)
from .cli import (
    main,
    create_argument_parser,
    validate_specification,
    list_examples,
)

# Backward compatibility - also expose everything from core
from .core import *

__version__ = "0.1.2"

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