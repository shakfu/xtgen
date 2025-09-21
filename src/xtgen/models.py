"""Data models for xtgen external specifications.

This module contains the dataclass definitions and type system for representing
audio externals and their components (parameters, outlets, methods, etc.).
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union


class AudioTypeError(ValueError):
    """Custom exception for audio type validation errors."""
    pass


def c_type(type_name: str) -> str:
    """Generate C type name from audio type."""
    return f"t_{type_name}"


def lookup_address(symbol: str) -> str:
    """Generate symbol lookup address."""
    return f"&s_{symbol}"


def lookup_routine(symbol: str) -> str:
    """Generate symbol lookup routine."""
    return f'gensym("{symbol}")'


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
    type_mapper: "TypeMapper" = field(init=False)
    arg_builder: "ArgumentBuilder" = field(init=False)
    code_generator: "CodeGenerator" = field(init=False)

    def __post_init__(self):
        # Delay import to avoid circular dependencies
        from .generators import TypeMapper, ArgumentBuilder, CodeGenerator

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