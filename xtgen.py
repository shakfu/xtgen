#!/usr/bin/env python3
"""xtgen.py

A modern, type-safe tool to generate skeleton PureData and Max/MSP external files.

This module provides a complete code generation system for audio externals using:
- YAML-based external specifications
- Mako templating system
- Dataclass-based object model with proper validation
- Focused helper classes for maintainable code generation

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

## Architecture

The system is built with focused, single-responsibility classes:

- `External`: Main external representation with metadata and components
- `TypeMapper`: Handles mapping between audio types and C code
- `ArgumentBuilder`: Builds C function arguments for various components
- `CodeGenerator`: Generates C code snippets and method calls
- `TypeMethod`: Represents type-based methods (bang, float, etc.)
- `MessageMethod`: Represents named message methods
- `Param`: Represents external parameters with validation
- `Outlet`: Represents external outlets

## YAML External Specification

```yaml
externals:
  - namespace: my
    name: counter
    prefix: ctr
    alias: cntr
    help: help-counter
    n_channels: 1

    params:
      - name: step
        type: float
        initial: 1.0
        arg: true
        inlet: true
        desc: "increment step size"

    outlets:
      - name: count
        type: float

    message_methods:
      - name: reset
        params: []
        doc: "reset counter to zero"

    type_methods:
      - type: bang
        doc: "increment and output counter"

    meta:
      desc: "A simple counter external"
      author: "Your Name"
      repo: "https://github.com/yourname/counter"
      features: ["counting", "resettable"]
```

"""

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any, Union

import yaml
from mako.template import Template
from mako.lookup import TemplateLookup


# ----------------------------------------------------------------------------
# CONSTANTS

# Get the directory containing this script
SCRIPT_DIR = Path(__file__).parent
TEMPLATE_DIR = SCRIPT_DIR / "resources" / "templates"
TEMPLATE_LOOKUP = TemplateLookup(directories=[str(TEMPLATE_DIR)])
OUTPUT_DIR = "build"

# ----------------------------------------------------------------------------
# UTILITY FUNCTIONS


def c_type(type_name: str) -> str:
    """Generate C type name from audio type."""
    return f"t_{type_name}"


def lookup_address(symbol: str) -> str:
    """Generate symbol lookup address."""
    return f"&s_{symbol}"


def lookup_routine(symbol: str) -> str:
    """Generate symbol lookup routine."""
    return f'gensym("{symbol}")'


# ----------------------------------------------------------------------------
# TYPE CLASSES


class AudioTypeError(ValueError):
    """Custom exception for audio type validation errors."""

    pass


# ----------------------------------------------------------------------------
# HELPER CLASSES FOR EXTERNAL GENERATION


class TypeMapper:
    """
    Handles mapping between audio types and C code representations.

    This class provides static mappings from audio-specific type names
    to their corresponding C language representations and PureData API constants.
    It serves as the central type conversion utility for external generation.

    The class maintains two key mappings:
    - TYPE_MAPPINGS: Audio types to PureData API constants
    - FUNC_TYPE_ARGS: Audio types to C function argument strings

    Example:
        >>> TypeMapper.get_pd_mapping('float')
        'A_DEFFLOAT'
        >>> TypeMapper.get_func_arg('symbol')
        't_symbol *s'
    """

    # Type mappings for PureData API constants
    TYPE_MAPPINGS: Dict[str, str] = {
        "float": "A_DEFFLOAT",
        "symbol": "A_DEFSYMBOL",
        "anything": "A_GIMME",
    }

    # Function argument mappings for C function signatures
    FUNC_TYPE_ARGS: Dict[str, str] = {
        "float": "t_floatarg f",
        "symbol": "t_symbol *s",
        "anything": "t_symbol *s, int argc, t_atom *argv",
    }

    @classmethod
    def get_pd_mapping(cls, type_name: str) -> str:
        """
        Get PureData API constant for a given audio type.

        Args:
            type_name: Audio type name (e.g., 'float', 'symbol', 'anything')

        Returns:
            PureData API constant string (e.g., 'A_DEFFLOAT', 'A_DEFSYMBOL')

        Raises:
            AudioTypeError: If type_name is not supported
        """
        if type_name not in cls.TYPE_MAPPINGS:
            raise AudioTypeError(
                f"Unknown type mapping for '{type_name}'. Valid types: {list(cls.TYPE_MAPPINGS.keys())}"
            )
        return cls.TYPE_MAPPINGS[type_name]

    @classmethod
    def get_func_arg(cls, type_name: str) -> str:
        """
        Get C function argument string for a given audio type.

        Args:
            type_name: Audio type name (e.g., 'float', 'symbol', 'anything')

        Returns:
            C function argument string (e.g., 't_floatarg f', 't_symbol *s')

        Raises:
            AudioTypeError: If type_name is not supported
        """
        if type_name not in cls.FUNC_TYPE_ARGS:
            raise AudioTypeError(
                f"Unknown function argument type '{type_name}'. Valid types: {list(cls.FUNC_TYPE_ARGS.keys())}"
            )
        return cls.FUNC_TYPE_ARGS[type_name]


