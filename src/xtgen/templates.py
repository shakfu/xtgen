"""Template rendering and project generation for xtgen externals.

This module contains the project generator classes responsible for rendering
templates and creating complete projects for each target in TARGETS.
"""

import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Union, List, Tuple

try:
    from importlib.resources import files, as_file
except ImportError:
    from importlib_resources import files, as_file

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from mako.lookup import TemplateLookup

from .dsp import DspGraph, load_graph
from .models import External


def get_package_resource_path(resource_path: str) -> Path:
    """Get path to a package resource file."""
    try:
        # Try to get the traversable path
        resource_files = files("xtgen") / resource_path
        # Use as_file context manager for proper handling
        with as_file(resource_files) as path:
            return Path(str(path))
    except Exception:
        # Fallback to the directory this file is in
        return Path(__file__).parent / resource_path


# Get the directory containing this script
SCRIPT_DIR = Path(__file__).parent
TEMPLATE_DIR = get_package_resource_path("resources/templates")
TEMPLATE_LOOKUP = TemplateLookup(directories=[str(TEMPLATE_DIR)])
OUTPUT_DIR = "build"


class Generator:
    """
    Base class for managing external project generation and file operations.

    This class handles the common functionality for generating audio externals,
    including YAML processing, template rendering, and file operations.

    Attributes:
        spec_yml: Path to the YAML specification file
        fullname: Full name of the external (including ~ for DSP externals),
            reset from the spec's 'name' on render
        name: Clean name without DSP suffix
        is_dsp: Whether this is a DSP external (spec filename ends in ~)
        target_dir: Directory where generated files will be placed
        project_path: Full path to the generated project directory
        model: External object created from YAML data
    """

    def __init__(
        self, spec_file: Union[str, Path], target_dir: str = OUTPUT_DIR
    ) -> None:
        """Initialize generator with specification file and target directory.

        Args:
            spec_file: Path to YAML or JSON specification file
            target_dir: Directory for generated output (default: "build")
        """
        self.spec_file: Path = Path(spec_file)
        self.fullname: str = Path(spec_file).stem
        self.name: str = self.fullname.strip("~")
        self.is_dsp: bool = self.fullname.endswith("~")
        self.target_dir: Path = Path(target_dir)
        self.project_path: Path = self.target_dir / self.fullname
        self.model: Optional[External] = None
        self.dsp: Optional[DspGraph] = None  # set from the spec's 'dsp' field

    def cmd(self, command_args: List[str]) -> str:
        """Execute command safely using subprocess.

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

    def load_specification(self) -> Dict[str, Any]:
        """Load and parse specification file (YAML or JSON).

        Returns:
            Parsed specification data as dictionary

        Raises:
            FileNotFoundError: If specification file not found
            ValueError: If file format is invalid or unsupported
        """
        if not self.spec_file.exists():
            raise FileNotFoundError(f"Specification file not found: {self.spec_file}")

        file_extension = self.spec_file.suffix.lower()

        try:
            with open(self.spec_file, 'r', encoding='utf-8') as f:
                if file_extension in ['.yml', '.yaml']:
                    if not YAML_AVAILABLE:
                        raise ValueError(
                            "YAML files are not supported. PyYAML package is not installed. "
                            "Install with: pip install PyYAML"
                        )
                    return yaml.safe_load(f.read())
                elif file_extension == '.json':
                    return json.load(f)
                else:
                    # Try YAML first (if available), then JSON as fallback
                    content = f.read()
                    if YAML_AVAILABLE:
                        try:
                            return yaml.safe_load(content)
                        except yaml.YAMLError:
                            pass

                    try:
                        return json.loads(content)
                    except json.JSONDecodeError as json_err:
                        supported_exts = ".json"
                        if YAML_AVAILABLE:
                            supported_exts = ".yml, .yaml, .json"
                        raise ValueError(
                            f"File {self.spec_file} is not valid JSON"
                            f"{' or YAML' if YAML_AVAILABLE else ''}. "
                            f"JSON error: {json_err}. "
                            f"Supported extensions: {supported_exts}"
                        )
        except Exception as e:
            if YAML_AVAILABLE and hasattr(e, '__class__') and 'yaml' in str(e.__class__).lower():
                raise ValueError(f"Invalid YAML syntax in {self.spec_file}: {e}")
            elif isinstance(e, json.JSONDecodeError):
                raise ValueError(f"Invalid JSON syntax in {self.spec_file}: {e}")
            else:
                raise

    def generate(self, force: bool = False) -> None:
        """Generate the external project. Override this in subclasses."""
        raise NotImplementedError("Subclasses must implement generate()")

    def make_project_dir(self, force: bool = False) -> None:
        """Validate the specification, then create the project directory.

        Raises:
            ValueError: If the specification is invalid
            FileExistsError: If the directory is non-empty and force is False
            OSError: If the directory cannot be created
        """
        # Validate before writing anything, so a bad spec leaves no partial project.
        self.validate()

        if not force and self.project_path.is_dir() and any(self.project_path.iterdir()):
            raise FileExistsError(
                f"{self.project_path} already exists and is not empty"
            )
        try:
            self.project_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise OSError(
                f"Failed to create project directory {self.project_path}: {e}"
            )

    def validate(self) -> Dict[str, Any]:
        """Load the specification and apply this target's rules without writing.

        Returns:
            Parsed specification data

        Raises:
            FileNotFoundError: If specification file not found
            ValueError: If the specification is invalid for this target
        """
        spec_data = self.load_specification()
        self.validate_specification_structure(spec_data)
        self.build_external(spec_data["externals"][0])
        return spec_data

    EXTERNAL_KEYS = frozenset({
        "name", "namespace", "prefix", "alias", "help", "n_channels",
        "params", "outlets", "message_methods", "type_methods", "meta", "dsp",
    })
    TARGET = "pd"  # name used in error messages
    SUPPORTS_DSP_GRAPH = False
    UNUSED_KEYS: Tuple[str, ...] = ()  # fields this target has no use for; rejected
    DSP_NEEDS_TILDE = True  # pd and max embed a graph only in a signal ('~') external

    def load_dsp(self, ext: Dict[str, Any]) -> None:
        """Compile the spec's 'dsp' graph and replace its params with the graph's.

        Raises:
            ValueError: If this target cannot embed a graph, or the graph is invalid
        """
        if not self.SUPPORTS_DSP_GRAPH:
            raise ValueError(f"'dsp' is not supported by the {self.TARGET} target yet")
        if not isinstance(ext["dsp"], str):
            raise ValueError("'dsp' must be a path to a .gdsp file")
        if self.DSP_NEEDS_TILDE and not self.is_dsp:
            raise ValueError(
                "'dsp' needs a signal external: name the spec file "
                f"'{self.spec_file.stem}~{self.spec_file.suffix}'"
            )
        # Taken from the graph, so the spec cannot disagree with it.
        given = [k for k in ("params", "n_channels") if k in ext]
        if given:
            raise ValueError(
                f"{', '.join(map(repr, given))} come(s) from the 'dsp' graph; "
                "remove from the spec"
            )
        if self.dsp is None:
            self.dsp = load_graph(self.spec_file.parent / ext["dsp"], f"{ext['name']}_dsp")
        ext["params"] = [dict(p) for p in self.dsp.params]
        # Each graph param is a method of the same name; dsp/dsp64/assist are built in.
        taken = {p["name"] for p in self.dsp.params} | {"dsp", "dsp64", "assist"}
        for m in ext.get("message_methods", []):
            if m.get("name") in taken:
                raise ValueError(
                    f"Message method {m['name']!r} has the name of a graph param "
                    "or of a built-in method"
                )

    def write_dsp(self, subdir: str = "") -> None:
        """Write the compiled graph and its header next to the generated source."""
        if self.dsp is None:
            return
        for suffix, text in ((".c", self.dsp.c_code), (".h", self.dsp.header)):
            target = self.project_path / subdir / (self.dsp.prefix + suffix)
            target.write_text(text)
            print(target, "rendered")

    def validate_specification_structure(self, spec_data: Dict[str, Any]) -> bool:
        """Validate specification structure and required fields.

        Args:
            spec_data: Parsed specification data (YAML or JSON) to validate

        Returns:
            True if validation passes

        Raises:
            ValueError: If specification structure is invalid
        """
        if not isinstance(spec_data, dict):
            raise ValueError("Specification file must contain a dictionary")

        if "externals" not in spec_data:
            raise ValueError("Specification file must contain 'externals' key")

        if (
            not isinstance(spec_data["externals"], list)
            or len(spec_data["externals"]) == 0
        ):
            raise ValueError("'externals' must be a non-empty list")

        # Project path and filenames derive from the spec file stem: one external per file.
        if len(spec_data["externals"]) > 1:
            raise ValueError(
                f"'externals' must contain exactly one external, got "
                f"{len(spec_data['externals'])}; use one specification file per external"
            )

        ext = spec_data["externals"][0]
        required_fields = ["name", "namespace"]
        for required_field in required_fields:
            if required_field not in ext:
                raise ValueError(
                    f"External must contain required field: '{required_field}'"
                )

        # build_external reads only these keys; reject others rather than drop them.
        if "inlets" in ext:
            raise ValueError(
                "'inlets' is not supported; set 'inlet: true' on each param instead"
            )
        unknown = sorted(set(ext) - self.EXTERNAL_KEYS)
        if unknown:
            raise ValueError(
                f"External contains unknown field(s): {', '.join(map(repr, unknown))}"
            )
        unused = [k for k in self.UNUSED_KEYS if k in ext]
        # Channels only exist on signal objects.
        if not self.is_dsp and "n_channels" in ext and self.TARGET in ("pd", "max"):
            unused.append("n_channels")
        if unused:
            raise ValueError(
                f"Field(s) not supported by the {self.TARGET} target: "
                f"{', '.join(map(repr, unused))}"
                + ("; n_channels needs a signal object ('~' spec filename)"
                   if "n_channels" in unused else "")
            )
        if "dsp" in ext:
            self.load_dsp(ext)

        # Validate optional fields have correct types
        if "params" in ext and not isinstance(ext["params"], list):
            raise ValueError("'params' must be a list")

        if "outlets" in ext and not isinstance(ext["outlets"], list):
            raise ValueError("'outlets' must be a list")

        if "message_methods" in ext and not isinstance(ext["message_methods"], list):
            raise ValueError("'message_methods' must be a list")

        if "type_methods" in ext and not isinstance(ext["type_methods"], list):
            raise ValueError("'type_methods' must be a list")

        # Validate component structures: (spec key, label, required fields)
        components = [
            ("params", "Parameter", ["name", "type"]),
            ("outlets", "Outlet", ["name", "type"]),
            ("message_methods", "Message method", ["name"]),
            ("type_methods", "Type method", ["type"]),
        ]
        for key, label, component_required in components:
            for item in ext.get(key, []):
                if not isinstance(item, dict):
                    raise ValueError(f"Each {label.lower()} must be a dictionary")
                for required_field in component_required:
                    if required_field not in item:
                        raise ValueError(
                            f"{label} must contain required field: '{required_field}'"
                        )

        # Every template renders these meta keys.
        meta = ext.get("meta")
        if not isinstance(meta, dict):
            raise ValueError("External must contain a 'meta' dictionary")
        for required_field in ["desc", "features", "author", "repo"]:
            if required_field not in meta:
                raise ValueError(f"'meta' must contain required field: '{required_field}'")

        return True

    def build_external(self, ext_data: Dict[str, Any]) -> External:
        """Build an External and its components from validated specification data.

        Args:
            ext_data: One entry of the specification's 'externals' list

        Returns:
            External whose params, outlets and methods have been type-checked

        Raises:
            ValueError: If a field or component type is invalid
        """
        try:
            external = External(
                name=ext_data["name"],
                namespace=ext_data["namespace"],
                prefix=ext_data.get("prefix", ""),
                alias=ext_data.get("alias"),
                help=ext_data.get("help"),
                n_channels=ext_data.get("n_channels", 1),
                is_dsp=self.is_dsp,
                params_data=ext_data.get("params", []),
                outlets_data=ext_data.get("outlets", []),
                message_methods_data=ext_data.get("message_methods", []),
                type_methods_data=ext_data.get("type_methods", []),
                meta=ext_data.get("meta"),
                dsp=self.dsp if "dsp" in ext_data else None,
            )
            # Components are built lazily; build them now so type errors surface here.
            external.param_objects
            external.outlet_objects
            external.message_method_objects
            external.type_method_objects
        except Exception as e:
            raise ValueError(f"Failed to create External object from specification data: {e}")
        return external

    def render(self, template: str, outfile: Optional[str] = None) -> None:
        """Render a template file with specification data and write output.

        This method handles the complete rendering pipeline:
        1. Load and validate specification (YAML or JSON)
        2. Create External object from specification data
        3. Render template with External object
        4. Write rendered output to file

        Args:
            template: Path to template file relative to templates directory
            outfile: Output filename (default: external_name.c)

        Raises:
            FileNotFoundError: If specification or template file not found
            ValueError: If specification validation, External creation, or rendering fails
        """
        # Load specification using the new unified method
        spec_data: Dict[str, Any] = self.load_specification()

        # Validate specification structure
        self.validate_specification_structure(spec_data)
        ext_data: Dict[str, Any] = spec_data["externals"][0]

        try:
            # Through the lookup, so templates can import shared defs (<%namespace>).
            templ = TEMPLATE_LOOKUP.get_template(template)
        except Exception as e:
            raise ValueError(f"Template file not found or invalid: {template}: {e}")

        self.model = external = self.build_external(ext_data)

        # Output and Makefile names follow the spec's 'name', as the C setup function does.
        self.name = external.name
        self.fullname = external.name + ("~" if self.is_dsp else "")

        try:
            rendered: str = str(templ.render(e=external, fullname=self.fullname))
        except Exception as e:
            raise ValueError(f"Template rendering failed: {e}")

        if not outfile:
            outfile = self.fullname + ".c"
        target: Path = self.project_path / outfile

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w") as f:
                f.write(rendered)
            print(target, "rendered")
        except Exception as e:
            raise ValueError(f"Failed to write output file {target}: {e}")


class PluginProject(Generator):
    """Base for plugin targets, which have no Pd object model.

    Plugins always process audio, so a '~' in the spec filename is dropped
    rather than switching to a DSP template.
    """

    # Pd/Max object-model fields with no plugin equivalent.
    PD_ONLY_KEYS = ("prefix", "alias", "help", "outlets", "message_methods", "type_methods")
    TARGET = "plugin"  # name used in error messages
    DSP_NEEDS_TILDE = False

    def __init__(
        self, spec_file: Union[str, Path], target_dir: str = OUTPUT_DIR
    ) -> None:
        super().__init__(spec_file, target_dir)
        self.is_dsp = False
        self.fullname = self.name
        self.project_path = self.target_dir / self.name

    def validate_specification_structure(self, spec_data: Dict[str, Any]) -> bool:
        """Validate as for Pd, then reject fields the plugin target cannot express.

        Raises:
            ValueError: If the specification uses Pd-only fields or invalid params
        """
        super().validate_specification_structure(spec_data)
        ext = spec_data["externals"][0]
        target = self.TARGET

        pd_only = [k for k in self.PD_ONLY_KEYS if k in ext]
        if pd_only:
            raise ValueError(
                f"Field(s) not supported by the {target} target: "
                f"{', '.join(map(repr, pd_only))}"
            )
        # Names become C/C++ identifiers, plugin ids and VCV slugs.
        for key in ("name", "namespace"):
            if not (isinstance(ext[key], str) and ext[key].isascii() and ext[key].isidentifier()):
                raise ValueError(f"'{key}' must be an ASCII identifier, got {ext[key]!r}")
        n_channels = ext.get("n_channels", 1)
        if type(n_channels) is not int or n_channels < 1:
            raise ValueError(f"'n_channels' must be a positive integer, got {n_channels!r}")

        for p in ext.get("params", []):
            name = p["name"]
            if not (isinstance(name, str) and name.isascii() and name.isidentifier()):
                raise ValueError(f"Parameter name must be an ASCII identifier, got {name!r}")
            if p["type"] != "float":
                raise ValueError(
                    f"Parameter '{name}': the {target} target supports only float params"
                )
            if p.get("arg"):
                raise ValueError(
                    f"Parameter '{name}': 'arg' is not supported by the {target} target"
                )
            for bound in ("min", "max"):
                if bound not in p:
                    raise ValueError(f"Parameter '{name}' must set '{bound}'")
            values = (p["min"], p.get("initial", 0), p["max"])
            if not all(
                isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
                for v in values
            ):
                raise ValueError(
                    f"Parameter '{name}': min, initial and max must be finite numbers"
                )
            if not values[0] <= values[1] <= values[2] or values[0] == values[2]:
                raise ValueError(
                    f"Parameter '{name}' needs min < max and min <= initial <= max, "
                    f"got min={values[0]}, initial={values[1]}, max={values[2]}"
                )
        return True


class ClapProject(PluginProject):
    """Generator for CLAP plugins; CMake wraps the CLAP as VST3 and AUv2.

    Example:
        >>> ClapProject('gain.yml').generate()
        # Creates build/gain/ with gain.c, gain_entry.cpp, CMakeLists.txt
    """

    TARGET = "clap"
    SUPPORTS_DSP_GRAPH = True

    def generate(self, force: bool = False) -> None:
        """Generate the CLAP project.

        Raises:
            FileExistsError: If project directory is non-empty and force is False
            OSError: If project directory cannot be created
            ValueError: If the specification is invalid or rendering fails
        """
        self.make_project_dir(force)
        self.render("clap/plugin.c.mako")
        self.render("clap/entry.cpp.mako", f"{self.name}_entry.cpp")
        self.render("clap/CMakeLists.txt.mako", "CMakeLists.txt")
        self.render("clap/README.md.mako", "README.md")
        self.write_dsp()


class VcvProject(PluginProject):
    """Generator for VCV Rack 2 plugins with one module.

    Example:
        >>> VcvProject('gain.yml').generate()
        # Creates build/gain/ with plugin.json, Makefile, src/, res/
    """

    TARGET = "vcv"
    SUPPORTS_DSP_GRAPH = True

    def generate(self, force: bool = False) -> None:
        """Generate the VCV Rack plugin project.

        Raises:
            FileExistsError: If project directory is non-empty and force is False
            OSError: If project directory cannot be created
            ValueError: If the specification is invalid or rendering fails
        """
        self.make_project_dir(force)
        shutil.copy2(
            get_package_resource_path("resources/vcv/Makefile"), self.project_path / "Makefile"
        )
        module = self.name[0].upper() + self.name[1:]
        self.render("vcv/plugin.hpp.mako", "src/plugin.hpp")
        self.render("vcv/plugin.cpp.mako", "src/plugin.cpp")
        self.render("vcv/module.cpp.mako", f"src/{module}.cpp")
        self.render("vcv/panel.svg.mako", f"res/{module}.svg")
        self.render("vcv/README.md.mako", "README.md")
        self.write_dsp("src")

        # Written with json.dumps, not a template, so spec strings are escaped.
        assert self.model is not None and self.model.meta is not None
        meta = self.model.meta
        manifest = {
            "slug": self.model.namespace,
            "name": self.model.namespace,
            "version": "2.0.0",
            "brand": self.model.namespace,
            "author": meta["author"],
            "sourceUrl": meta["repo"],
            "modules": [
                {
                    "slug": module,
                    "name": self.model.name,
                    "description": " ".join(str(meta["desc"]).split()),
                    # A graph with no audio inputs is a generator, not an effect.
                    "tags": [] if self.dsp and not self.dsp.n_inputs else ["Effect"],
                }
            ],
        }
        target = self.project_path / "plugin.json"
        target.write_text(json.dumps(manifest, indent=2) + "\n")
        print(target, "rendered")


class MaxProject(Generator):
    """Generator for Max/MSP external projects.

    This class specializes the base Generator for creating Max/MSP externals,
    handling the specific templates and file structure required for Max/MSP.

    Example:
        >>> project = MaxProject('counter.yml')
        >>> project.generate()
        # Creates Max/MSP external in build/counter/
    """

    TARGET = "max"
    SUPPORTS_DSP_GRAPH = True
    UNUSED_KEYS = ("help",)  # the Max SDK has no call to name a help file

    def validate_specification_structure(self, spec_data: Dict[str, Any]) -> bool:
        """Validate as for Pd, then reject type methods Max has no message for.

        Raises:
            ValueError: If the specification is invalid for Max
        """
        super().validate_specification_structure(spec_data)
        for m in spec_data["externals"][0].get("type_methods", []):
            if m["type"] == "pointer":
                raise ValueError("Type method 'pointer' is not supported by the max target")
        return True

    def generate(self, force: bool = False) -> None:
        """Generate Max/MSP external project with all required files.

        Creates the project directory and renders the appropriate templates
        for Max/MSP externals, including support for both regular and DSP externals.

        Args:
            force: Overwrite files in an existing, non-empty project directory

        Raises:
            FileExistsError: If project directory is non-empty and force is False
            OSError: If project directory cannot be created
            ValueError: If template rendering fails
        """
        self.make_project_dir(force)

        # Render appropriate external template based on type
        if self.dsp:
            self.render("mx/graph-external.c.mako")
        elif self.is_dsp:
            self.render("mx/dsp-external.c.mako")
        else:
            self.render("mx/external.c.mako")

        # Generate documentation
        self.render("mx/README.md.mako", "README.md")
        self.write_dsp()


class PdProject(Generator):
    """Generator for PureData external projects.

    This class specializes the base Generator for creating PureData externals,
    handling the specific templates, Makefiles, and file structure required for PD.

    Example:
        >>> project = PdProject('counter.yml')
        >>> project.generate()
        # Creates PureData external in build/counter/
    """

    SUPPORTS_DSP_GRAPH = True

    def validate_specification_structure(self, spec_data: Dict[str, Any]) -> bool:
        """Validate, then reject a float method that a signal inlet would replace.

        Raises:
            ValueError: If the specification is invalid for Pd
        """
        super().validate_specification_structure(spec_data)
        ext = spec_data["externals"][0]
        # CLASS_MAINSIGNALIN replaces the class's float method; a graph with no inputs has none.
        has_signal_inlet = self.is_dsp and (self.dsp is None or self.dsp.n_inputs > 0)
        if has_signal_inlet and any(m["type"] == "float" for m in ext.get("type_methods", [])):
            raise ValueError(
                "A 'float' type method conflicts with the main signal inlet, "
                "which Pd gives its own float method"
            )
        return True

    def generate(self, force: bool = False) -> None:
        """Generate PureData external project with all required files.

        Creates the project directory and renders the appropriate templates
        for PureData externals, including Makefiles and support files.

        The generation process:
        1. Creates project directory structure
        2. Copies pdlibbuilder Makefile for compilation
        3. Renders appropriate C source template (regular or DSP)
        4. Generates project-specific Makefile
        5. Creates README documentation

        Args:
            force: Overwrite files in an existing, non-empty project directory

        Raises:
            FileExistsError: If project directory is non-empty and force is False
            OSError: If project directory cannot be created
            ValueError: If template rendering fails
        """
        self.make_project_dir(force)

        # Copy pdlibbuilder Makefile for compilation support
        src_makefile: Path = get_package_resource_path("resources/pd/Makefile.pdlibbuilder")
        dst_makefile: Path = self.project_path / "Makefile.pdlibbuilder"
        shutil.copy2(src_makefile, dst_makefile)

        # Render appropriate external template based on type
        if self.dsp:
            self.render("pd/graph-external.c.mako")
        elif self.is_dsp:
            self.render("pd/dsp-external.c.mako")
        else:
            self.render("pd/external.c.mako")

        # Generate build system and documentation
        self.render("pd/Makefile.mako", "Makefile")
        self.render("pd/README.md.mako", "README.md")
        self.write_dsp()

# CLI target name -> generator class.
TARGETS: Dict[str, type[Generator]] = {
    "pd": PdProject,
    "max": MaxProject,
    "clap": ClapProject,
    "vcv": VcvProject,
}
