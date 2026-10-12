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
        assert external.type == "t_counter"
        assert external.klass == "counter_class"

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
            "externals": [
                {
                    "namespace": "t",
                    "name": "symobj",
                    "params": [
                        {"name": "label", "type": "symbol", "initial": 'a"b',
                         "arg": True, "inlet": True},
                        {"name": "tag", "type": "symbol", "arg": False, "inlet": False},
                    ],
                    "meta": {"desc": "", "author": "", "repo": "", "features": []},
                }
            ]
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
externals:
  - namespace: test
    name: simple
    prefix: smp
    params: []
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
externals:
  - namespace: test
    name: osc
    prefix: osc
    params: []
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
  "externals": [
    {
      "namespace": "test",
      "name": "simple",
      "prefix": "smp",
      "params": [],
      "outlets": [],
      "message_methods": [],
      "type_methods": []
    }
  ]
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
  "externals": [
    {
      "namespace": "test",
      "name": "osc",
      "prefix": "osc",
      "params": [],
      "outlets": [],
      "message_methods": [],
      "type_methods": []
    }
  ]
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
externals:
  - namespace: test
    name: fallback_yaml
    prefix: fy
    params: []
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
            assert spec_data["externals"][0]["name"] == "fallback_yaml"
        finally:
            shutil.rmtree(temp_dir)

        # Test JSON content with unknown extension
        json_content: str = '''{
  "externals": [
    {
      "namespace": "test",
      "name": "fallback_json",
      "prefix": "fj",
      "params": [],
      "outlets": [],
      "message_methods": [],
      "type_methods": []
    }
  ]
}'''
        temp_dir = tempfile.mkdtemp()
        fallback_path = Path(temp_dir) / "fallback.txt"
        with open(fallback_path, "w") as f:
            f.write(json_content)

        try:
            generator = Generator(fallback_path)
            spec_data = generator.load_specification()
            assert spec_data["externals"][0]["name"] == "fallback_json"
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
externals:
  - namespace: test
    name: testobj
    prefix: tst
    alias: testobj
    help: help-testobj
    n_channels: 1
    params:
      - name: value
        type: float
        min: 0.0
        max: 1.0
        initial: 0.5
        arg: true
        inlet: false
        desc: "test value"
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
    meta:
      desc: "A test object"
      author: "test"
      repo: "https://github.com/test/testobj"
      features: ["simple test"]
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
            sample_yaml_file.read_text().replace("    help: help-testobj\n", "")
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
        shutil.copy(get_test_resource_path("resources/examples/counter.yml"), spec)
        PdProject(spec, target_dir=temp_dir).generate()

        source: Path = Path(temp_dir) / spec.stem / f"{spec.stem}.c"
        if spec.stem.endswith("~"):
            content: str = source.read_text()
            # one signal inlet (sp[0]) and one signal outlet (sp[1])
            assert "x->x_out = outlet_new(&x->x_obj, &s_signal);" in content
            assert "sp[2]" not in content

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
  "externals": [
    {
      "namespace": "test",
      "name": "jsonobj",
      "prefix": "json",
      "alias": "jsonobj",
      "help": "help-jsonobj",
      "n_channels": 1,
      "params": [
        {
          "name": "value",
          "type": "float",
          "min": 0.0,
          "max": 1.0,
          "initial": 0.5,
          "arg": true,
          "inlet": false,
          "desc": "test value"
        }
      ],
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
      ],
      "meta": {
        "desc": "A test object from JSON",
        "author": "test",
        "repo": "https://github.com/test/jsonobj",
        "features": ["json test"]
      }
    }
  ]
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
        assert builder.build_type_signature([]) == ", 0"

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
        assert external.class_type_signature == ", 0"


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
    def two_externals_json(self, tmp_path: Path) -> Path:
        path = tmp_path / "pair.json"
        path.write_text(
            '{"externals": ['
            '{"namespace": "my", "name": "first"},'
            '{"namespace": "my", "name": "second"}]}'
        )
        return path

    def test_multiple_externals_rejected(self, two_externals_json: Path) -> None:
        """Extra externals must raise, not be silently dropped."""
        generator = Generator(two_externals_json)
        with pytest.raises(ValueError, match="exactly one external"):
            generator.validate_specification_structure(generator.load_specification())

    @pytest.mark.parametrize(
        "extra, error",
        [
            ('"inlets": [{"name": "bound", "type": "list"}]', "'inlet: true' on each param"),
            ('"outlet": []', "unknown field\\(s\\): 'outlet'"),
        ],
    )
    def test_unread_external_keys_rejected(
        self, tmp_path: Path, extra: str, error: str
    ) -> None:
        """Keys render() never reads must raise, not be silently dropped."""
        path = tmp_path / "ext.json"
        path.write_text(
            '{"externals": [{"namespace": "my", "name": "ext", ' + extra + ", "
            '"meta": {"desc": "d", "features": [], "author": "a", "repo": "r"}}]}'
        )
        generator = Generator(path)
        with pytest.raises(ValueError, match=error):
            generator.validate_specification_structure(generator.load_specification())

    def test_multiple_externals_cli(self, two_externals_json: Path, tmp_path: Path) -> None:
        """Both --validate and generate must fail on a multi-external spec."""
        import sys
        from unittest.mock import patch

        out_dir = tmp_path / "out"
        for args in (["--validate"], ["-o", str(out_dir)]):
            with patch.object(sys, "argv", ["xtgen", *args, str(two_externals_json)]):
                assert main() == 1
        assert not (out_dir / "pair" / "pair.c").exists()

    META = '"meta": {"desc": "d", "features": [], "author": "a", "repo": "r"}'

    @pytest.mark.parametrize(
        "body, error",
        [
            ('"outlets": [{"name": "o", "type": "int"}], ' + META, "Invalid outlet type"),
            ('"type_methods": [{"type": "foo"}], ' + META, "Invalid type method"),
            ('"params": [{"name": "p", "type": "bad"}], ' + META, "Invalid parameter type"),
            ('"outlets": [{"type": "float"}], ' + META, "Outlet must contain required field: 'name'"),
            ('"message_methods": [{"params": []}], ' + META, "Message method must contain"),
            ('"type_methods": [{"doc": "x"}], ' + META, "Type method must contain"),
            ('"outlets": []', "'meta' dictionary"),
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
        spec.write_text('{"externals": [{"namespace": "my", "name": "bad", ' + body + "}]}")
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
externals:
  - name: test
    params: []
    outlets: []
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
    "externals": [{
        "name": "test",
        "params": [],
        "outlets": []
    }]
}"""
        json_file = Path(temp_dir) / "test.json"
        json_file.write_text(json_content)

        # Mock YAML_AVAILABLE to False
        with unittest.mock.patch('xtgen.templates.YAML_AVAILABLE', False):
            project = PdProject(json_file)

            # Should work fine with JSON
            spec = project.load_specification()
            assert spec is not None
            assert "externals" in spec

    @pytest.fixture
    def temp_dir(self) -> TypingGenerator[str, None, None]:
        """Create a temporary directory for CLI test output."""
        temp_dir: str = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)


PLUGIN_META = {"desc": "d", "features": ["f"], "author": "a", "repo": "r"}


def write_plugin_spec(path: Path, **ext: Any) -> Path:
    """Write a one-external JSON spec with plugin defaults overridden by `ext`."""
    data: Dict[str, Any] = {"namespace": "my", "name": path.stem.strip("~"), "meta": PLUGIN_META}
    data.update(ext)
    path.write_text(json.dumps({"externals": [data]}))
    return path


def run(args: List[str], cwd: Optional[Path] = None, env: Optional[Dict[str, str]] = None) -> None:
    """Run a command, failing the test with its stderr."""
    import subprocess

    result = subprocess.run(args, capture_output=True, text=True, cwd=cwd, env=env)
    assert result.returncode == 0, result.stderr + result.stdout


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
    def test_counter_example_rejected(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], target: str
    ) -> None:
        """Pd-only fields fail both --validate and generation, naming the fields."""
        import sys
        from unittest.mock import patch

        counter = get_test_resource_path("resources/examples/counter.yml")
        for args in (["--validate"], ["-o", str(tmp_path)]):
            with patch.object(sys, "argv", ["xtgen", "-t", target, *args, str(counter)]):
                assert main() == 1
            err = capsys.readouterr().err
            assert f"not supported by the {target} target" in err
            assert "'outlets'" in err and "'alias'" in err
        assert not (tmp_path / "counter").exists()

    def test_validate_uses_target_rules(self) -> None:
        counter = get_test_resource_path("resources/examples/counter.yml")
        assert validate_specification(counter, target="pd")
        assert not validate_specification(counter, target="clap")
        assert validate_specification(self.GAIN, target="clap")

    @pytest.mark.parametrize(
        "ext, error",
        [
            ({"params": [{"name": "s", "type": "symbol", "min": 0, "max": 1}]}, "only float params"),
            ({"params": [{"name": "p", "type": "float", "min": 0, "max": 1, "arg": True}]}, "'arg' is not supported"),
            ({"params": [{"name": "p", "type": "float", "max": 1}]}, "must set 'min'"),
            ({"params": [{"name": "p", "type": "float", "min": 0, "max": 1, "initial": 2}]}, "min <= initial <= max"),
            ({"params": [{"name": "p", "type": "float", "min": 1, "max": 1, "initial": 1}]}, "min < max"),
            ({"params": [{"name": "p", "type": "float", "min": "0", "max": 1}]}, "finite numbers"),
            ({"params": [{"name": "p", "type": "float", "min": 0, "max": 1e999}]}, "finite numbers"),
            ({"params": [{"name": "p-q", "type": "float", "min": 0, "max": 1}]}, "ASCII identifier"),
            ({"name": "my-gain"}, "'name' must be an ASCII identifier"),
            ({"namespace": "a.b"}, "'namespace' must be an ASCII identifier"),
            ({"n_channels": 0}, "positive integer"),
            ({"help": "help-x"}, "'help'"),
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
        # plugin.mk appends to FLAGS, so an environment value is kept.
        env = dict(os.environ, FLAGS="-Werror")
        run(["make", f"RACK_DIR={os.environ['RACK_DIR']}"], cwd=tmp_path / "gain", env=env)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