@dataclass
class ArgumentBuilder:
    """
    Builds C function arguments for various external components.

    This class constructs proper C function signatures and argument lists
    for external constructors, type methods, and message methods. It handles
    the complexity of mapping audio types to appropriate C argument strings
    while respecting PureData's argument limits and conventions.

    Key responsibilities:
    - Generate constructor argument lists with proper type mapping
    - Create PureData class type signatures for registration
    - Build method argument lists including external instance pointers

    Example:
        >>> mapper = TypeMapper()
        >>> builder = ArgumentBuilder(mapper)
        >>> builder.build_constructor_args([Param('step', 'float')])
        't_floatarg f0'
    """

    type_mapper: TypeMapper

    def __init__(self, type_mapper: TypeMapper) -> None:
        """
        Initialize ArgumentBuilder with a TypeMapper instance.

        Args:
            type_mapper: TypeMapper instance for type conversions
        """
        self.type_mapper = type_mapper

    def build_constructor_args(self, args: List["Param"]) -> str:
        """
        Build C constructor arguments for external creation.

        Constructs the argument list for the external's constructor function,
        handling PureData's limitation of 6 typed arguments before falling
        back to A_GIMME (generic argument parsing).

        Args:
            args: List of Param objects representing constructor arguments

        Returns:
            C function argument string for constructor signature
        """
        if len(args) == 0:
            return "void"
        elif 0 < len(args) <= 6:
            type_args: List[str] = []
            for i, arg in enumerate(args):
                func_arg: str = self.type_mapper.get_func_arg(arg.type)
                type_args.append(func_arg + str(i))
            return ", ".join(type_args)
        else:
            # Use A_GIMME for many arguments
            return "t_symbol *s, int argc, t_atom *argv"

    def build_type_signature(self, args: List["Param"]) -> str:
        """
        Build PureData class type signature for registration.

        Creates the type signature string used in class_new() calls to
        register the external with PureData's type system.

        Args:
            args: List of Param objects representing constructor arguments

        Returns:
            Type signature string for PureData class registration
        """
        suffix: str = ", 0"

        if len(args) == 0:
            return suffix
        elif 0 < len(args) <= 6:
            mappings: List[str] = []
            for arg in args:
                mapping: str = self.type_mapper.get_pd_mapping(arg.type)
                mappings.append(mapping)
            return ", ".join(mappings) + suffix
        else:
            return "A_GIMME" + suffix

    def build_method_args(self, external_type: str, params: List[str]) -> str:
        """
        Build C function arguments for message methods.

        Constructs argument lists for message method functions, always
        including the external instance pointer as the first argument.

        Args:
            external_type: C type name of the external (e.g., 't_counter')
            params: List of parameter type names for the method

        Returns:
            C function argument string for message method signature
        """
        base_arg: str = f"{external_type} *x"

        if len(params) == 0:
            return base_arg
        elif params == ["list"] or len(params) > 6:
            return f"{base_arg}, t_symbol *s, int argc, t_atom *argv"
        else:
            type_args: List[str] = []
            for i, param_type in enumerate(params):
                func_arg: str = self.type_mapper.get_func_arg(param_type)
                type_args.append(func_arg + str(i))
            return f"{base_arg}, {', '.join(type_args)}"


