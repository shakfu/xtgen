#!/usr/bin/env python3
"""xtgen.py

A tool to generate skeleton puredata or max external files.

Requires the following python packages:

- mako
- pyyaml

## Example of Usage

>>> import xtgen

>>> xtgen.PdProject('counter.yml').generate()
>>> # generates a regular c pd external skeleton

>>> xtgen.PdProject('counter~.yml').generate()
>>> # generates an audio dsp pd external

>>> xtgen.MaxProject('counter.yml').generate()
>>> ... (similar as above)

## Model

external
    namespace
    name
    prefix
    meta
        desc
        author
        repo
    params
    inlets
    outlets
    typed_methods
    message_methods
    dsp_methods



externals:

    message_methods:
      - name: reset
        params: []
        doc: reset count to zero

      - name: bound
        params: [float, float]
        doc: set (or reset) lower and uppwer boundary of counter

      - name: step
        params: [float]
        doc: set the counter increment per step

    type_methods:
      - type: bang
        doc: each bang increments the counter

      - type: float
        doc: each number is printed out

      - type: symbol
        doc: each symbol is printed out

      - type: pointer
        doc: each pointer is printed out

      - type: list
        doc: each list is printed out

      - type: anything
        doc: enything is printed out

"""
import argparse
import os
import shutil
import subprocess
import sys
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


@dataclass
class AbstractType:
    """Base class for audio external types."""
    name: str
    VALID_TYPES: List[str] = field(default_factory=list, init=False)

    def __post_init__(self):
        if self.name not in self.VALID_TYPES:
            raise AudioTypeError(f"Invalid type '{self.name}'. Valid types: {self.VALID_TYPES}")

    def __str__(self) -> str:
        return self.name


@dataclass
class ScalarType(AbstractType):
    """Scalar audio types: bang, float, symbol, pointer, signal."""
    VALID_TYPES: List[str] = field(default_factory=lambda: ["bang", "float", "symbol", "pointer", "signal"], init=False)

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
    VALID_TYPES: List[str] = field(default_factory=lambda: ["list", "anything"], init=False)

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
    parent: 'External'
    type: str
    doc: str = ""

    VALID_TYPES = ["bang", "float", "int", "symbol", "pointer", "list", "anything"]

    def __post_init__(self):
        if self.type not in self.VALID_TYPES:
            raise AudioTypeError(f"Invalid type method '{self.type}'. Valid types: {self.VALID_TYPES}")

    @property
    def name(self) -> str:
        """Type methods are named after their type."""
        return self.type

    @property
    def args(self) -> str:
        """Generate C function arguments for this type method."""
        base_arg = f"{self.parent.type} *x"

        if self.type == "bang":
            return base_arg
        elif self.type in ["float", "int"]:
            return f"{base_arg}, t_floatarg f"
        elif self.type == "symbol":
            return f"{base_arg}, t_symbol *s"
        elif self.type == "pointer":
            return f"{base_arg}, t_gpointer *pt"
        elif self.type in ["list", "anything"]:
            return f"{base_arg}, t_symbol *s, int argc, t_atom *argv"
        else:
            raise AudioTypeError(f"Argument generation not implemented for type '{self.type}'")

    @property
    def class_addmethod(self) -> str:
        """Generate class_add method call for this type."""
        return f"class_add{self.type}({self.parent.klass}, {self.parent.name}_{self.type})"


@dataclass
class MessageMethod:
    """Represents a message method for an external."""
    parent: 'External'
    name: str
    params: List[str] = field(default_factory=list)
    doc: str = ""

    @property
    def args(self) -> str:
        """Generate C function arguments for this message method."""
        base_arg = f"{self.parent.type} *x"

        if len(self.params) == 0:
            return base_arg
        elif self.params == ["list"] or len(self.params) > 6:
            return f"{base_arg}, t_symbol *s, int argc, t_atom *argv"
        else:
            type_args = []
            for i, param_type in enumerate(self.params):
                if param_type not in self.parent.func_type_args:
                    raise AudioTypeError(f"Unknown parameter type '{param_type}' in method '{self.name}'")
                type_args.append(self.parent.func_type_args[param_type] + str(i))
            type_str = ", ".join(type_args)
            return f"{base_arg}, {type_str}"

    @property
    def class_addmethod(self) -> str:
        """Generate class_addmethod call for this message method."""
        prefix = (
            f"class_addmethod({self.parent.name}_class, "
            f"(t_method){self.parent.name}_{self.name}, "
            f'gensym("{self.name}")'
        )

        if len(self.params) == 0:
            return f"{prefix}, 0)"
        elif self.params == ["list"] or len(self.params) > 6:
            return f"{prefix}, A_GIMME, 0)"
        else:
            type_mappings = []
            for param_type in self.params:
                if param_type not in self.parent.mapping:
                    raise AudioTypeError(f"Unknown parameter mapping for type '{param_type}' in method '{self.name}'")
                type_mappings.append(self.parent.mapping[param_type])
            type_str = ", ".join(type_mappings)
            return f"{prefix}, {type_str}, 0)"


