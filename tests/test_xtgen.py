#!/usr/bin/env python3
"""
Test suite for xtgen - Audio external code generator

Tests cover:
- Type system validation
- YAML parsing and external object creation
- Template variable generation
- End-to-end generation scenarios
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Generator as TypingGenerator
import os
import json
import re

from xtgen.models import (
    ScalarType,
    CompoundType,
    External,
    TypeMethod,
    MessageMethod,
    Param,
    Outlet,
    AudioTypeError,
)
from xtgen.generators import (
    TypeMapper,
    ArgumentBuilder,
    CodeGenerator,
)
from xtgen.templates import (
    Generator,
    PdProject,
    MaxProject,
    ClapProject,
    VcvProject,
    TARGETS,
    YAML_AVAILABLE,
)
from xtgen.cli import (
    main,
    create_argument_parser,
    validate_specification,
    list_examples,
    find_example,
    example_targets,
    EXAMPLES_DIR,
)
# Also import from core for backward compatibility
from xtgen import (
    ScalarType as CoreScalarType,
    CompoundType as CoreCompoundType,
    External as CoreExternal,
    TypeMethod as CoreTypeMethod,
    MessageMethod as CoreMessageMethod,
    Param as CoreParam,
    Outlet as CoreOutlet,
    PdProject as CorePdProject,
    MaxProject as CoreMaxProject,
    Generator as CoreGenerator,
    AudioTypeError as CoreAudioTypeError,
    TypeMapper as CoreTypeMapper,
    ArgumentBuilder as CoreArgumentBuilder,
    CodeGenerator as CoreCodeGenerator,
)

try:
    from importlib.resources import files
except ImportError:
    from importlib_resources import files

def get_test_resource_path(resource_path: str) -> Path:
    """Get path to a package resource file for testing."""
    resource_files = files("xtgen") / resource_path
    if hasattr(resource_files, 'as_posix'):
        return Path(str(resource_files))
    else:
        with resource_files as path:
            return Path(str(path))


class TestTypeSystem:
    """Test the audio type system classes."""

    def test_scalar_type_valid_types(self) -> None:
        """Test ScalarType with valid types."""
        for valid_type in ["bang", "float", "symbol", "pointer", "signal"]:
            scalar: ScalarType = ScalarType(valid_type)
            assert scalar.name == valid_type
            assert str(scalar) == valid_type

    def test_scalar_type_invalid_type(self) -> None:
        """Test ScalarType with invalid type raises AudioTypeError."""
        with pytest.raises(AudioTypeError):
            ScalarType("invalid_type")

    def test_scalar_type_properties(self) -> None:
        """Test ScalarType property generation."""
        float_type: ScalarType = ScalarType("float")
        assert float_type.c_type == "t_float"
        assert float_type.lookup_address == "&s_float"
        assert float_type.lookup_routine == 'gensym("float")'
        assert float_type.type_method_arg == "t_floatarg f"

    def test_compound_type_valid_types(self) -> None:
        """Test CompoundType with valid types."""
        for valid_type in ["list", "anything"]:
            compound: CompoundType = CompoundType(valid_type)
            assert compound.name == valid_type

    def test_compound_type_properties(self) -> None:
        """Test CompoundType property generation."""
        list_type: CompoundType = CompoundType("list")
        assert list_type.c_type == "t_list"
        assert list_type.type_method_arg == "t_symbol *s, int argc, t_atom *argv"

        # Test 'anything' type doesn't have c_type
        anything_type: CompoundType = CompoundType("anything")
        with pytest.raises(AudioTypeError):
            anything_type.c_type


class TestExternalModel:
    """Test External class and related components."""

    @pytest.fixture
    def sample_external_data(self) -> Dict[str, Any]:
        """Sample external data for testing."""
        return {
            "namespace": "test",
            "name": "counter",
            "prefix": "ctr",
            "alias": "cntr",
            "params_data": [
                {
                    "name": "step",
                    "type": "float",
                    "min": 0.0,
                    "max": 1.0,
                    "initial": 0.5,
                    "arg": True,
                    "inlet": True,
                    "desc": "step size",
                }
            ],
            "outlets_data": [
                {"name": "f", "type": "float"},
                {"name": "b", "type": "bang"},
            ],
            "message_methods_data": [
                {"name": "reset", "params": [], "doc": "reset counter to zero"}
            ],
            "type_methods_data": [{"type": "bang", "doc": "increment counter"}],
        }

    def test_external_creation(self, sample_external_data: Dict[str, Any]) -> None:
        """Test External object creation from data."""
        external: External = External(**sample_external_data)
        assert external.name == "counter"
        # 'prefix' names the C identifiers
        assert external.type == "t_ctr"
        assert external.klass == "ctr_class"

    def test_external_params(self, sample_external_data: Dict[str, Any]) -> None:
        """Test External params property."""
        external: External = External(**sample_external_data)
        params: List[Param] = external.params
        assert len(params) == 1
        assert params[0].name == "step"
        assert params[0].type == "float"
        assert params[0].is_arg

    def test_external_outlets(self, sample_external_data: Dict[str, Any]) -> None:
        """Test External outlets property."""
        external: External = External(**sample_external_data)
        outlets: List[Outlet] = external.outlets
        assert len(outlets) == 2
        assert outlets[0].name == "f"
        assert outlets[1].type == "bang"

    def test_external_methods(self, sample_external_data: Dict[str, Any]) -> None:
        """Test External method properties."""
        external: External = External(**sample_external_data)

        # Test message methods
        msg_methods: List[MessageMethod] = external.message_methods
        assert len(msg_methods) == 1
        assert msg_methods[0].name == "reset"

        # Test type methods
        type_methods: List[TypeMethod] = external.type_methods
        assert len(type_methods) == 1
        assert type_methods[0].type == "bang"


class TestMethodGeneration:
    """Test method generation for External objects."""

    @pytest.fixture
    def external_with_methods(self) -> External:
        """External with various method types for testing."""
        return External(
            name="test",
            namespace="test",
            message_methods_data=[
                {"name": "simple", "params": [], "doc": "simple method"},
                {"name": "with_float", "params": ["float"], "doc": "method with float"},
                {
                    "name": "with_multiple",
                    "params": ["float", "symbol"],
                    "doc": "method with multiple params",
                },
            ],
            type_methods_data=[
                {"type": "bang", "doc": "bang handler"},
                {"type": "float", "doc": "float handler"},
                {"type": "list", "doc": "list handler"},
            ],
            params_data=[],
            outlets_data=[],
        )

    def test_type_method_args(self, external_with_methods: External) -> None:
        """Test TypeMethod argument generation."""
        type_methods: List[TypeMethod] = external_with_methods.type_methods

        bang_method: TypeMethod = next(m for m in type_methods if m.type == "bang")
        assert "t_test *x" in bang_method.args

        float_method: TypeMethod = next(m for m in type_methods if m.type == "float")
        assert "t_floatarg f" in float_method.args

        list_method: TypeMethod = next(m for m in type_methods if m.type == "list")
        assert "t_symbol *s, int argc, t_atom *argv" in list_method.args

    def test_message_method_args(self, external_with_methods: External) -> None:
        """Test MessagedMethod argument generation."""
        msg_methods: List[MessageMethod] = external_with_methods.message_methods

        simple: MessageMethod = next(m for m in msg_methods if m.name == "simple")
        assert simple.args == "t_test *x"

        with_float: MessageMethod = next(
            m for m in msg_methods if m.name == "with_float"
        )
        assert "t_floatarg f0" in with_float.args


class TestParamCodegen:
    """Param types are limited to those the Pd templates can render."""

    @pytest.mark.parametrize("ptype", ["int", "atom", "signal", "sample"])
    def test_unsupported_param_type_rejected(self, ptype: str) -> None:
        ext = External(
            name="t",
            namespace="t",
            params_data=[{"name": "p", "type": ptype, "arg": True, "inlet": True}],
        )
        with pytest.raises(AudioTypeError):
            ext.params

    def test_int_type_method_rejected(self) -> None:
        ext = External(name="t", namespace="t", type_methods_data=[{"type": "int"}])
        with pytest.raises(AudioTypeError):
            ext.type_methods

    def test_symbol_param_renders(self, tmp_path: Path) -> None:
        spec = {
            "namespace": "t",
            "name": "symobj",
            "params": [
                {"name": "label", "type": "symbol", "initial": 'a"b'},
                {"name": "tag", "type": "symbol"},
            ],
            "meta": {"desc": "", "author": "", "repo": "", "features": []},
            "external": {"args": ["label"], "inlets": ["label"]},
        }
        spec_path = tmp_path / "symobj.json"
        spec_path.write_text(json.dumps(spec))
        PdProject(spec_path, target_dir=str(tmp_path)).generate()
        c = (tmp_path / "symobj" / "symobj.c").read_text()

        assert "t_symbol *label;" in c
        assert 'x->label = gensym("a\\"b");' in c
        assert 'x->tag = gensym("");' in c
        assert "symbolinlet_new(&x->x_obj, &x->label);" in c
        assert "t_symbol *s0" in c and "A_DEFSYMBOL, 0" in c

    def test_symbol_initial_control_char_rejected(self) -> None:
        ext = External(
            name="t",
            namespace="t",
            params_data=[{"name": "p", "type": "symbol", "initial": "a\nb"}],
        )
        with pytest.raises(AudioTypeError):
            ext.params[0].c_initial


class TestSpecificationProcessing:
    """Test YAML and JSON file processing and validation."""

    def test_valid_yaml_processing(self) -> None:
        """Test processing of valid YAML file."""
        yaml_content: str = """
namespace: test
name: simple
params: []
external:
  prefix: smp
  outlets: []
  message_methods: []
  type_methods: []
"""
        # Create file with specific name so we can test name detection
        temp_dir: str = tempfile.mkdtemp()
        yaml_path: Path = Path(temp_dir) / "simple.yml"
        with open(yaml_path, "w") as f:
            f.write(yaml_content)

        try:
            generator: Generator = Generator(yaml_path)
            assert generator.name == "simple"
            assert generator.fullname == "simple"
            assert not generator.is_dsp
        finally:
            shutil.rmtree(temp_dir)

    def test_dsp_external_detection(self) -> None:
        """Test DSP external detection from filename."""
        yaml_content: str = """
namespace: test
name: osc
params: []
external:
  prefix: osc
  outlets: []
  message_methods: []
  type_methods: []
