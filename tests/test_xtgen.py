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
from typing import Dict, Any, List, Generator as TypingGenerator
import os

from xtgen import (
    ScalarType,
    CompoundType,
    External,
    TypeMethod,
    MessageMethod,
    Param,
    Outlet,
    PdProject,
    MaxProject,
    Generator,
    AudioTypeError,
    TypeMapper,
    ArgumentBuilder,
    CodeGenerator,
    main,
    create_argument_parser,
    validate_specification,
    list_examples,
    YAML_AVAILABLE,
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


class TestCommandLineInterface:
    """Test command-line interface functionality."""

    def test_argument_parser_creation(self) -> None:
        """Test that argument parser is created correctly."""
        parser = create_argument_parser()
        assert parser.prog == "xtgen"
        assert parser.description is not None and "Generate PureData and Max/MSP external projects" in parser.description

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
        with unittest.mock.patch('xtgen.core.YAML_AVAILABLE', False):
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
        with unittest.mock.patch('xtgen.core.YAML_AVAILABLE', False):
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