@dataclass
class CodeGenerator:
    """
    Generates C code snippets for external components.

    This class creates specific C code fragments used in audio external
    generation, focusing on PureData API calls for method registration,
    class setup, and alias creation. It works closely with TypeMapper
    and ArgumentBuilder to ensure proper type handling.

    Key responsibilities:
    - Generate class method registration calls (class_addbang, class_addfloat, etc.)
    - Create message method registration calls (class_addmethod)
    - Generate alias creator calls (class_addcreator)

    Example:
        >>> mapper = TypeMapper()
        >>> builder = ArgumentBuilder(mapper)
        >>> generator = CodeGenerator(mapper, builder)
        >>> generator.generate_class_addmethod('counter', 'bang', 'bang')
        'class_addbang(counter_class, counter_bang)'
    """

    type_mapper: TypeMapper
    arg_builder: ArgumentBuilder

    def __init__(self, type_mapper: TypeMapper, arg_builder: ArgumentBuilder) -> None:
        """
        Initialize CodeGenerator with required helper instances.

        Args:
            type_mapper: TypeMapper instance for type conversions
            arg_builder: ArgumentBuilder instance for argument construction
        """
        self.type_mapper = type_mapper
        self.arg_builder = arg_builder

    def generate_class_addmethod(
        self, external_name: str, method_name: str, method_type: str
    ) -> str:
        """
        Generate class_add method call for type methods.

        Creates the appropriate class_add* call for registering type-specific
        methods (bang, float, symbol, etc.) with PureData's class system.

        Args:
            external_name: Name of the external class
            method_name: Name of the method (currently unused, kept for consistency)
            method_type: Type of the method (bang, float, symbol, etc.)

        Returns:
            C code string for class method registration
        """
        return f"class_add{method_type}({external_name}_class, {external_name}_{method_type})"

    def generate_message_addmethod(
        self, external_name: str, method_name: str, params: List[str]
    ) -> str:
        """
        Generate class_addmethod call for message methods.

        Creates the class_addmethod call for registering custom message
        methods with PureData, handling parameter type mapping and
        argument count limitations.

        Args:
            external_name: Name of the external class
            method_name: Name of the message method
            params: List of parameter type names

        Returns:
            C code string for message method registration
        """
        prefix: str = (
            f"class_addmethod({external_name}_class, "
            f"(t_method){external_name}_{method_name}, "
            f'gensym("{method_name}")'
        )

        if len(params) == 0:
            return f"{prefix}, 0)"
        elif params == ["list"] or len(params) > 6:
            return f"{prefix}, A_GIMME, 0)"
        else:
            mappings: List[str] = []
            for param_type in params:
                mapping: str = self.type_mapper.get_pd_mapping(param_type)
                mappings.append(mapping)
            return f"{prefix}, {', '.join(mappings)}, 0)"

    def generate_creator_call(
        self, external_name: str, alias: Optional[str], type_signature: str
    ) -> str:
        """
        Generate class_addcreator call for external alias.

        Creates the class_addcreator call for registering an alternative
        name (alias) for the external, allowing users to instantiate
        the external using different names.

        Args:
            external_name: Name of the external class
            alias: Alias name for the external
            type_signature: Type signature string for the creator

        Returns:
            C code string for alias registration, empty string if no alias needed
        """
        if not alias or alias == external_name:
            return ""  # No alias needed
        return (
            f"class_addcreator((t_newmethod)"
            f'{external_name}_new, gensym("{alias}"), '
            f"{type_signature})"
        )