@dataclass
class Param:
    """Represents a parameter of an external."""
    parent: 'External'
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
            raise AudioTypeError(f"Invalid parameter type '{self.type}'. Valid types: {list(self.C_TYPES.keys())}")

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
    parent: 'External'
    name: str
    type: str

    def __post_init__(self):
        # Basic validation - could be expanded
        valid_outlet_types = ["float", "bang", "symbol", "list", "anything"]
        if self.type not in valid_outlet_types:
            raise AudioTypeError(f"Invalid outlet type '{self.type}'. Valid types: {valid_outlet_types}")


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

    # Class constants
    MAPPING = {
        "float": "A_DEFFLOAT",
        "symbol": "A_DEFSYMBOL",
        "anything": "A_GIMME",
    }

    FUNC_TYPE_ARGS = {
        "float": "t_floatarg f",
        "symbol": "t_symbol *s",
        "anything": "t_symbol *s, int argc, t_atom *argv",
    }

    def __post_init__(self):
        # Set defaults
        if self.alias is None:
            self.alias = self.name

    @property
    def type(self) -> str:
        """Get the C type name for this external."""
        return f"t_{self.name}"

    @property
    def klass(self) -> str:
        """Get the C class name for this external."""
        return f"{self.name}_class"

    @property
    def mapping(self) -> Dict[str, str]:
        """Get type mappings (for backward compatibility)."""
        return self.MAPPING

    @property
    def func_type_args(self) -> Dict[str, str]:
        """Get function type arguments (for backward compatibility)."""
        return self.FUNC_TYPE_ARGS

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
                max=param_data.get("max")
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
        return [Outlet(parent=self, name=o["name"], type=o["type"]) for o in self.outlets_data]

    @property
    def type_method_objects(self) -> List[TypeMethod]:
        """Convert raw type method data to TypeMethod objects."""
        return [TypeMethod(parent=self, type=m["type"], doc=m.get("doc", "")) for m in self.type_methods_data]

    @property
    def message_method_objects(self) -> List[MessageMethod]:
        """Convert raw message method data to MessageMethod objects."""
        result = []
        for method_data in self.message_methods_data:
            method = MessageMethod(
                parent=self,
                name=method_data["name"],
                params=method_data.get("params", []),
                doc=method_data.get("doc", "")
            )
            result.append(method)
        return result

    @property
    def class_new_args(self) -> str:
        """Generate C function arguments for the external constructor."""
        args = self.args
        if len(args) == 0:
            return "void"
        elif 0 < len(args) <= 6:
            type_args = []
            for i, arg in enumerate(args):
                if arg.type not in self.func_type_args:
                    raise AudioTypeError(f"Unknown argument type '{arg.type}' for external '{self.name}'")
                type_args.append(self.func_type_args[arg.type] + str(i))
            return ", ".join(type_args)
        else:
            # Use A_GIMME for many arguments
            return "t_symbol *s, int argc, t_atom *argv"

    @property
    def class_type_signature(self) -> str:
        """Generate PureData class type signature."""
        args = self.args
        suffix = ", 0"

        if len(args) == 0:
            return suffix
        elif 0 < len(args) <= 6:
            type_mappings = []
            for arg in args:
                if arg.type not in self.mapping:
                    raise AudioTypeError(f"Unknown type mapping for '{arg.type}' in external '{self.name}'")
                type_mappings.append(self.mapping[arg.type])
            return ", ".join(type_mappings) + suffix
        else:
            return "A_GIMME" + suffix

    @property
    def class_addcreator(self) -> str:
        """Generate class_addcreator call for alias."""
        if not self.alias or self.alias == self.name:
            return ""  # No alias needed
        return (
            f"class_addcreator((t_newmethod)"
            f'{self.name}_new, gensym("{self.alias}"), '
            f"{self.class_type_signature})"
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
    """main base class to manage external projects and related files."""

    def __init__(self, spec_yml, target_dir=OUTPUT_DIR):
        self.spec_yml = Path(spec_yml)
        self.fullname = Path(spec_yml).stem
        self.name = self.fullname.strip("~")
        self.is_dsp = self.fullname.endswith("~")
        self.target_dir = Path(target_dir)
        self.project_path = self.target_dir / self.fullname
        self.model = None

    def cmd(self, command_args):
        """Execute command safely using subprocess."""
        try:
            result = subprocess.run(command_args, check=True, capture_output=True, text=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"Command failed: {' '.join(command_args)}")
            print(f"Error: {e.stderr}")
            raise

    def generate(self):
        """override this"""

    def validate_yaml_structure(self, yml_data):
        """Validate YAML structure and required fields."""
        if not isinstance(yml_data, dict):
            raise ValueError("YAML file must contain a dictionary")

        if "externals" not in yml_data:
            raise ValueError("YAML file must contain 'externals' key")

        if not isinstance(yml_data["externals"], list) or len(yml_data["externals"]) == 0:
            raise ValueError("'externals' must be a non-empty list")

        ext = yml_data["externals"][0]
        required_fields = ["name", "namespace"]
        for field in required_fields:
            if field not in ext:
                raise ValueError(f"External must contain required field: '{field}'")

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
            for field in param_required:
                if field not in param:
                    raise ValueError(f"Parameter must contain required field: '{field}'")

        return True

    def render(self, template, outfile=None):
        try:
            with open(self.spec_yml) as f:
                yml = yaml.safe_load(f.read())
        except FileNotFoundError:
            raise FileNotFoundError(f"YAML specification file not found: {self.spec_yml}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax in {self.spec_yml}: {e}")

        # Validate YAML structure
        self.validate_yaml_structure(yml)
        ext_yml = yml["externals"][0]

        try:
            template_path = TEMPLATE_DIR / template
            templ = Template(filename=str(template_path))
        except Exception as e:
            raise ValueError(f"Template file not found or invalid: {template}: {e}")

        try:
            # Map YAML data to External dataclass fields
            external_data = {
                'name': ext_yml['name'],
                'namespace': ext_yml['namespace'],
                'prefix': ext_yml.get('prefix', ''),
                'alias': ext_yml.get('alias'),
                'help': ext_yml.get('help'),
                'n_channels': ext_yml.get('n_channels', 1),
                'params_data': ext_yml.get('params', []),
                'outlets_data': ext_yml.get('outlets', []),
                'message_methods_data': ext_yml.get('message_methods', []),
                'type_methods_data': ext_yml.get('type_methods', []),
                'meta': ext_yml.get('meta')
            }
            self.model = external = External(**external_data)
        except Exception as e:
            raise ValueError(f"Failed to create External object from YAML data: {e}")

        try:
            rendered = str(templ.render(e=external))
        except Exception as e:
            raise ValueError(f"Template rendering failed: {e}")

        if not outfile:
            outfile = self.fullname + ".c"
        target = self.project_path / outfile

        try:
            with open(target, "w") as f:
                f.write(rendered)
            print(target, "rendered")
        except Exception as e:
            raise ValueError(f"Failed to write output file {target}: {e}")


class MaxProject(Generator):
    """main max-centric class to manage external projects and related files."""

    def generate(self):
        try:
            Path(OUTPUT_DIR).mkdir(exist_ok=True)
            self.project_path.mkdir(exist_ok=True)
        except OSError as e:
            if self.project_path.exists():
                print(f"Warning: {self.project_path} already exists, files may be overwritten")
            else:
                raise OSError(f"Failed to create project directory {self.project_path}: {e}")

        if self.is_dsp:
            self.render("mx/dsp-external.cpp.mako")
        else:
            self.render("mx/external.cpp.mako")
        # self.render("mx/Makefile.mako", "Makefile")
        self.render("mx/README.md.mako", "README.md")


class PdProject(Generator):
    """main pd-centric class to manage external projects and related files."""

    def generate(self):
        try:
            Path(OUTPUT_DIR).mkdir(exist_ok=True)
            self.project_path.mkdir(exist_ok=True)
        except OSError as e:
            if self.project_path.exists():
                print(f"Warning: {self.project_path} already exists, files may be overwritten")
            else:
                raise OSError(f"Failed to create project directory {self.project_path}: {e}")

        # Copy pdlibbuilder Makefile safely
        src_makefile = Path("resources/pd/Makefile.pdlibbuilder")
        dst_makefile = self.project_path / "Makefile.pdlibbuilder"
        shutil.copy2(src_makefile, dst_makefile)
        if self.is_dsp:
            self.render("pd/dsp-external.c.mako")
        else:
            self.render("pd/external.c.mako")
        self.render("pd/Makefile.mako", "Makefile")
        self.render("pd/README.md.mako", "README.md")


# ----------------------------------------------------------------------------
# MAIN CLASS

if __name__ == "__main__":
    p = PdProject("resources/examples/counter.yml")
    # p = MaxProject("resources/examples/counter.yml")
    p.generate()