"""
        temp_dir: str = tempfile.mkdtemp()
        yaml_path: Path = Path(temp_dir) / "osc~.yml"
        with open(yaml_path, "w") as f:
            f.write(yaml_content)

        try:
            generator: Generator = Generator(yaml_path)
            assert generator.is_dsp
            assert generator.name == "osc"
        finally:
            shutil.rmtree(temp_dir)

    def test_valid_json_processing(self) -> None:
        """Test processing of valid JSON file."""
        json_content: str = '''{
  "namespace": "test",
  "name": "simple",
  "params": [],
  "external": {
    "prefix": "smp",
    "outlets": [],
    "message_methods": [],
    "type_methods": []
  }
}'''
        # Create file with specific name so we can test name detection
        temp_dir: str = tempfile.mkdtemp()
        json_path: Path = Path(temp_dir) / "simple.json"
        with open(json_path, "w") as f:
            f.write(json_content)

        try:
            generator: Generator = Generator(json_path)
            assert generator.name == "simple"
            assert generator.fullname == "simple"
            assert not generator.is_dsp
        finally:
            shutil.rmtree(temp_dir)

    def test_dsp_external_detection_json(self) -> None:
        """Test DSP external detection from JSON filename."""
        json_content: str = '''{
  "namespace": "test",
  "name": "osc",
  "params": [],
  "external": {
    "prefix": "osc",
    "outlets": [],
    "message_methods": [],
    "type_methods": []
  }
}'''
        temp_dir: str = tempfile.mkdtemp()
        json_path: Path = Path(temp_dir) / "osc~.json"
        with open(json_path, "w") as f:
            f.write(json_content)

        try:
            generator: Generator = Generator(json_path)
            assert generator.is_dsp
            assert generator.name == "osc"
        finally:
            shutil.rmtree(temp_dir)

    def test_fallback_format_detection(self) -> None:
        """Test automatic format detection for files without standard extensions."""
        # Test YAML content with unknown extension
        yaml_content: str = """
namespace: test
name: fallback_yaml
params: []
external:
  prefix: fy
  outlets: []
  message_methods: []
  type_methods: []
"""
        temp_dir: str = tempfile.mkdtemp()
        fallback_path: Path = Path(temp_dir) / "fallback.txt"
        with open(fallback_path, "w") as f:
            f.write(yaml_content)

        try:
            generator: Generator = Generator(fallback_path)
            spec_data = generator.load_specification()
            assert spec_data["name"] == "fallback_yaml"
        finally:
            shutil.rmtree(temp_dir)

        # Test JSON content with unknown extension
        json_content: str = '''{
  "namespace": "test",
  "name": "fallback_json",
  "params": [],
  "external": {
    "prefix": "fj",
    "outlets": [],
    "message_methods": [],
    "type_methods": []
  }
}'''
        temp_dir = tempfile.mkdtemp()
        fallback_path = Path(temp_dir) / "fallback.txt"
        with open(fallback_path, "w") as f:
            f.write(json_content)

        try:
            generator = Generator(fallback_path)
            spec_data = generator.load_specification()
            assert spec_data["name"] == "fallback_json"
        finally:
            shutil.rmtree(temp_dir)


class TestProjectGeneration:
    """Test end-to-end project generation."""

    @pytest.fixture
    def temp_dir(self) -> TypingGenerator[str, None, None]:
        """Create a temporary directory for test output."""
        temp_dir: str = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_yaml_file(self, temp_dir: str) -> Path:
        """Create a sample YAML file for testing."""
        yaml_content: str = """
namespace: test
name: testobj
params:
  - name: value
    type: float
    min: 0.0
    max: 1.0
    initial: 0.5
    desc: "test value"
meta:
  desc: "A test object"
  author: "test"
  repo: "https://github.com/test/testobj"
  features: ["simple test"]
external:
  alias: testobj
  help: help-testobj
  args: [value]
  outlets:
    - name: out
      type: float
  message_methods:
    - name: set
      params: [float]
      doc: "set the value"
  type_methods:
    - type: bang
      doc: "output current value"