@dataclass
class AbstractType:
    """Base class for audio external types."""

    name: str
    VALID_TYPES: List[str] = field(default_factory=list, init=False)

    def __post_init__(self):
        if self.name not in self.VALID_TYPES:
            raise AudioTypeError(
                f"Invalid type '{self.name}'. Valid types: {self.VALID_TYPES}"
            )

    def __str__(self) -> str:
        return self.name


@dataclass
class ScalarType(AbstractType):
    """Scalar audio types: bang, float, symbol, pointer, signal."""

    VALID_TYPES: List[str] = field(
        default_factory=lambda: ["bang", "float", "symbol", "pointer", "signal"],
        init=False,
    )

    @property
    def c_type(self) -> str:
        """Generate C type name."""
        return c_type(self.name)

    @property
    def lookup_address(self) -> str:
        """Generate symbol lookup address."""
        return lookup_address(self.name)

    @property
    def lookup_routine(self) -> str:
        """Generate symbol lookup routine."""
        return lookup_routine(self.name)

    @property
    def type_method_arg(self) -> str:
        """Generate C function argument for this type."""
        type_args = {
            "bang": "",
            "float": "t_floatarg f",
            "int": "t_floatarg f",
            "symbol": "t_symbol *s",
            "pointer": "t_gpointer *pt",
        }
        if self.name not in type_args:
            raise AudioTypeError(f"No type method argument defined for '{self.name}'")
        return type_args[self.name]


@dataclass
class CompoundType(AbstractType):
    """Compound audio types: list, anything."""

    VALID_TYPES: List[str] = field(
        default_factory=lambda: ["list", "anything"], init=False
    )

    @property
    def c_type(self) -> str:
        """Generate C type name (not available for 'anything')."""
        if self.name == "anything":
            raise AudioTypeError("C type not available for 'anything' type")
        return c_type(self.name)

    @property
    def lookup_address(self) -> str:
        """Generate symbol lookup address."""
        return lookup_address(self.name)

    @property
    def lookup_routine(self) -> str:
        """Generate symbol lookup routine."""
        return lookup_routine(self.name)

    @property
    def type_method_arg(self) -> str:
        """Generate C function argument for this type."""
        type_args = {
            "list": "t_symbol *s, int argc, t_atom *argv",
            "anything": "t_symbol *s, int argc, t_atom *argv",
        }
        return type_args[self.name]


@dataclass
class TypeMethod:
    """Represents a type method for an external (bang, float, etc.)."""

    parent: "External"
    type: str
    doc: str = ""

    VALID_TYPES = ["bang", "float", "int", "symbol", "pointer", "list", "anything"]

    def __post_init__(self):
        if self.type not in self.VALID_TYPES:
            raise AudioTypeError(
                f"Invalid type method '{self.type}'. Valid types: {self.VALID_TYPES}"
            )

    @property
    def name(self) -> str:
        """Type methods are named after their type."""
        return self.type

    @property
    def args(self) -> str:
        """Generate C function arguments for this type method."""
        base_arg = f"{self.parent.type} *x"

        type_args_map = {
            "bang": "",
            "float": ", t_floatarg f",
            "int": ", t_floatarg f",
            "symbol": ", t_symbol *s",
            "pointer": ", t_gpointer *pt",
            "list": ", t_symbol *s, int argc, t_atom *argv",
            "anything": ", t_symbol *s, int argc, t_atom *argv",
        }

        if self.type not in type_args_map:
            raise AudioTypeError(
                f"Argument generation not implemented for type '{self.type}'"
            )

        return base_arg + type_args_map[self.type]

    @property
    def class_addmethod(self) -> str:
        """Generate class_add method call for this type."""
        return self.parent.code_generator.generate_class_addmethod(
            self.parent.name, self.name, self.type
        )


