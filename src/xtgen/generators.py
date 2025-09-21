"""Code generation utilities for xtgen externals.

This module contains the helper classes responsible for generating C code
snippets, managing type mappings, and building function arguments for
audio externals.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional

from .models import AudioTypeError


class TypeMapper:
    """Handles mapping between audio types and C code representations.

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
        """Get PureData API constant for a given audio type.

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
        """Get C function argument string for a given audio type.

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
    """Builds C function arguments for various external components.

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
        """Initialize ArgumentBuilder with a TypeMapper instance.

        Args:
            type_mapper: TypeMapper instance for type conversions
        """
        self.type_mapper = type_mapper

    def build_constructor_args(self, args: List["Param"]) -> str:
        """Build C constructor arguments for external creation.

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
        """Build PureData class type signature for registration.

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
        """Build C function arguments for message methods.

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
    """Generates C code snippets for external components.

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
        """Initialize CodeGenerator with required helper instances.

        Args:
            type_mapper: TypeMapper instance for type conversions
            arg_builder: ArgumentBuilder instance for argument construction
        """
        self.type_mapper = type_mapper
        self.arg_builder = arg_builder

    def generate_class_addmethod(
        self, external_name: str, method_name: str, method_type: str
    ) -> str:
        """Generate class_add method call for type methods.

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
        """Generate class_addmethod call for message methods.

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
        """Generate class_addcreator call for external alias.

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