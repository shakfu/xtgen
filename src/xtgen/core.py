#!/usr/bin/env python3
"""xtgen - A modern, type-safe tool to generate skeleton PureData and Max/MSP external files.

This module provides backward compatibility imports and a unified interface
for external generation. The implementation has been modularized into focused
components for better maintainability:

- models.py: Data models and type definitions
- generators.py: Code generation utilities
- templates.py: Template rendering and project generation
- cli.py: Command-line interface

## Quick Start

>>> from xtgen import PdProject, MaxProject
>>>
>>> # Generate PureData external
>>> pd_project = PdProject('counter.yml')
>>> pd_project.generate()
>>>
>>> # Generate Max/MSP external
>>> max_project = MaxProject('counter.yml')
>>> max_project.generate()
"""

# Backward compatibility imports
from .models import (
    AudioTypeError,
    AbstractType,
    ScalarType,
    CompoundType,
    TypeMethod,
    MessageMethod,
    Param,
    Outlet,
    External,
    c_type,
    lookup_address,
    lookup_routine,
)
from .generators import (
    TypeMapper,
    ArgumentBuilder,
    CodeGenerator,
)
from .templates import (
    Generator,
    MaxProject,
    PdProject,
    get_package_resource_path,
    OUTPUT_DIR,
    TEMPLATE_DIR,
    TEMPLATE_LOOKUP,
)
from .cli import main
# All functionality has been moved to dedicated modules.
# This core.py file now serves as the main entry point and provides backward compatibility.


# ----------------------------------------------------------------------------
# MAIN ENTRY POINT

if __name__ == "__main__":
    import sys
    sys.exit(main())