@dataclass
class MessageMethod:
    """Represents a message method for an external."""

    parent: "External"
    name: str
    params: List[str] = field(default_factory=list)
    doc: str = ""

    @property
    def args(self) -> str:
        """Generate C function arguments for this message method."""
        return self.parent.arg_builder.build_method_args(self.parent.type, self.params)

    @property
    def class_addmethod(self) -> str:
        """Generate class_addmethod call for this message method."""
        return self.parent.code_generator.generate_message_addmethod(
            self.parent.name, self.name, self.params
        )


@dataclass
class Param:
    """Represents a parameter of an external."""

    parent: "External"
    name: str
    type: str
    initial: Union[float, int, str]
    is_arg: bool
    has_inlet: bool
    desc: str = ""
    min: Optional[float] = None
    max: Optional[float] = None

    C_TYPES = {
        "atom": "t_atom",
        "float": "t_float",
        "symbol": "t_symbol",
        "int": "t_int",
        "signal": "t_signal",
        "sample": "t_sample",
    }

    def __post_init__(self):
        if self.type not in self.C_TYPES:
            raise AudioTypeError(
                f"Invalid parameter type '{self.type}'. Valid types: {list(self.C_TYPES.keys())}"
            )

    @property
    def pd_type(self) -> str:
        """Get the PureData C type for this parameter."""
        return self.C_TYPES[self.type]

    @property
    def struct_declaration(self) -> str:
        """Generate C struct field declaration."""
        return f"{self.pd_type} {self.name}"


@dataclass
class Outlet:
    """Represents an outlet of an external."""

    parent: "External"
    name: str
    type: str

    def __post_init__(self):
        # Basic validation - could be expanded
        valid_outlet_types = ["float", "bang", "symbol", "list", "anything"]
        if self.type not in valid_outlet_types:
            raise AudioTypeError(
                f"Invalid outlet type '{self.type}'. Valid types: {valid_outlet_types}"
            )