"""
        yaml_path: Path = Path(temp_dir) / "testobj.yml"
        with open(yaml_path, "w") as f:
            f.write(yaml_content)
        return yaml_path

    def test_pd_project_generation(self, sample_yaml_file: Path, temp_dir: str) -> None:
        """Test PureData project generation."""
        project: PdProject = PdProject(sample_yaml_file, target_dir=temp_dir)
        project.generate()

        # Check that files were created
        project_dir: Path = Path(temp_dir) / "testobj"
        assert project_dir.exists()
        assert (project_dir / "testobj.c").exists()
        assert (project_dir / "Makefile").exists()
        assert (project_dir / "README.md").exists()
        assert (project_dir / "Makefile.pdlibbuilder").exists()

    @pytest.mark.parametrize(
        "spec_name, source",
        [("other.yml", "testobj.c"), ("testobj~.yml", "testobj~.c")],
    )
    def test_pd_source_named_after_external(
        self, sample_yaml_file: Path, temp_dir: str, spec_name: str, source: str
    ) -> None:
        """C source and Makefile use the spec's 'name', not the spec filename."""
        spec_path: Path = sample_yaml_file.rename(Path(temp_dir) / spec_name)
        project: PdProject = PdProject(spec_path, target_dir=temp_dir)
        project.generate()

        project_dir: Path = Path(temp_dir) / spec_path.stem
        assert sorted(p.name for p in project_dir.glob("*.c")) == [source]
        makefile: str = (project_dir / "Makefile").read_text()
        assert f"class.sources = {source}\n" in makefile

    @pytest.mark.parametrize("spec_name", ["testobj.yml", "testobj~.yml"])
    def test_pd_help_symbol_optional(
        self, sample_yaml_file: Path, temp_dir: str, spec_name: str
    ) -> None:
        """Without 'help', Pd keeps its class-name default instead of 'None'."""
        spec_path: Path = Path(temp_dir) / spec_name
        spec_path.write_text(
            sample_yaml_file.read_text().replace("  help: help-testobj\n", "")
        )
        PdProject(spec_path, target_dir=temp_dir).generate()

        project_dir: Path = Path(temp_dir) / spec_path.stem
        content: str = (project_dir / f"{spec_path.stem}.c").read_text()
        assert "None" not in content
        assert "class_sethelpsymbol" not in content
        makefile: str = (project_dir / "Makefile").read_text()
        assert f"datafiles = $(wildcard {spec_path.stem}-help.pd) README.md" in makefile

    def test_pd_help_symbol_explicit(
        self, sample_yaml_file: Path, temp_dir: str
    ) -> None:
        """An explicit 'help' is passed to class_sethelpsymbol."""
        PdProject(sample_yaml_file, target_dir=temp_dir).generate()
        content: str = (Path(temp_dir) / "testobj" / "testobj.c").read_text()
        assert 'class_sethelpsymbol(testobj_class, gensym("help-testobj"));' in content

    def test_max_project_generation(
        self, sample_yaml_file: Path, temp_dir: str
    ) -> None:
        """Test Max/MSP project generation."""
        # Max has no help-file call, so it rejects 'help'.
        sample_yaml_file.write_text(
            sample_yaml_file.read_text().replace("  help: help-testobj\n", "")
        )
        project: MaxProject = MaxProject(sample_yaml_file, target_dir=temp_dir)
        project.generate()

        # Check that files were created
        project_dir: Path = Path(temp_dir) / "testobj"
        assert project_dir.exists()
        assert (project_dir / "testobj.c").exists()
        assert (project_dir / "README.md").exists()

    @pytest.mark.parametrize("spec_name", ["counter.yml", "counter~.yml"])
    def test_max_source_compiles_as_c(self, temp_dir: str, spec_name: str) -> None:
        """Max sources are plain C that compiles against stub Max SDK headers."""
        import subprocess

        compiler = shutil.which("cc")
        if compiler is None:
            pytest.skip("no C compiler")
        spec: Path = Path(temp_dir) / spec_name
        shutil.copy(get_test_resource_path("resources/examples/counter.yml"), spec)
        project: MaxProject = MaxProject(spec, target_dir=temp_dir)
        project.generate()

        source: Path = Path(temp_dir) / spec.stem / f"{spec.stem}.c"
        content: str = source.read_text()
        assert "daisysp" not in content
        assert ("dsp64" in content) == spec.stem.endswith("~")
        assert f'class_new("my.{spec.stem}"' in content

        stubs: Path = Path(__file__).parent / "mx"
        result = subprocess.run(
            [compiler, "-std=c99", "-fsyntax-only", "-Werror=implicit-function-declaration",
             "-I", str(stubs), str(source)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr

    @pytest.mark.parametrize("spec_name", ["counter.yml", "counter~.yml"])
    def test_pd_source_compiles_as_c(self, temp_dir: str, spec_name: str) -> None:
        """Pd sources compile against a stub m_pd.h with Pd's signatures."""
        import subprocess

        compiler = shutil.which("cc")
        if compiler is None:
            pytest.skip("no C compiler")
        spec: Path = Path(temp_dir) / spec_name
        text = get_test_resource_path("resources/examples/counter.yml").read_text()
        if spec_name.endswith("~.yml"):
            # A signal object rejects a float method; its signal inlet takes floats.
            text = text.replace("    - type: float\n      doc: each number is printed out\n\n", "")
            assert "- type: float" not in text
        spec.write_text(text)
        PdProject(spec, target_dir=temp_dir).generate()

        source: Path = Path(temp_dir) / spec.stem / f"{spec.stem}.c"
        if spec.stem.endswith("~"):
            content: str = source.read_text()
            # without n_channels: one signal inlet and one signal outlet
            assert "#define N_CHANNELS 1\n" in content

        stubs: Path = Path(__file__).parent / "pd"
        result = subprocess.run(
            [compiler, "-std=c99", "-fsyntax-only", "-Wall", "-Werror",
             "-I", str(stubs), str(source)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr

    def test_generated_c_file_content(
        self, sample_yaml_file: Path, temp_dir: str
    ) -> None:
        """Test that generated C file contains expected content."""
        project: PdProject = PdProject(sample_yaml_file, target_dir=temp_dir)
        project.generate()

        c_file: Path = Path(temp_dir) / "testobj" / "testobj.c"
        content: str = c_file.read_text()

        # Check for essential C code elements
        assert "typedef struct _testobj" in content
        assert "static t_class *testobj_class" in content
        assert "t_float value" in content  # parameter
        assert "t_outlet *out_out" in content  # outlet
        assert "A test object" in content  # description from meta

    @pytest.mark.parametrize(
        "spec_name, source, ctor",
        [
            ("testobj.yml", "testobj.c", "testobj_new(t_floatarg f0)"),
            ("testobj~.yml", "testobj~.c", "testobj_tilde_new(t_floatarg f0)"),
        ],
    )
    def test_constructor_assigns_creation_args(
        self, sample_yaml_file: Path, temp_dir: str, spec_name: str, source: str, ctor: str
    ) -> None:
        """Creation args overwrite 'initial' in both control and dsp templates."""
        spec_path: Path = sample_yaml_file.rename(Path(temp_dir) / spec_name)
        PdProject(spec_path, target_dir=temp_dir).generate()

        content: str = (Path(temp_dir) / spec_path.stem / source).read_text()
        body: str = content.split(ctor, 1)[1].split("return (void *)x;", 1)[0]
        assert body.index("x->value = 0.5;") < body.index(
            "if (f0 != 0) x->value = f0;"
        )
        assert "switch stmt here" not in content

    def test_dsp_registers_tilde_identifiers(
        self, sample_yaml_file: Path, temp_dir: str
    ) -> None:
        """DSP setup registers the '_tilde' functions the template defines."""
        spec_path: Path = Path(temp_dir) / "testobj~.yml"
        spec_path.write_text(
            sample_yaml_file.read_text().replace("alias: testobj", "alias: tobj~")
        )
        PdProject(spec_path, target_dir=temp_dir).generate()

        content: str = (Path(temp_dir) / "testobj~" / "testobj~.c").read_text()
        assert "void testobj_tilde_bang(t_testobj_tilde *x)" in content
        assert "void testobj_tilde_set(t_testobj_tilde *x, t_floatarg f0)" in content
        assert "class_addbang(testobj_tilde_class, testobj_tilde_bang);" in content
        assert (
            "class_addmethod(testobj_tilde_class, (t_method)testobj_tilde_set, "
            'gensym("set"), A_DEFFLOAT, 0);'
        ) in content
        assert (
            'class_addcreator((t_newmethod)testobj_tilde_new, gensym("tobj~"), '
            "A_DEFFLOAT, 0);"
        ) in content
        assert "(t_method)testobj_tilde_dsp" in content
        assert "testobj_class" not in content

    def test_json_project_generation(self, temp_dir: str) -> None:
        """Test project generation using JSON specification file."""
        json_content: str = '''{
  "namespace": "test",
  "name": "jsonobj",
  "params": [
    {
      "name": "value",
      "type": "float",
      "min": 0.0,
      "max": 1.0,
      "initial": 0.5,
      "desc": "test value"
    }
  ],
  "meta": {
    "desc": "A test object from JSON",
    "author": "test",
    "repo": "https://github.com/test/jsonobj",
    "features": ["json test"]
  },
  "external": {
    "alias": "jsonobj",
    "help": "help-jsonobj",
    "args": ["value"],
    "outlets": [
      {
        "name": "out",
        "type": "float"
      }
    ],
    "message_methods": [
      {
        "name": "set",
        "params": ["float"],
        "doc": "set the value"
      }
    ],
    "type_methods": [
      {
        "type": "bang",
        "doc": "output current value"
      }
    ]
  }
}'''
        json_path: Path = Path(temp_dir) / "jsonobj.json"
        with open(json_path, "w") as f:
            f.write(json_content)

        # Test PureData project generation from JSON
        project: PdProject = PdProject(json_path, target_dir=temp_dir)
        project.generate()

        # Check that files were created
        project_dir: Path = Path(temp_dir) / "jsonobj"
        assert project_dir.exists()
        assert (project_dir / "jsonobj.c").exists()
        assert (project_dir / "Makefile").exists()
        assert (project_dir / "README.md").exists()
        assert (project_dir / "Makefile.pdlibbuilder").exists()

        # Verify content
        c_file: Path = project_dir / "jsonobj.c"
        content: str = c_file.read_text()
        assert "typedef struct _jsonobj" in content
        assert "A test object from JSON" in content


class TestHelperClasses:
    """Test the new focused helper classes."""

    def test_type_mapper(self) -> None:
        """Test TypeMapper functionality."""
        mapper: TypeMapper = TypeMapper()

        # Test valid mappings
        assert mapper.get_pd_mapping("float") == "A_DEFFLOAT"
        assert mapper.get_func_arg("float") == "t_floatarg f"

        # Test invalid types
        with pytest.raises(AudioTypeError):
            mapper.get_pd_mapping("invalid_type")

        with pytest.raises(AudioTypeError):
            mapper.get_func_arg("invalid_type")

    def test_argument_builder(self) -> None:
        """Test ArgumentBuilder functionality."""
        mapper: TypeMapper = TypeMapper()
        builder: ArgumentBuilder = ArgumentBuilder(mapper)

        # Test empty args
        assert builder.build_constructor_args([]) == "void"

        # Test type signature
        assert builder.build_type_signature([]) == "0"

    @staticmethod
    def _arg_params(types: List[str]) -> List[Param]:
        ext: External = External(name="t", namespace="t")
        return [Param(ext, f"p{i}", t, 0, True, False) for i, t in enumerate(types)]

    def test_constructor_assignments_typed(self) -> None:
        """Typed args name-match the signature and skip Pd's omitted defaults."""
        builder: ArgumentBuilder = ArgumentBuilder(TypeMapper())
        params: List[Param] = self._arg_params(["float", "symbol"])

        assert builder.build_constructor_args(params) == "t_floatarg f0, t_symbol *s1"
        assert builder.build_constructor_assignments(params) == [
            "if (f0 != 0) x->p0 = f0;",
            "if (s1 != &s_) x->p1 = s1;",
        ]

    def test_constructor_assignments_gimme(self) -> None:
        """More than 5 args read from argv, guarded by argc."""
        builder: ArgumentBuilder = ArgumentBuilder(TypeMapper())
        params: List[Param] = self._arg_params(["float"] * 7 + ["symbol"])

        assert builder.build_constructor_args(params) == (
            "t_symbol *s, int argc, t_atom *argv"
        )
        stmts: List[str] = builder.build_constructor_assignments(params)
        assert len(stmts) == 8
        assert stmts[0] == "if (argc > 0) x->p0 = atom_getfloatarg(0, argc, argv);"
        assert stmts[6] == "if (argc > 6) x->p6 = atom_getfloatarg(6, argc, argv);"
        assert stmts[7] == "if (argc > 7) x->p7 = atom_getsymbolarg(7, argc, argv);"

    def test_typed_arg_limit_is_maxpdarg(self) -> None:
        """Pd typechecks 5 args (MAXPDARG); 6 must fall back to A_GIMME."""
        mapper: TypeMapper = TypeMapper()
        builder: ArgumentBuilder = ArgumentBuilder(mapper)
        generator: CodeGenerator = CodeGenerator(mapper, builder)

        five: List[Param] = self._arg_params(["float"] * 5)
        assert builder.build_type_signature(five) == ", ".join(["A_DEFFLOAT"] * 5) + ", 0"
        assert generator.generate_message_addmethod("t", "m", ["float"] * 5).endswith(
            ", ".join(["A_DEFFLOAT"] * 5) + ", 0)"
        )

        six: List[Param] = self._arg_params(["float"] * 6)
        assert builder.build_constructor_args(six) == "t_symbol *s, int argc, t_atom *argv"
        assert builder.build_type_signature(six) == "A_GIMME, 0"
        assert (
            builder.build_method_args("t_t", ["float"] * 6)
            == "t_t *x, t_symbol *s, int argc, t_atom *argv"
        )
        assert generator.generate_message_addmethod("t", "m", ["float"] * 6).endswith(
            'gensym("m"), A_GIMME, 0)'
        )

    @pytest.mark.parametrize(
        "params",
        [
            ["float", "anything"],
            ["list", "float"],
            ["anything", "anything"],
            ["anything"],
            ["list"],
        ],
    )
    def test_gimme_types_not_mixed(self, params: List[str]) -> None:
        """'list'/'anything' params collapse to a lone A_GIMME; Pd rejects mixing."""
        mapper: TypeMapper = TypeMapper()
        builder: ArgumentBuilder = ArgumentBuilder(mapper)
        generator: CodeGenerator = CodeGenerator(mapper, builder)

        assert (
            builder.build_method_args("t_test", params)
            == "t_test *x, t_symbol *s, int argc, t_atom *argv"
        )
        assert generator.generate_message_addmethod("test", "m", params).endswith(
            'gensym("m"), A_GIMME, 0)'
        )

    def test_code_generator(self) -> None:
        """Test CodeGenerator functionality."""
        mapper: TypeMapper = TypeMapper()
        builder: ArgumentBuilder = ArgumentBuilder(mapper)
        generator: CodeGenerator = CodeGenerator(mapper, builder)

        # Test method generation
        method_call: str = generator.generate_class_addmethod("test", "bang", "bang")
        assert "class_addbang" in method_call
        assert "test_class" in method_call

        # Test message method generation
        message_call: str = generator.generate_message_addmethod("test", "reset", [])
        assert "class_addmethod" in message_call
        assert "reset" in message_call

    def test_helper_integration(self) -> None:
        """Test that helper classes work together correctly."""
        # Create a simple external to test integration
        external_data: Dict[str, Any] = {
            "name": "test",
            "namespace": "test",
            "params_data": [],
            "outlets_data": [],
            "message_methods_data": [],
            "type_methods_data": [],
        }

        external: External = External(**external_data)

        # Test that helper objects are created
        assert external.type_mapper is not None
        assert external.arg_builder is not None
        assert external.code_generator is not None

        # Test that they work
        assert external.class_new_args == "void"
        assert external.class_type_signature == "0"


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_missing_specification_file(self) -> None:
        """Test handling of missing specification file."""
        with pytest.raises(FileNotFoundError):
            generator: Generator = Generator("nonexistent.yml")
            generator.load_specification()

    def test_invalid_specification_content(self) -> None:
        """Test handling of invalid specification content."""
        yaml_content: str = "invalid: yaml: content: ["
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            yaml_path: str = f.name

        try:
            generator: Generator = Generator(yaml_path)
            with pytest.raises(ValueError):
                generator.load_specification()
        finally:
            os.unlink(yaml_path)

    @pytest.fixture
    def externals_list_json(self, tmp_path: Path) -> Path:
        path = tmp_path / "pair.json"
        path.write_text('{"externals": [{"namespace": "my", "name": "first"}]}')
        return path

    def test_externals_list_rejected(self, externals_list_json: Path) -> None:
        """The pre-0.3 'externals' list fails with a migration hint."""
        generator = Generator(externals_list_json)
        with pytest.raises(ValueError, match="'externals' is no longer supported"):
            generator.validate_specification_structure(generator.load_specification())

    @pytest.mark.parametrize(
        "extra, error",
        [
            ('"inlets": ["p"]', "'inlets' belongs in the 'external' block"),
            ('"modulated": ["p"]', "'modulated' belongs in the 'plugin' block"),
            ('"outlet": []', "unknown field: 'outlet'"),
            ('"external": {"outlet": []}', "'external' contains unknown field\\(s\\): 'outlet'"),
            ('"external": []', "'external' must be a dictionary"),
            ('"external": {"args": "p"}', "'external.args' must be a list of param names"),
            ('"external": {"args": ["p", "p"]}', "names a param twice"),
            ('"external": {"inlets": ["q"]}', "'external.inlets' names unknown param 'q'"),
            # The other target's block is checked too.
            ('"plugin": {"modulated": ["q"]}', "'plugin.modulated' names unknown param 'q'"),
            ('"params": [{"name": "p", "type": "float", "arg": true}]', "'arg'.* moved to"),
            ('"params": [{"name": "p", "type": "float", "inlet": true}]', "'inlet'.* moved to"),
            ('"params": [{"name": "p", "type": "float", "unit": "Hz"}]', "unknown field\\(s\\): 'unit'"),
        ],
    )
    def test_unread_keys_rejected(
        self, tmp_path: Path, extra: str, error: str
    ) -> None:
        """Keys render() never reads must raise, not be silently dropped."""
        path = tmp_path / "ext.json"
        params = '' if '"params"' in extra else '"params": [{"name": "p", "type": "float"}], '
        path.write_text(
            '{"namespace": "my", "name": "ext", ' + params + extra + ", "
            '"meta": {"desc": "d", "features": [], "author": "a", "repo": "r"}}'
        )
        generator = Generator(path)
        with pytest.raises(ValueError, match=error):
            generator.validate_specification_structure(generator.load_specification())

    def test_externals_list_cli(self, externals_list_json: Path, tmp_path: Path) -> None:
        """Both --validate and generate must fail on a pre-0.3 spec."""
        import sys
        from unittest.mock import patch

        out_dir = tmp_path / "out"
        for args in (["--validate"], ["-o", str(out_dir)]):
            with patch.object(sys, "argv", ["xtgen", *args, str(externals_list_json)]):
                assert main() == 1
        assert not (out_dir / "pair" / "pair.c").exists()

    META = '"meta": {"desc": "d", "features": [], "author": "a", "repo": "r"}'

    @pytest.mark.parametrize(
        "body, error",
        [
            ('"external": {"outlets": [{"name": "o", "type": "int"}]}, ' + META, "Invalid outlet type"),
            ('"external": {"type_methods": [{"type": "foo"}]}, ' + META, "Invalid type method"),
            ('"params": [{"name": "p", "type": "bad"}], ' + META, "Invalid parameter type"),
            ('"external": {"outlets": [{"type": "float"}]}, ' + META, "Outlet must contain required field: 'name'"),
            ('"external": {"message_methods": [{"params": []}]}, ' + META, "Message method must contain"),
            ('"external": {"type_methods": [{"doc": "x"}]}, ' + META, "Type method must contain"),
            ('"external": {"outlets": []}', "'meta' dictionary"),
            ('"meta": {"desc": "d"}', "'meta' must contain required field"),
        ],
    )
    def test_validate_rejects_what_generation_rejects(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], body: str, error: str
    ) -> None:
        """--validate must fail on any spec that generation would reject."""
        import sys
        from unittest.mock import patch

        spec = tmp_path / "bad.json"
        spec.write_text('{"namespace": "my", "name": "bad", ' + body + "}")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        for args in (["--validate"], ["-o", str(out_dir)]):
            with patch.object(sys, "argv", ["xtgen", *args, str(spec)]):
                assert main() == 1
            assert error in capsys.readouterr().err
        assert not (out_dir / "bad").exists()


class TestCommandLineInterface:
    """Test command-line interface functionality."""

    def test_argument_parser_creation(self) -> None:
        """Test that argument parser is created correctly."""
        parser = create_argument_parser()
        assert parser.prog == "xtgen"
        assert parser.description is not None and "Generate PureData, Max/MSP, CLAP/VST3/AU and VCV Rack projects" in parser.description

    def test_validate_specification_function(self) -> None:
        """Test the validate_specification function."""
        # Test with valid specification
        result = validate_specification(get_test_resource_path("resources/examples/counter.yml"), verbose=False)
        assert result is True

        # Test with non-existent file
        result = validate_specification(Path("nonexistent.yml"), verbose=False)
        assert result is False

    def test_cli_with_default_arguments(self, temp_dir: str) -> None:
        """Test CLI with default arguments."""
        import sys
        from unittest.mock import patch

        # Mock sys.argv to simulate CLI call
        test_args = ["xtgen", str(get_test_resource_path("resources/examples/counter.yml")), "-o", temp_dir]

        with patch.object(sys, 'argv', test_args):
            result = main()
            assert result == 0

        # Check that project was generated
        project_dir = Path(temp_dir) / "counter"
        assert project_dir.exists()
        assert (project_dir / "counter.c").exists()

    def test_cli_max_target(self, temp_dir: str) -> None:
        """Test CLI with Max/MSP target."""
        import sys
        from unittest.mock import patch

        test_args = ["xtgen", "-t", "max", str(get_test_resource_path("resources/examples/counter.json")), "-o", temp_dir]

        with patch.object(sys, 'argv', test_args):
            result = main()
            assert result == 0

        # Check that Max project was generated
        project_dir = Path(temp_dir) / "counter"
        assert project_dir.exists()
        assert (project_dir / "counter.c").exists()

    @pytest.mark.parametrize("target", ["pd", "max"])
    def test_cli_regenerate_requires_force(self, temp_dir: str, target: str) -> None:
        """Regenerating into a non-empty project dir fails unless --force is given."""
        import sys
        from unittest.mock import patch

        spec = str(get_test_resource_path("resources/examples/counter.yml"))
        args = ["xtgen", "-t", target, spec, "-o", temp_dir]
        source = Path(temp_dir) / "counter" / "counter.c"

        with patch.object(sys, "argv", args):
            assert main() == 0
        source.write_text("/* edited */\n")

        with patch.object(sys, "argv", args):
            assert main() == 1
        assert source.read_text() == "/* edited */\n"

        with patch.object(sys, "argv", args + ["--force"]):
            assert main() == 0
        assert source.read_text() != "/* edited */\n"

    def test_cli_generates_into_empty_existing_dir(self, temp_dir: str) -> None:
        """An existing but empty project dir does not need --force."""
        import sys
        from unittest.mock import patch

        (Path(temp_dir) / "counter").mkdir()
        spec = str(get_test_resource_path("resources/examples/counter.yml"))
        with patch.object(sys, "argv", ["xtgen", spec, "-o", temp_dir]):
            assert main() == 0
        assert (Path(temp_dir) / "counter" / "counter.c").exists()

    @pytest.mark.parametrize("target", ["pd", "max"])
    def test_cli_creates_missing_output_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str
    ) -> None:
        """A nested, non-existent -o dir is created; ./build is not created in CWD."""
        import sys
        from unittest.mock import patch

        monkeypatch.chdir(tmp_path)
        spec = str(get_test_resource_path("resources/examples/counter.yml"))
        with patch.object(sys, "argv", ["xtgen", "-t", target, spec, "-o", "out/sub"]):
            assert main() == 0
        assert (tmp_path / "out" / "sub" / "counter" / "counter.c").exists()
        assert not (tmp_path / "build").exists()

    def test_cli_validation_mode(self) -> None:
        """Test CLI validation-only mode."""
        import sys
        from unittest.mock import patch

        test_args = ["xtgen", "--validate", str(get_test_resource_path("resources/examples/counter.yml"))]

        with patch.object(sys, 'argv', test_args):
            result = main()
            assert result == 0

    def test_cli_validation_mode_invalid_file(self) -> None:
        """Test CLI validation mode with invalid file."""
        import sys
        from unittest.mock import patch

        test_args = ["xtgen", "--validate", "nonexistent.yml"]

        with patch.object(sys, 'argv', test_args):
            result = main()
            assert result == 1

    def test_cli_list_examples(self) -> None:
        """Test CLI list examples functionality."""
        import sys
        from unittest.mock import patch

        test_args = ["xtgen", "--list-examples"]

        with patch.object(sys, 'argv', test_args):
            result = main()
            assert result == 0

    def test_cli_verbose_quiet_conflict(self) -> None:
        """Test that verbose and quiet options conflict."""
        import sys
        from unittest.mock import patch

        test_args = ["xtgen", "-v", "-q", str(get_test_resource_path("resources/examples/counter.yml"))]

        with patch.object(sys, 'argv', test_args):
            result = main()
            assert result == 1

    @pytest.mark.parametrize("args, code", [(["--list-examples"], 0), (["nosuch"], 1)])
    def test_python_m_xtgen(self, args: List[str], code: int) -> None:
        """'python -m xtgen' runs the CLI and returns its exit status."""
        import subprocess
        import sys

        result = subprocess.run([sys.executable, "-m", "xtgen", *args],
                                capture_output=True, text=True)
        assert result.returncode == code, result.stderr

    def test_list_examples_function(self) -> None:
        """Test the list_examples function."""
        # This function prints to stdout, so we'll just ensure it doesn't crash
        try:
            list_examples()
        except Exception as e:
            pytest.fail(f"list_examples() raised an exception: {e}")

    def test_yaml_availability_in_parser(self) -> None:
        """Test that argument parser reflects YAML availability."""
        parser = create_argument_parser()

        if YAML_AVAILABLE:
            assert "YAML or JSON" in parser.description
            assert ".yml, .yaml" in parser.epilog
        else:
            assert "JSON specifications" in parser.description
            assert "PyYAML" in parser.epilog
            assert "pip install PyYAML" in parser.epilog

    def test_yaml_file_handling_when_unavailable(self, temp_dir: str) -> None:
        """Test handling of YAML files when YAML is not available."""
        import unittest.mock

        # Create a test YAML file
        yaml_content = """
name: test
params: []
"""
        yaml_file = Path(temp_dir) / "test.yml"
        yaml_file.write_text(yaml_content)

        # Mock YAML_AVAILABLE to False
        with unittest.mock.patch('xtgen.templates.YAML_AVAILABLE', False):
            project = PdProject(yaml_file)

            # Should raise an error when trying to load YAML file
            with pytest.raises(ValueError, match="YAML files are not supported"):
                project.load_specification()

    def test_json_fallback_when_yaml_unavailable(self, temp_dir: str) -> None:
        """Test that JSON files work even when YAML is unavailable."""
        import unittest.mock

        # Create a test JSON file
        json_content = """{
    "name": "test",
    "params": []
}"""
        json_file = Path(temp_dir) / "test.json"
        json_file.write_text(json_content)

        # Mock YAML_AVAILABLE to False
        with unittest.mock.patch('xtgen.templates.YAML_AVAILABLE', False):
            project = PdProject(json_file)

            # Should work fine with JSON
            spec = project.load_specification()
            assert spec is not None
            assert spec["name"] == "test"

    @pytest.fixture
    def temp_dir(self) -> TypingGenerator[str, None, None]:
        """Create a temporary directory for CLI test output."""
        temp_dir: str = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)


PLUGIN_META = {"desc": "d", "features": ["f"], "author": "a", "repo": "r"}


def write_plugin_spec(path: Path, **ext: Any) -> Path:
    """Write a JSON spec with plugin defaults overridden by `ext`."""
    data: Dict[str, Any] = {"namespace": "my", "name": path.stem.strip("~"), "meta": PLUGIN_META}
    data.update(ext)
    path.write_text(json.dumps(data))
    return path


def run(args: List[str], cwd: Optional[Path] = None, env: Optional[Dict[str, str]] = None) -> None:
    """Run a command, failing the test with its stderr."""
    import subprocess

    result = subprocess.run(args, capture_output=True, text=True, cwd=cwd, env=env)
    assert result.returncode == 0, result.stderr + result.stdout


TESTS_DIR = Path(__file__).parent


def check_c_syntax(source: Path, target: str) -> None:
    """Syntax-check a generated pd or max source against the stub SDK headers."""
    cc = shutil.which("cc")
    if cc is None:
        pytest.skip("no C compiler")
    flags = {"pd": ["-Wall", "-Werror"], "max": ["-Werror=implicit-function-declaration"]}[target]
    stubs = TESTS_DIR / {"pd": "pd", "max": "mx"}[target]
    run([cc, "-std=c99", "-fsyntax-only", *flags, "-I", str(stubs), "-I", str(source.parent),
         str(source)])


def build_and_run_clap(src: Path, name: str, plugin_id: str, *mode: str) -> None:
    """Compile a generated CLAP project warning-free, link tests/clap/host.c, run it."""
    cc, cxx = shutil.which("cc"), shutil.which("c++")
    if cc is None or cxx is None:
        pytest.skip("no C/C++ compiler")
    inc = ["-I", str(TESTS_DIR / "clap" / "include"), "-I", str(src)]
    warn = ["-Wall", "-Wextra", "-Werror"]
    objs = [src / "host.o", src / "plugin.o", src / "entry.o"]
    run([cc, "-std=c11", "-Wpedantic", *warn, *inc, "-c", str(src / f"{name}.c"), "-o", str(objs[1])])
    run([cxx, "-std=c++17", *warn, *inc, "-c", str(src / f"{name}_entry.cpp"), "-o", str(objs[2])])
    run([cc, "-std=c11", *warn, *inc, "-c", str(TESTS_DIR / "clap" / "host.c"), "-o", str(objs[0])])
    dsp_c = src / f"{name}_dsp.c"
    if dsp_c.is_file():
        objs.append(src / "dsp.o")
        run([cc, "-std=c99", *warn, "-c", str(dsp_c), "-o", str(objs[-1])])
    run([cxx, "-o", str(src / "host"), *map(str, objs)])
    run([str(src / "host"), plugin_id, *mode])


def build_and_run_max(src: Path, name: str, *args: str) -> None:
    """Link a generated Max graph external with tests/mx/fake_max.c and run graph_host."""
    cc = shutil.which("cc")
    if cc is None:
        pytest.skip("no C compiler")
    mx = TESTS_DIR / "mx"
    inc = ["-I", str(mx), "-I", str(src)]
    objs = []
    for source in (mx / "fake_max.c", mx / "graph_host.c", src / f"{name}~.c", src / f"{name}_dsp.c"):
        objs.append(src / (source.stem + ".o"))
        # gen-dsp's C is held to -Werror; the Max-API casts in the rest are not -Wextra clean.
        flags = ["-Wall", "-Wextra", "-Werror"] if source.stem.endswith("_dsp") else []
        run([cc, "-std=c99", *flags, *inc, "-c", str(source), "-o", str(objs[-1])])
    run([cc, "-o", str(src / "host"), *map(str, objs), "-lm"])
    run([str(src / "host"), *args])


def build_vcv(project: Path) -> None:
    """Build a VCV plugin against $RACK_DIR with -Werror."""
    # plugin.mk appends to FLAGS, so an environment value is kept.
    env = dict(os.environ, FLAGS="-Werror")
    run(["make", f"RACK_DIR={os.environ['RACK_DIR']}"], cwd=project, env=env)


def run_in_rack(project: Path, module: str, *args: str) -> None:
    """Link a built VCV plugin's objects with tests/vcv/rack_host.cpp and libRack; run it."""
    rack = os.environ["RACK_DIR"]
    objs = [str(o) for o in (project / "build" / "src").glob("*.o")]
    run(["c++", "-std=c++11", f"-I{rack}/include", f"-I{rack}/dep/include",
         f"-DMODEL=model{module}", "-c", str(TESTS_DIR / "vcv" / "rack_host.cpp"),
         "-o", str(project / "rack_host.o")])
    run(["c++", "-o", str(project / "rack_host"), str(project / "rack_host.o"), *objs,
         f"-L{rack}", "-lRack"])
    # libRack.dylib's install name is bare, so the loader needs its directory.
    env = dict(os.environ, DYLD_LIBRARY_PATH=rack, LD_LIBRARY_PATH=rack)
    run([str(project / "rack_host"), *args], env=env)


class TestPluginTargets:
    """CLAP and VCV Rack targets."""

    GAIN = get_test_resource_path("resources/examples/gain.yml")
    CLAP_DIR = Path(__file__).parent / "clap"

    def test_registry_lists_all_targets(self) -> None:
        assert TARGETS == {
            "pd": PdProject, "max": MaxProject, "clap": ClapProject, "vcv": VcvProject,
        }
        parser = create_argument_parser()
        for target in TARGETS:
            assert parser.parse_args(["-t", target]).target == target

    @pytest.mark.parametrize("target", ["clap", "vcv"])
    def test_cli_generates_gain_example(self, tmp_path: Path, target: str) -> None:
        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", ["xtgen", "-q", "-t", target, "-o", str(tmp_path), str(self.GAIN)]):
            assert main() == 0
        expected = {
            "clap": ["gain.c", "gain_entry.cpp", "CMakeLists.txt", "README.md"],
            "vcv": ["plugin.json", "Makefile", "README.md", "src/plugin.hpp",
                    "src/plugin.cpp", "src/Gain.cpp", "res/Gain.svg"],
        }[target]
        for name in expected:
            assert (tmp_path / "gain" / name).is_file(), name

    @pytest.mark.parametrize("target", ["clap", "vcv"])
    def test_external_block_ignored(self, tmp_path: Path, target: str) -> None:
        """Plugins read only the 'plugin' block; counter's 'external' block is for pd and max."""
        counter = get_test_resource_path("resources/examples/counter.yml")
        project = TARGETS[target](counter, target_dir=str(tmp_path))
        project.generate()
        assert project.model is not None
        assert project.model.outlets == [] and project.model.alias == "counter"
        assert not any(p.has_inlet or p.is_arg for p in project.model.params)

    def test_plugin_block_ignored(self, tmp_path: Path) -> None:
        """pd reads only the 'external' block: a modulated param gets no inlet."""
        spec = tmp_path / "gain~.yml"
        shutil.copy(self.GAIN, spec)
        project = PdProject(spec, target_dir=str(tmp_path))
        project.generate()
        assert project.model is not None
        assert not any(p.has_inlet for p in project.model.params)

    def test_validate_uses_target_rules(self) -> None:
        counter = get_test_resource_path("resources/examples/counter.yml")
        assert validate_specification(counter, target="pd")
        assert not validate_specification(self.GAIN, target="pd")
        assert validate_specification(self.GAIN, target="clap")

    @pytest.mark.parametrize(
        "ext, error",
        [
            ({"params": [{"name": "s", "type": "symbol", "min": 0, "max": 1}]}, "only float params"),
            ({"params": [{"name": "p", "type": "float", "min": 0, "max": 1, "arg": True}]}, "'arg'.* moved to"),
            ({"params": [{"name": "p", "type": "float", "max": 1}]}, "must set 'min'"),
            ({"params": [{"name": "p", "type": "float", "min": 0, "max": 1, "initial": 2}]}, "min <= initial <= max"),
            ({"params": [{"name": "p", "type": "float", "min": 1, "max": 1, "initial": 1}]}, "min < max"),
            ({"params": [{"name": "p", "type": "float", "min": "0", "max": 1}]}, "finite numbers"),
            ({"params": [{"name": "p", "type": "float", "min": 0, "max": 1e999}]}, "finite numbers"),
            ({"params": [{"name": "p-q", "type": "float", "min": 0, "max": 1}]}, "ASCII identifier"),
            ({"name": "my-gain"}, "'name' must be an ASCII identifier"),
            ({"namespace": "a.b"}, "'namespace' must be an ASCII identifier"),
            ({"n_channels": 0}, "positive integer"),
            ({"help": "help-x"}, "'help' belongs in the 'external' block"),
            ({"plugin": {"modulated": ["nope"]}}, "'plugin.modulated' names unknown param 'nope'"),
            ({"plugin": {"cv": []}}, "'plugin' contains unknown field\\(s\\): 'cv'"),
            ({"external": {"args": ["nope"]}}, "'external.args' names unknown param 'nope'"),
        ],
    )
    @pytest.mark.parametrize("target", ["clap", "vcv"])
    def test_plugin_spec_rejected(
        self, tmp_path: Path, target: str, ext: Dict[str, Any], error: str
    ) -> None:
        spec = write_plugin_spec(tmp_path / "x.json", **ext)
        project = TARGETS[target](spec, target_dir=str(tmp_path))
        with pytest.raises(ValueError, match=error):
            project.generate()
        assert not (tmp_path / "x").exists()

    @pytest.mark.parametrize("target", ["clap", "vcv"])
    def test_tilde_filename_ignored(self, tmp_path: Path, target: str) -> None:
        """Plugins always process audio; '~' is dropped from paths."""
        spec = tmp_path / "gain~.yml"
        shutil.copy(self.GAIN, spec)
        TARGETS[target](spec, target_dir=str(tmp_path)).generate()
        assert (tmp_path / "gain").is_dir()
        assert not (tmp_path / "gain~").exists()

    def test_vcv_manifest_escapes_strings(self, tmp_path: Path) -> None:
        meta = dict(PLUGIN_META, author='a "q" \\ b', desc="line one\nline two\n")
        spec = write_plugin_spec(tmp_path / "gain.json", meta=meta)
        VcvProject(spec, target_dir=str(tmp_path)).generate()
        manifest = json.loads((tmp_path / "gain" / "plugin.json").read_text())
        assert manifest["author"] == 'a "q" \\ b'
        assert manifest["modules"][0] == {
            "slug": "Gain", "name": "gain", "description": "line one line two", "tags": ["Effect"],
        }

    def test_clap_modulatable_flags(self, tmp_path: Path) -> None:
        """Only params listed in 'plugin.modulated' are CLAP modulatable."""
        ClapProject(self.GAIN, target_dir=str(tmp_path)).generate()
        source = (tmp_path / "gain" / "gain.c").read_text()
        specs = source[source.index("_param_specs[PARAM_COUNT + 1] = {"):]
        assert '{ "gain", 0.0, 2.0, 1.0,\n      CLAP_PARAM_IS_AUTOMATABLE | CLAP_PARAM_IS_MODULATABLE },' in specs
        assert '{ "pan", -1.0, 1.0, 0.0,\n      CLAP_PARAM_IS_AUTOMATABLE },' in specs

    def test_vcv_panel_widens_with_rows(self, tmp_path: Path) -> None:
        """7 rows per 4 HP column pair: 9 params + 1 channel need 2 pairs = 9 HP."""
        params = [{"name": f"p{i}", "type": "float", "min": 0, "max": 1} for i in range(9)]
        spec = write_plugin_spec(tmp_path / "wide.json", params=params)
        VcvProject(spec, target_dir=str(tmp_path)).generate()
        assert 'width="45.72mm"' in (tmp_path / "wide" / "res" / "Wide.svg").read_text()

    CLAP_SPECS = [
        pytest.param({}, id="gain-example"),
        pytest.param({"n_channels": 1, "params": []}, id="mono-no-params"),
        pytest.param(
            {
                "n_channels": 3,
                "params": [{"name": "drive", "type": "float", "min": -1e-05, "max": 24, "initial": 0}],
                "meta": dict(PLUGIN_META, author='a "q" \\ b', desc="two\nlines"),
            },
            id="three-channels-escaped-meta",
        ),
    ]

    @pytest.mark.parametrize("ext", CLAP_SPECS)
    def test_clap_plugin_runs_in_host(self, tmp_path: Path, ext: Dict[str, Any]) -> None:
        """Generated CLAP compiles warning-free and passes tests/clap/host.c."""
        cc, cxx = shutil.which("cc"), shutil.which("c++")
        if cc is None or cxx is None:
            pytest.skip("no C/C++ compiler")
        if ext:
            spec = write_plugin_spec(tmp_path / "gain.json", **ext)
        else:
            spec = tmp_path / "gain.yml"
            shutil.copy(self.GAIN, spec)
        ClapProject(spec, target_dir=str(tmp_path)).generate()

        src = tmp_path / "gain"
        inc = ["-I", str(self.CLAP_DIR / "include")]
        warn = ["-Wall", "-Wextra", "-Werror"]
        run([cc, "-std=c11", "-Wpedantic", *warn, *inc, "-c", str(src / "gain.c"), "-o", str(src / "gain.o")])
        run([cxx, "-std=c++17", *warn, *inc, "-c", str(src / "gain_entry.cpp"), "-o", str(src / "entry.o")])
        run([cc, "-std=c11", *warn, *inc, "-c", str(self.CLAP_DIR / "host.c"), "-o", str(src / "host.o")])
        run([cxx, "-o", str(src / "host"), str(src / "host.o"), str(src / "gain.o"), str(src / "entry.o")])
        run([str(src / "host"), "my.gain"])

    @pytest.mark.skipif(not os.environ.get("RACK_DIR"), reason="RACK_DIR (Rack SDK path) not set")
    @pytest.mark.parametrize("ext", CLAP_SPECS)
    def test_vcv_plugin_builds(self, tmp_path: Path, ext: Dict[str, Any]) -> None:
        """Generated VCV plugin builds against the Rack SDK at $RACK_DIR."""
        if ext:
            spec = write_plugin_spec(tmp_path / "gain.json", **ext)
        else:
            spec = tmp_path / "gain.yml"
            shutil.copy(self.GAIN, spec)
        VcvProject(spec, target_dir=str(tmp_path)).generate()
        build_vcv(tmp_path / "gain")


class TestBuiltinExamples:
    """Built-in example specs, addressed by name and built for each target they support."""

    ALL = ["pd", "max", "clap", "vcv"]
    MATRIX = {
        "counter.json": ALL,  # plugins ignore its 'external' block
        "counter.yml": ALL,
        "gain.yml": ["clap", "vcv"],  # n_channels without '~': plugins only
        "lowpass~.yml": ALL,
        "oscil~.yml": ALL,
        "reslp~.yml": ALL,
    }
    STUBS = Path(__file__).parent

    def test_target_matrix(self) -> None:
        """A new or changed example must update MATRIX, so portability cannot regress silently."""
        found = {p.name: example_targets(p) for p in EXAMPLES_DIR.iterdir()
                 if p.suffix in (".yml", ".json")}
        assert found == self.MATRIX

    def test_list_examples_shows_targets(self, capsys: pytest.CaptureFixture[str]) -> None:
        list_examples()
        lines = capsys.readouterr().out.splitlines()
        for name, targets in self.MATRIX.items():
            assert any(line.split() == [name, *(t + "," for t in targets[:-1]), targets[-1]]
                       for line in lines), name

    @pytest.mark.parametrize(
        "name, expected",
        [("counter", "counter.yml"), ("counter.json", "counter.json"),
         ("lowpass~", "lowpass~.yml"), ("nosuch", None)],
    )
    def test_find_example(self, name: str, expected: Optional[str]) -> None:
        found = find_example(name)
        assert (found.name if found else None) == expected

    def test_local_path_wins(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import sys
        from unittest.mock import patch

        spec = {"name": "local", "namespace": "my",
                "meta": {"desc": "", "features": [], "author": "", "repo": ""}}
        (tmp_path / "gain.json").write_text(json.dumps(spec))
        monkeypatch.chdir(tmp_path)
        with patch.object(sys, "argv", ["xtgen", "-q", "-o", "out", "gain.json"]):
            assert main() == 0
        assert (tmp_path / "out" / "gain" / "local.c").is_file()

    def test_unknown_name_fails(self, capsys: pytest.CaptureFixture[str]) -> None:
        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", ["xtgen", "nosuch"]):
            assert main() == 1
        assert "built-in example not found: nosuch" in capsys.readouterr().err

    @pytest.mark.parametrize(
        "example, target",
        [(e, t) for e, ts in MATRIX.items() for t in ts if e != "counter.json"],
    )
    def test_readme_headings(self, tmp_path: Path, example: str, target: str) -> None:
        """Markdown headings render as '## ', not as escaped '\\##'."""
        if example == "reslp~.yml":
            pytest.importorskip("gen_dsp.graph")
        project = TARGETS[target](EXAMPLES_DIR / example, target_dir=str(tmp_path))
        project.generate()
        text = (project.project_path / "README.md").read_text()
        headings = [line for line in text.splitlines() if "##" in line]
        assert headings and all(h.startswith("## ") for h in headings), headings
        assert "## Parameters" in text
        assert ("## DSP" in text) == (example == "reslp~.yml")

    @pytest.mark.parametrize(
        "example, target",
        [(e, t) for e, ts in MATRIX.items() for t in ts],
    )
    def test_example_builds(self, tmp_path: Path, example: str, target: str) -> None:
        """Generated by bare name; C sources compile, and CLAP passes tests/clap/host.c."""
        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", ["xtgen", "-q", "-t", target, "-o", str(tmp_path), example]):
            assert main() == 0
        stem = Path(example).stem
        dsp = stem.endswith("~")
        name = stem.strip("~")

        if target in ("pd", "max"):
            source = tmp_path / stem / f"{name}{'~' if dsp else ''}.c"
            assert source.is_file()
            check_c_syntax(source, target)
        elif target == "clap":
            # Graph DSP is not pass-through, so only require finite output.
            graph = (tmp_path / name / f"{name}_dsp.c").is_file()
            build_and_run_clap(tmp_path / name, name, f"my.{name}", *(["finite"] if graph else []))
        else:
            module = name[0].upper() + name[1:]
            for f in ("plugin.json", "Makefile", f"src/{module}.cpp", f"res/{module}.svg"):
                assert (tmp_path / name / f).is_file(), f

def find_pd() -> Optional[str]:
    """Return a Pd binary: $PD, pd on PATH, or a macOS app bundle."""
    import glob

    if os.environ.get("PD"):
        return os.environ["PD"]
    found = shutil.which("pd")
    if found:
        return found
    apps = sorted(glob.glob("/Applications/Pd*.app") + glob.glob("/Applications/*/Pd*.app"))
    return apps[-1] + "/Contents/Resources/bin/pd" if apps else None


# Two-channel patch: feed 1 and 3, snapshot both outlets, send MESSAGE, snapshot again, quit.
_TWO_CHANNEL_PATCH = r"""#N canvas 0 0 600 400 12;
#X obj 10 10 loadbang;
#X obj 10 40 t b b;
#X msg 120 40 \; pd dsp 1;
#X obj 10 70 delay 5;
#X obj 200 70 sig~ 1;
#X obj 280 70 sig~ 3;
#X obj 200 130 OBJECT;
#X obj 200 170 snapshot~;
#X obj 300 170 snapshot~;
#X obj 200 200 print L;
#X obj 300 200 print R;
#X msg 120 100 MESSAGE;
#X obj 10 130 delay 5;
#X msg 10 230 \; pd quit;
#X obj 10 100 t b b b;
#X obj 10 160 t b b;
#X connect 0 0 1 0;
#X connect 1 1 2 0;
#X connect 1 0 3 0;
#X connect 3 0 14 0;
#X connect 14 2 7 0;
#X connect 14 2 8 0;
#X connect 14 1 11 0;
#X connect 14 0 12 0;
#X connect 12 0 15 0;
#X connect 15 1 7 0;
#X connect 15 1 8 0;
#X connect 15 0 13 0;
#X connect 4 0 6 0;
#X connect 5 0 6 1;
#X connect 6 0 7 0;
#X connect 6 1 8 0;
#X connect 11 0 6 0;
#X connect 7 0 9 0;
#X connect 8 0 10 0;
"""


def two_channel_patch(obj: str, message: Optional[str] = None) -> str:
    """Pd patch printing obj~'s two signal outlets, before and after an optional message."""
    patch = _TWO_CHANNEL_PATCH.replace("OBJECT", obj).replace("MESSAGE", message or "bang")
    return patch if message else patch.replace("#X connect 11 0 6 0;\n", "")


SCALE_TEST_PATCH = two_channel_patch("scale~", "gain 2")


class TestDspGraph:
    """Specs whose 'dsp' field names a gen-dsp graph (needs gen-dsp with lang='c')."""

    DSP_DIR = Path(__file__).parent / "dsp"
    SCALE = DSP_DIR / "scale~.yml"  # stereo gain, param gain 0..2 = 0.5
    SINE = DSP_DIR / "sine~.yml"  # generator: no audio inputs
    HYBRID = {"external": {
        "outlets": [{"name": "f", "type": "float"}, {"name": "b", "type": "bang"}],
        "type_methods": [{"type": "bang"}, {"type": "list"}],
        "message_methods": [{"name": "reset", "params": []},
                            {"name": "set", "params": ["float", "float"]}],
    }}

    @pytest.fixture(autouse=True)
    def _needs_gen_dsp(self) -> None:
        pytest.importorskip("gen_dsp.graph")

    def write_spec(self, path: Path, **ext: Any) -> Path:
        shutil.copy(self.DSP_DIR / "scale.gdsp", path.parent / "scale.gdsp")
        base = {"namespace": "test", "name": "scale", "dsp": "scale.gdsp",
                "meta": {"desc": "", "features": [], "author": "", "repo": ""}}
        path.write_text(json.dumps({**base, **ext}))
        return path

    def test_graph_supplies_params(self) -> None:
        spec = PdProject(self.SCALE).validate()
        assert spec["params"] == [
            {"name": "gain", "type": "float", "min": 0.0, "max": 2.0, "initial": 0.5}
        ]

    @pytest.mark.parametrize(
        "target, src, build_file, build_ref",
        [
            ("pd", "scale~", "scale~/Makefile", "scale_dsp.c"),
            ("max", "scale~", "scale~/README.md", "scale_dsp.c"),  # no build file: README says
            ("clap", "scale", "scale/CMakeLists.txt", "scale_dsp.c"),
            ("vcv", "scale/src", "scale/Makefile", "src/*.c"),
        ],
    )
    def test_writes_graph_sources(
        self, tmp_path: Path, target: str, src: str, build_file: str, build_ref: str
    ) -> None:
        TARGETS[target](self.SCALE, target_dir=str(tmp_path)).generate()
        header = (tmp_path / src / "scale_dsp.h").read_text()
        assert "ScaleDspState* scale_dsp_create(float sr);" in header
        assert 'extern "C"' in header
        assert "#include <math.h>" in (tmp_path / src / "scale_dsp.c").read_text()
        assert build_ref in (tmp_path / build_file).read_text()

    @pytest.mark.parametrize("spec", [SCALE, SINE])
    def test_pd_source_compiles(self, tmp_path: Path, spec: Path) -> None:
        PdProject(spec, target_dir=str(tmp_path)).generate()
        check_c_syntax(tmp_path / spec.stem / f"{spec.stem}.c", "pd")

    @pytest.mark.parametrize("hybrid", [False, True])
    def test_pd_external_runs_in_pd(self, tmp_path: Path, hybrid: bool) -> None:
        """Builds with pd-lib-builder and checks outlet values in real Pd.

        The hybrid object also has message outlets and methods; 'bang' and
        'reset' are sent to it, and their stubs must run.
        """
        import subprocess

        pd = find_pd()
        if pd is None or shutil.which("make") is None:
            pytest.skip("Pd (set $PD) or make not available")
        spec = self.write_spec(tmp_path / "scale~.json", **(self.HYBRID if hybrid else {}))
        PdProject(spec, target_dir=str(tmp_path / "out")).generate()
        project = tmp_path / "out" / "scale~"
        pd_include = Path(__file__).parents[1] / "src" / "xtgen" / "resources" / "pd"
        run(["make", f"PDINCLUDEDIR={pd_include}"], cwd=project)
        patch = SCALE_TEST_PATCH
        if hybrid:
            patch += ("#X msg 400 40 bang;\n#X msg 450 40 reset;\n#X connect 1 1 16 0;\n"
                      "#X connect 1 1 17 0;\n#X connect 16 0 6 0;\n#X connect 17 0 6 0;\n")
        (project / "run.pd").write_text(patch)
        result = subprocess.run(
            [pd, "-nogui", "-batch", "-noaudio", "-nomidi", "-stderr", "-path", ".",
             "-open", "run.pd"],
            cwd=project, capture_output=True, text=True, timeout=30,
        )
        printed = [line for line in result.stderr.splitlines() if line[:3] in ("L: ", "R: ")]
        # default gain 0.5, then 2 after the 'gain 2' message; inputs are 1 and 3
        assert printed == ["L: 0.5", "R: 1.5", "L: 2", "R: 6"], result.stderr
        if hybrid:
            assert "bang body" in result.stderr and "reset body" in result.stderr

    def test_clap_applies_graph_and_param_events(self, tmp_path: Path) -> None:
        """Output is input * 0.5 (default), then * 2.0 from the param event at FRAMES / 2."""
        ClapProject(self.SCALE, target_dir=str(tmp_path)).generate()
        build_and_run_clap(tmp_path / "scale", "scale", "test.scale", "gain", "0.5", "2")

    def test_clap_modulates_graph_param(self, tmp_path: Path) -> None:
        """A CLAP_EVENT_PARAM_MOD of +1.5 on gain 0.5 gives input * 2.0, leaving the value at 0.5."""
        spec = self.write_spec(tmp_path / "scale~.json", plugin={"modulated": ["gain"]})
        ClapProject(spec, target_dir=str(tmp_path)).generate()
        build_and_run_clap(tmp_path / "scale", "scale", "test.scale", "mod", "0.5", "2")

    def test_vcv_graph_param_takes_cv(self, tmp_path: Path) -> None:
        spec = self.write_spec(tmp_path / "scale~.json", plugin={"modulated": ["gain"]})
        VcvProject(spec, target_dir=str(tmp_path)).generate()
        module = (tmp_path / "scale" / "src" / "Scale.cpp").read_text()
        assert ("scale_dsp_set_param(dsp, 0, clamp(params[GAIN_PARAM].getValue() "
                "+ inputs[GAIN_CV_INPUT].getVoltage() / 10.f * 2.0f,") in module

    def test_clap_generator_has_no_input_port(self, tmp_path: Path) -> None:
        ClapProject(self.SINE, target_dir=str(tmp_path)).generate()
        build_and_run_clap(tmp_path / "sine", "sine", "test.sine", "finite")

    @pytest.mark.parametrize(
        "ext, target, error",
        [
            ({"params": []}, "pd", "'params' come(s) from the 'dsp' graph"),
            ({"n_channels": 2}, "clap", "'n_channels' come(s) from the 'dsp' graph"),
            ({"external": {"type_methods": [{"type": "float"}]}}, "pd", "conflicts with the main signal inlet"),
            ({"external": {"message_methods": [{"name": "gain", "params": ["float"]}]}}, "pd", "name of a graph param"),
            ({"external": {"message_methods": [{"name": "gain", "params": ["float"]}]}}, "max", "name of a graph param"),
            ({"external": {"message_methods": [{"name": "dsp64", "params": []}]}}, "max", "built-in method"),
            ({"external": {"message_methods": [{"name": "dsp", "params": []}]}}, "pd", "name of a graph param"),
            ({"external": {"inlets": ["gain"]}}, "pd", "cannot name graph params"),
            ({"external": {"args": ["gain"]}}, "max", "cannot name graph params"),
            ({"plugin": {"modulated": ["cutoff"]}}, "clap", "'plugin.modulated' names unknown param 'cutoff'"),
            ({"dsp": "missing.gdsp"}, "pd", "'dsp' graph not found"),
            ({"dsp": 3}, "pd", "'dsp' must be a path"),
        ],
    )
    def test_invalid_dsp_spec_rejected(
        self, tmp_path: Path, ext: Dict[str, Any], target: str, error: str
    ) -> None:
        spec = self.write_spec(tmp_path / "scale~.json", **ext)
        with pytest.raises(ValueError, match=re.escape(error)):
            TARGETS[target](spec, target_dir=str(tmp_path)).generate()
        assert not (tmp_path / "scale~").exists() and not (tmp_path / "scale").exists()

    @pytest.mark.parametrize("target", ["pd", "max"])
    def test_needs_tilde_filename(self, tmp_path: Path, target: str) -> None:
        spec = self.write_spec(tmp_path / "scale.json")
        with pytest.raises(ValueError, match=r"name the spec file 'scale~\.json'"):
            TARGETS[target](spec).validate()

    def test_pd_hybrid_compiles(self, tmp_path: Path) -> None:
        """A graph object can also have message outlets and type/message methods."""
        spec = self.write_spec(tmp_path / "scale~.json", **self.HYBRID)
        PdProject(spec, target_dir=str(tmp_path / "out")).generate()
        source = tmp_path / "out" / "scale~" / "scale~.c"
        check_c_syntax(source, "pd")
        text = source.read_text()
        assert "x->out_f = outlet_new(&x->x_obj, &s_float);" in text
        assert 'gensym("reset")' in text and "class_addbang(" in text

    def test_generator_may_have_float_method(self, tmp_path: Path) -> None:
        """Without a main signal inlet, a 'float' type method is free to use."""
        shutil.copy(self.DSP_DIR / "sine.gdsp", tmp_path / "sine.gdsp")
        spec = tmp_path / "sine~.json"
        spec.write_text(json.dumps({
            "namespace": "test", "name": "sine", "dsp": "sine.gdsp",
            "external": {"type_methods": [{"type": "float"}]},
            "meta": {"desc": "", "features": [], "author": "", "repo": ""},
        }))
        PdProject(spec, target_dir=str(tmp_path / "out")).generate()
        check_c_syntax(tmp_path / "out" / "sine~" / "sine~.c", "pd")

    @pytest.mark.parametrize("spec", [SCALE, SINE])
    def test_max_source_compiles(self, tmp_path: Path, spec: Path) -> None:
        MaxProject(spec, target_dir=str(tmp_path)).generate()
        check_c_syntax(tmp_path / spec.stem / f"{spec.stem}.c", "max")

    @pytest.mark.parametrize(
        "spec, args",
        [(SCALE, ["2", "2", "gain", "0.5", "2"]), (SINE, ["0", "1"])],
    )
    def test_max_external_runs(self, tmp_path: Path, spec: Path, args: List[str]) -> None:
        """Through a fake Max runtime, with input and output buffers aliased."""
        MaxProject(spec, target_dir=str(tmp_path)).generate()
        build_and_run_max(tmp_path / spec.stem, spec.stem.strip("~"), *args)

    def test_max_hybrid_runs(self, tmp_path: Path) -> None:
        """A Max graph object with outlets and methods still links and runs."""
        spec = self.write_spec(tmp_path / "scale~.json", **self.HYBRID)
        MaxProject(spec, target_dir=str(tmp_path / "out")).generate()
        source = tmp_path / "out" / "scale~" / "scale~.c"
        check_c_syntax(source, "max")
        assert 'class_addmethod(c, (method)scale_set, "set", A_FLOAT, A_FLOAT, 0);' in source.read_text()
        build_and_run_max(source.parent, "scale", "2", "2", "gain", "0.5", "2")

    @pytest.mark.parametrize(
        "spec, feature, au_type",
        [(SCALE, "CLAP_PLUGIN_FEATURE_AUDIO_EFFECT", "aufx"),
         (SINE, "CLAP_PLUGIN_FEATURE_INSTRUMENT", "aumu")],
    )
    def test_clap_generator_is_instrument(
        self, tmp_path: Path, spec: Path, feature: str, au_type: str
    ) -> None:
        """clap-wrapper takes the AU type from the first feature; it builds no 'augn'."""
        ClapProject(spec, target_dir=str(tmp_path)).generate()
        name = spec.stem.strip("~")
        source = (tmp_path / name / f"{name}.c").read_text()
        features = source[source.index("_features[] = {"):]
        first = next(line.strip() for line in features.splitlines()[1:] if "FEATURE" in line)
        assert first.startswith(feature + ",")
        cmake = (tmp_path / name / "CMakeLists.txt").read_text()
        assert f'AUV2_INSTRUMENT_TYPE "{au_type}"' in cmake

    @pytest.mark.parametrize("spec, tags", [(SCALE, ["Effect"]), (SINE, [])])
    def test_vcv_graph_module(self, tmp_path: Path, spec: Path, tags: List[str]) -> None:
        VcvProject(spec, target_dir=str(tmp_path)).generate()
        name = spec.stem.strip("~")
        manifest = json.loads((tmp_path / name / "plugin.json").read_text())
        assert manifest["modules"][0]["tags"] == tags
        module = (tmp_path / name / "src" / f"{name.capitalize()}.cpp").read_text()
        assert f"{name}_dsp_perform(dsp," in module

    @pytest.mark.skipif(not os.environ.get("RACK_DIR"), reason="RACK_DIR (Rack SDK path) not set")
    @pytest.mark.parametrize(
        "spec, args",
        [(SCALE, ["2", "2", "0.5", "2"]), (SINE, ["0", "1"])],
    )
    def test_vcv_graph_runs_in_rack(self, tmp_path: Path, spec: Path, args: List[str]) -> None:
        """Builds against the Rack SDK and runs the module headless with libRack."""
        VcvProject(spec, target_dir=str(tmp_path)).generate()
        name = spec.stem.strip("~")
        build_vcv(tmp_path / name)
        run_in_rack(tmp_path / name, name.capitalize(), *args)

    @pytest.mark.parametrize(
        "graph, error",
        [
            ("graph g {\n in x\n out o = y\n param dsp 0..1 = 0\n y = x * dsp\n}",
             "shadows a built-in method name"),
            ("graph g { in x out }", "Invalid 'dsp' graph"),
        ],
    )
    def test_invalid_graph_rejected(self, tmp_path: Path, graph: str, error: str) -> None:
        spec = self.write_spec(tmp_path / "scale~.json")
        (tmp_path / "scale.gdsp").write_text(graph)
        with pytest.raises(ValueError, match=error):
            PdProject(spec).validate()

    def test_missing_gen_dsp_explained(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import sys

        monkeypatch.setitem(sys.modules, "gen_dsp.graph.compile", None)
        with pytest.raises(ValueError, match=r"pip install 'xtgen\[dsp\]'"):
            PdProject(self.SCALE).validate()


class TestFieldSupport:
    """pd and max implement the spec fields they accept, and reject the rest."""

    META = {"desc": "", "features": [], "author": "", "repo": ""}

    def write(self, path: Path, **ext: Any) -> Path:
        path.write_text(json.dumps({"namespace": "test", "name": "thing", "meta": self.META, **ext}))
        return path

    @pytest.mark.parametrize(
        "filename, ext, target, error",
        [
            ("thing.json", {"n_channels": 2}, "pd", "'n_channels'"),
            ("thing.json", {"n_channels": 2}, "max", "'n_channels'"),
            ("thing.json", {"external": {"help": "help-thing"}}, "max", "'external.help'"),
            ("thing~.json", {"external": {"help": "help-thing"}}, "max", "'external.help'"),
            ("thing.json", {"external": {"type_methods": [{"type": "pointer"}]}}, "max", "'pointer'"),
            ("thing~.json", {"external": {"type_methods": [{"type": "float"}]}}, "pd", "main signal inlet"),
        ],
    )
    def test_unused_fields_rejected(
        self, tmp_path: Path, filename: str, ext: Dict[str, Any], target: str, error: str
    ) -> None:
        spec = self.write(tmp_path / filename, **ext)
        with pytest.raises(ValueError, match=re.escape(error)):
            TARGETS[target](spec, target_dir=str(tmp_path)).generate()
        assert not any(tmp_path.iterdir()) or list(tmp_path.iterdir()) == [spec]

    @pytest.mark.parametrize(
        "filename, struct, setup",
        [("thing.json", "t_abc", "void thing_setup(void)"),
         ("thing~.json", "t_abc_tilde", "void thing_tilde_setup(void)")],
    )
    def test_pd_prefix_names_identifiers(
        self, tmp_path: Path, filename: str, struct: str, setup: str
    ) -> None:
        """'prefix' names the C struct, class and functions; Pd still finds <name>_setup."""
        spec = self.write(tmp_path / filename, external={
            "prefix": "abc", "alias": "thg", "type_methods": [{"type": "bang"}]})
        PdProject(spec, target_dir=str(tmp_path / "out")).generate()
        stem = Path(filename).stem
        source = tmp_path / "out" / stem / f"{stem}.c"
        text = source.read_text()
        assert f"}} {struct};" in text and setup in text
        assert f'class_new(gensym("{stem}")' in text
        assert "thing_class" not in text and "thing_tilde_class" not in text
        check_c_syntax(source, "pd")

    @pytest.mark.parametrize("target", ["pd", "max"])
    def test_control_object_float_method(self, tmp_path: Path, target: str) -> None:
        """Only a Pd signal inlet takes over floats; control objects and Max keep the method."""
        for filename in ("thing.json",) + (("thing~.json",) if target == "max" else ()):
            spec = self.write(tmp_path / filename, external={"type_methods": [{"type": "float"}]})
            TARGETS[target](spec).validate()

    def test_pd_signal_channels(self, tmp_path: Path) -> None:
        spec = self.write(tmp_path / "thing~.json", n_channels=3)
        PdProject(spec, target_dir=str(tmp_path / "out")).generate()
        source = tmp_path / "out" / "thing~" / "thing~.c"
        assert "#define N_CHANNELS 3\n" in source.read_text()
        check_c_syntax(source, "pd")

    def test_pd_signal_channels_run_in_pd(self, tmp_path: Path) -> None:
        """Two-channel pass-through in real Pd: each outlet copies its inlet."""
        import subprocess

        pd = find_pd()
        if pd is None or shutil.which("make") is None:
            pytest.skip("Pd (set $PD) or make not available")
        spec = self.write(tmp_path / "thing~.json", n_channels=2)
        PdProject(spec, target_dir=str(tmp_path / "out")).generate()
        project = tmp_path / "out" / "thing~"
        pd_include = Path(__file__).parents[1] / "src" / "xtgen" / "resources" / "pd"
        run(["make", f"PDINCLUDEDIR={pd_include}"], cwd=project)
        (project / "run.pd").write_text(two_channel_patch("thing~"))
        result = subprocess.run(
            [pd, "-nogui", "-batch", "-noaudio", "-nomidi", "-stderr", "-path", ".",
             "-open", "run.pd"],
            cwd=project, capture_output=True, text=True, timeout=30,
        )
        printed = [line for line in result.stderr.splitlines() if line[:3] in ("L: ", "R: ")]
        assert printed == ["L: 1", "R: 3", "L: 1", "R: 3"], result.stderr

    def test_max_methods_and_alias(self, tmp_path: Path) -> None:
        """Max registers the spec's type and message methods and its alias."""
        MaxProject(EXAMPLES_DIR / "counter.yml", target_dir=str(tmp_path)).generate()
        source = tmp_path / "counter" / "counter.c"
        text = source.read_text()
        for line in (
            'class_addmethod(c, (method)ctr_float, "float", A_FLOAT, 0);',
            'class_addmethod(c, (method)ctr_symbol, "symbol", A_SYM, 0);',
            'class_addmethod(c, (method)ctr_bound, "bound", A_FLOAT, A_FLOAT, 0);',
            'class_addmethod(c, (method)ctr_reset, "reset", 0);',
            'class_alias(c, gensym("cntr"));',
            "void ctr_bound(t_ctr *x, double f0, double f1)",
        ):
            assert line in text, line
        # a declared 'bang' replaces the generic one
        assert text.count('"bang"') == 1
        check_c_syntax(source, "max")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
