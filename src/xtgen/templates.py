"""Template rendering and project generation for xtgen externals.

This module contains the project generator classes responsible for rendering
templates and creating complete external projects for both PureData and Max/MSP.
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Union, List

try:
    from importlib.resources import files, as_file
except ImportError:
    from importlib_resources import files, as_file

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from mako.template import Template
from mako.lookup import TemplateLookup

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
        fullname: Full name of the external (including ~ for DSP externals)
        name: Clean name without DSP suffix
        is_dsp: Whether this is a DSP (signal processing) external
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

    def generate(self) -> None:
        """Generate the external project. Override this in subclasses."""
        raise NotImplementedError("Subclasses must implement generate()")

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

        ext = spec_data["externals"][0]
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
            template_path: Path = TEMPLATE_DIR / template
            templ = Template(filename=str(template_path))
        except Exception as e:
            raise ValueError(f"Template file not found or invalid: {template}: {e}")

        try:
            # Map specification data to External dataclass fields
            external_data: Dict[str, Any] = {
                "name": ext_data["name"],
                "namespace": ext_data["namespace"],
                "prefix": ext_data.get("prefix", ""),
                "alias": ext_data.get("alias"),
                "help": ext_data.get("help"),
                "n_channels": ext_data.get("n_channels", 1),
                "params_data": ext_data.get("params", []),
                "outlets_data": ext_data.get("outlets", []),
                "message_methods_data": ext_data.get("message_methods", []),
                "type_methods_data": ext_data.get("type_methods", []),
                "meta": ext_data.get("meta"),
            }
            self.model = external = External(**external_data)
        except Exception as e:
            raise ValueError(f"Failed to create External object from specification data: {e}")

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
    """Generator for Max/MSP external projects.

    This class specializes the base Generator for creating Max/MSP externals,
    handling the specific templates and file structure required for Max/MSP.

    Example:
        >>> project = MaxProject('counter.yml')
        >>> project.generate()
        # Creates Max/MSP external in build/counter/
    """

    def generate(self) -> None:
        """Generate Max/MSP external project with all required files.

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
    """Generator for PureData external projects.

    This class specializes the base Generator for creating PureData externals,
    handling the specific templates, Makefiles, and file structure required for PD.

    Example:
        >>> project = PdProject('counter.yml')
        >>> project.generate()
        # Creates PureData external in build/counter/
    """

    def generate(self) -> None:
        """Generate PureData external project with all required files.

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
        src_makefile: Path = get_package_resource_path("resources/pd/Makefile.pdlibbuilder")
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