@dataclass
class External:
    """Represents an audio external with all its components."""

    # Core identification
    name: str
    namespace: str
    prefix: str = ""
    alias: Optional[str] = None
    help: Optional[str] = None
    n_channels: int = 1

    # Components (as raw data, converted to objects via properties)
    params_data: List[Dict[str, Any]] = field(default_factory=list)
    outlets_data: List[Dict[str, Any]] = field(default_factory=list)
    message_methods_data: List[Dict[str, Any]] = field(default_factory=list)
    type_methods_data: List[Dict[str, Any]] = field(default_factory=list)
    meta: Optional[Dict[str, Any]] = None

    # Helper components (initialized in __post_init__)
    type_mapper: TypeMapper = field(init=False)
    arg_builder: ArgumentBuilder = field(init=False)
    code_generator: CodeGenerator = field(init=False)

    def __post_init__(self):
        # Set defaults
        if self.alias is None:
            self.alias = self.name

        # Initialize helper components
        self.type_mapper = TypeMapper()
        self.arg_builder = ArgumentBuilder(self.type_mapper)
        self.code_generator = CodeGenerator(self.type_mapper, self.arg_builder)

    @property
    def type(self) -> str:
        """Get the C type name for this external."""
        return f"t_{self.name}"

    @property
    def klass(self) -> str:
        """Get the C class name for this external."""
        return f"{self.name}_class"

    # Backward compatibility properties
    @property
    def mapping(self) -> Dict[str, str]:
        """Get type mappings (for backward compatibility)."""
        return self.type_mapper.TYPE_MAPPINGS

    @property
    def func_type_args(self) -> Dict[str, str]:
        """Get function type arguments (for backward compatibility)."""
        return self.type_mapper.FUNC_TYPE_ARGS

    @property
    def param_objects(self) -> List[Param]:
        """Convert raw param data to Param objects."""
        result = []
        for param_data in self.params_data:
            param = Param(
                parent=self,
                name=param_data["name"],
                type=param_data["type"],
                initial=param_data.get("initial", 0),
                is_arg=param_data.get("arg", False),
                has_inlet=param_data.get("inlet", False),
                desc=param_data.get("desc", ""),
                min=param_data.get("min"),
                max=param_data.get("max"),
            )
            result.append(param)
        return result

    @property
    def args(self) -> List[Param]:
        """Get parameters that are constructor arguments."""
        return [p for p in self.param_objects if p.is_arg]

    @property
    def inlets(self) -> List[Param]:
        """Get parameters that have inlets."""
        return [p for p in self.param_objects if p.has_inlet]

    @property
    def outlet_objects(self) -> List[Outlet]:
        """Convert raw outlet data to Outlet objects."""
        return [
            Outlet(parent=self, name=o["name"], type=o["type"])
            for o in self.outlets_data
        ]

    @property
    def type_method_objects(self) -> List[TypeMethod]:
        """Convert raw type method data to TypeMethod objects."""
        return [
            TypeMethod(parent=self, type=m["type"], doc=m.get("doc", ""))
            for m in self.type_methods_data
        ]

    @property
    def message_method_objects(self) -> List[MessageMethod]:
        """Convert raw message method data to MessageMethod objects."""
        result = []
        for method_data in self.message_methods_data:
            method = MessageMethod(
                parent=self,
                name=method_data["name"],
                params=method_data.get("params", []),
                doc=method_data.get("doc", ""),
            )
            result.append(method)
        return result

    @property
    def class_new_args(self) -> str:
        """Generate C function arguments for the external constructor."""
        return self.arg_builder.build_constructor_args(self.args)

    @property
    def class_type_signature(self) -> str:
        """Generate PureData class type signature."""
        return self.arg_builder.build_type_signature(self.args)

    @property
    def class_addcreator(self) -> str:
        """Generate class_addcreator call for alias."""
        return self.code_generator.generate_creator_call(
            self.name, self.alias, self.class_type_signature
        )

    # Backward compatibility properties for templates
    @property
    def params(self) -> List[Param]:
        """Backward compatibility: get param objects (templates expect this name)."""
        return self.param_objects

    @property
    def outlets(self) -> List[Outlet]:
        """Backward compatibility: get outlet objects (templates expect this name)."""
        return self.outlet_objects

    @property
    def type_methods(self) -> List[TypeMethod]:
        """Backward compatibility: get type method objects (templates expect this name)."""
        return self.type_method_objects

    @property
    def message_methods(self) -> List[MessageMethod]:
        """Backward compatibility: get message method objects (templates expect this name)."""
        return self.message_method_objects


# ----------------------------------------------------------------------------
# MAIN CLASS


class Generator:
    """
    Base class for managing external project generation and file operations.

    This class handles the common functionality for generating audio externals,
    including YAML processing, template rendering, and file operations.

    Attributes:
        spec_yml: Path to the YAML specification file
        fullname: Full name of the external (including ~ for DSP externals)
        name: Clean name without DSP suffix
        is_dsp: Whether this is a DSP (signal processing) external
        target_dir: Directory where generated files will be placed
        project_path: Full path to the generated project directory
        model: External object created from YAML data
    """

    def __init__(
        self, spec_yml: Union[str, Path], target_dir: str = OUTPUT_DIR
    ) -> None:
        """
        Initialize generator with specification file and target directory.

        Args:
            spec_yml: Path to YAML specification file
            target_dir: Directory for generated output (default: "build")
        """
        self.spec_yml: Path = Path(spec_yml)
        self.fullname: str = Path(spec_yml).stem
        self.name: str = self.fullname.strip("~")
        self.is_dsp: bool = self.fullname.endswith("~")
        self.target_dir: Path = Path(target_dir)
        self.project_path: Path = self.target_dir / self.fullname
        self.model: Optional[External] = None

    def cmd(self, command_args: List[str]) -> str:
        """
        Execute command safely using subprocess.

        Args:
            command_args: List of command arguments to execute

        Returns:
            Command stdout output

        Raises:
            subprocess.CalledProcessError: If command fails
        """
        try:
            result = subprocess.run(
                command_args, check=True, capture_output=True, text=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"Command failed: {' '.join(command_args)}")
            print(f"Error: {e.stderr}")
            raise

    def generate(self) -> None:
        """Generate the external project. Override this in subclasses."""
        raise NotImplementedError("Subclasses must implement generate()")

    def validate_yaml_structure(self, yml_data: Dict[str, Any]) -> bool:
        """
        Validate YAML structure and required fields.

        Args:
            yml_data: Parsed YAML data to validate

        Returns:
            True if validation passes

        Raises:
            ValueError: If YAML structure is invalid
        """
        if not isinstance(yml_data, dict):
            raise ValueError("YAML file must contain a dictionary")

        if "externals" not in yml_data:
            raise ValueError("YAML file must contain 'externals' key")

        if (
            not isinstance(yml_data["externals"], list)
            or len(yml_data["externals"]) == 0
        ):
            raise ValueError("'externals' must be a non-empty list")

        ext = yml_data["externals"][0]
        required_fields = ["name", "namespace"]
        for required_field in required_fields:
            if required_field not in ext:
                raise ValueError(
                    f"External must contain required field: '{required_field}'"
                )

        # Validate optional fields have correct types
        if "params" in ext and not isinstance(ext["params"], list):
            raise ValueError("'params' must be a list")

        if "outlets" in ext and not isinstance(ext["outlets"], list):
            raise ValueError("'outlets' must be a list")

        if "message_methods" in ext and not isinstance(ext["message_methods"], list):
            raise ValueError("'message_methods' must be a list")

        if "type_methods" in ext and not isinstance(ext["type_methods"], list):
            raise ValueError("'type_methods' must be a list")

        # Validate parameter structures
        for param in ext.get("params", []):
            if not isinstance(param, dict):
                raise ValueError("Each parameter must be a dictionary")
            param_required = ["name", "type"]
            for required_field in param_required:
                if required_field not in param:
                    raise ValueError(
                        f"Parameter must contain required field: '{required_field}'"
                    )

        return True

    def render(self, template: str, outfile: Optional[str] = None) -> None:
        """
        Render a template file with YAML data and write output.

        This method handles the complete rendering pipeline:
        1. Load and validate YAML specification
        2. Create External object from YAML data
        3. Render template with External object
        4. Write rendered output to file

        Args:
            template: Path to template file relative to templates directory
            outfile: Output filename (default: external_name.c)

        Raises:
            FileNotFoundError: If YAML or template file not found
            ValueError: If YAML validation, External creation, or rendering fails
        """
        try:
            with open(self.spec_yml) as f:
                yml: Dict[str, Any] = yaml.safe_load(f.read())
        except FileNotFoundError:
            raise FileNotFoundError(
                f"YAML specification file not found: {self.spec_yml}"
            )
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax in {self.spec_yml}: {e}")

        # Validate YAML structure
        self.validate_yaml_structure(yml)
        ext_yml: Dict[str, Any] = yml["externals"][0]

        try:
            template_path: Path = TEMPLATE_DIR / template
            templ = Template(filename=str(template_path))
        except Exception as e:
            raise ValueError(f"Template file not found or invalid: {template}: {e}")

        try:
            # Map YAML data to External dataclass fields
            external_data: Dict[str, Any] = {
                "name": ext_yml["name"],
                "namespace": ext_yml["namespace"],
                "prefix": ext_yml.get("prefix", ""),
                "alias": ext_yml.get("alias"),
                "help": ext_yml.get("help"),
                "n_channels": ext_yml.get("n_channels", 1),
                "params_data": ext_yml.get("params", []),
                "outlets_data": ext_yml.get("outlets", []),
                "message_methods_data": ext_yml.get("message_methods", []),
                "type_methods_data": ext_yml.get("type_methods", []),
                "meta": ext_yml.get("meta"),
            }
            self.model = external = External(**external_data)
        except Exception as e:
            raise ValueError(f"Failed to create External object from YAML data: {e}")

        try:
            rendered: str = str(templ.render(e=external))
        except Exception as e:
            raise ValueError(f"Template rendering failed: {e}")

        if not outfile:
            outfile = self.fullname + ".c"
        target: Path = self.project_path / outfile

        try:
            with open(target, "w") as f:
                f.write(rendered)
            print(target, "rendered")
        except Exception as e:
            raise ValueError(f"Failed to write output file {target}: {e}")


class MaxProject(Generator):
    """
    Generator for Max/MSP external projects.

    This class specializes the base Generator for creating Max/MSP externals,
    handling the specific templates and file structure required for Max/MSP.

    Example:
        >>> project = MaxProject('counter.yml')
        >>> project.generate()
        # Creates Max/MSP external in build/counter/
    """

    def generate(self) -> None:
        """
        Generate Max/MSP external project with all required files.

        Creates the project directory and renders the appropriate templates
        for Max/MSP externals, including support for both regular and DSP externals.

        Raises:
            OSError: If project directory cannot be created
            ValueError: If template rendering fails
        """
        try:
            Path(OUTPUT_DIR).mkdir(exist_ok=True)
            self.project_path.mkdir(exist_ok=True)
        except OSError as e:
            if self.project_path.exists():
                print(
                    f"Warning: {self.project_path} already exists, files may be overwritten"
                )
            else:
                raise OSError(
                    f"Failed to create project directory {self.project_path}: {e}"
                )

        # Render appropriate external template based on type
        if self.is_dsp:
            self.render("mx/dsp-external.cpp.mako")
        else:
            self.render("mx/external.cpp.mako")

        # Generate documentation
        self.render("mx/README.md.mako", "README.md")


class PdProject(Generator):
    """
    Generator for PureData external projects.

    This class specializes the base Generator for creating PureData externals,
    handling the specific templates, Makefiles, and file structure required for PD.

    Example:
        >>> project = PdProject('counter.yml')
        >>> project.generate()
        # Creates PureData external in build/counter/
    """

    def generate(self) -> None:
        """
        Generate PureData external project with all required files.

        Creates the project directory and renders the appropriate templates
        for PureData externals, including Makefiles and support files.

        The generation process:
        1. Creates project directory structure
        2. Copies pdlibbuilder Makefile for compilation
        3. Renders appropriate C source template (regular or DSP)
        4. Generates project-specific Makefile
        5. Creates README documentation

        Raises:
            OSError: If project directory cannot be created
            ValueError: If template rendering fails
        """
        try:
            Path(OUTPUT_DIR).mkdir(exist_ok=True)
            self.project_path.mkdir(exist_ok=True)
        except OSError as e:
            if self.project_path.exists():
                print(
                    f"Warning: {self.project_path} already exists, files may be overwritten"
                )
            else:
                raise OSError(
                    f"Failed to create project directory {self.project_path}: {e}"
                )

        # Copy pdlibbuilder Makefile for compilation support
        src_makefile: Path = Path("resources/pd/Makefile.pdlibbuilder")
        dst_makefile: Path = self.project_path / "Makefile.pdlibbuilder"
        shutil.copy2(src_makefile, dst_makefile)

        # Render appropriate external template based on type
        if self.is_dsp:
            self.render("pd/dsp-external.c.mako")
        else:
            self.render("pd/external.c.mako")

        # Generate build system and documentation
        self.render("pd/Makefile.mako", "Makefile")
        self.render("pd/README.md.mako", "README.md")


# ----------------------------------------------------------------------------
# MAIN CLASS

if __name__ == "__main__":
    p = PdProject("resources/examples/counter.yml")
    # p = MaxProject("resources/examples/counter.yml")
    p.generate()
