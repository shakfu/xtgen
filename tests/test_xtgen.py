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
import yaml
import os

from xtgen import (
    ScalarType, CompoundType, External, TypeMethod, MessageMethod,
    Param, Outlet, PdProject, MaxProject, Generator, AudioTypeError,
    TypeMapper, ArgumentBuilder, CodeGenerator
)


class TestTypeSystem:
    """Test the audio type system classes."""

    def test_scalar_type_valid_types(self):
        """Test ScalarType with valid types."""
        for valid_type in ["bang", "float", "symbol", "pointer", "signal"]:
            scalar = ScalarType(valid_type)
            assert scalar.name == valid_type
            assert str(scalar) == valid_type

    def test_scalar_type_invalid_type(self):
        """Test ScalarType with invalid type raises AudioTypeError."""
        with pytest.raises(AudioTypeError):
            ScalarType("invalid_type")

    def test_scalar_type_properties(self):
        """Test ScalarType property generation."""
        float_type = ScalarType("float")
        assert float_type.c_type == "t_float"
        assert float_type.lookup_address == "&s_float"
        assert float_type.lookup_routine == 'gensym("float")'
        assert float_type.type_method_arg == "t_floatarg f"

    def test_compound_type_valid_types(self):
        """Test CompoundType with valid types."""
        for valid_type in ["list", "anything"]:
            compound = CompoundType(valid_type)
            assert compound.name == valid_type

    def test_compound_type_properties(self):
        """Test CompoundType property generation."""
        list_type = CompoundType("list")
        assert list_type.c_type == "t_list"
        assert list_type.type_method_arg == "t_symbol *s, int argc, t_atom *argv"

        # Test 'anything' type doesn't have c_type
        anything_type = CompoundType("anything")
        with pytest.raises(AudioTypeError):
            anything_type.c_type


class TestExternalModel:
    """Test External class and related components."""

    @pytest.fixture
    def sample_external_data(self):
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
                    "desc": "step size"
                }
            ],
            "outlets_data": [
                {"name": "f", "type": "float"},
                {"name": "b", "type": "bang"}
            ],
            "message_methods_data": [
                {
                    "name": "reset",
                    "params": [],
                    "doc": "reset counter to zero"
                }
            ],
            "type_methods_data": [
                {
                    "type": "bang",
                    "doc": "increment counter"
                }
            ]
        }

    def test_external_creation(self, sample_external_data):
        """Test External object creation from data."""
        external = External(**sample_external_data)
        assert external.name == "counter"
        assert external.type == "t_counter"
        assert external.klass == "counter_class"

    def test_external_params(self, sample_external_data):
        """Test External params property."""
        external = External(**sample_external_data)
        params = external.params
        assert len(params) == 1
        assert params[0].name == "step"
        assert params[0].type == "float"
        assert params[0].is_arg == True

    def test_external_outlets(self, sample_external_data):
        """Test External outlets property."""
        external = External(**sample_external_data)
        outlets = external.outlets
        assert len(outlets) == 2
        assert outlets[0].name == "f"
        assert outlets[1].type == "bang"

    def test_external_methods(self, sample_external_data):
        """Test External method properties."""
        external = External(**sample_external_data)

        # Test message methods
        msg_methods = external.message_methods
        assert len(msg_methods) == 1
        assert msg_methods[0].name == "reset"

        # Test type methods
        type_methods = external.type_methods
        assert len(type_methods) == 1
        assert type_methods[0].type == "bang"


class TestMethodGeneration:
    """Test method generation for External objects."""

    @pytest.fixture
    def external_with_methods(self):
        """External with various method types for testing."""
        return External(
            name="test",
            namespace="test",
            message_methods_data=[
                {"name": "simple", "params": [], "doc": "simple method"},
                {"name": "with_float", "params": ["float"], "doc": "method with float"},
                {"name": "with_multiple", "params": ["float", "symbol"], "doc": "method with multiple params"}
            ],
            type_methods_data=[
                {"type": "bang", "doc": "bang handler"},
                {"type": "float", "doc": "float handler"},
                {"type": "list", "doc": "list handler"}
            ],
            params_data=[],
            outlets_data=[]
        )

    def test_type_method_args(self, external_with_methods):
        """Test TypeMethod argument generation."""
        type_methods = external_with_methods.type_methods

        bang_method = next(m for m in type_methods if m.type == "bang")
        assert "t_test *x" in bang_method.args

        float_method = next(m for m in type_methods if m.type == "float")
        assert "t_floatarg f" in float_method.args

        list_method = next(m for m in type_methods if m.type == "list")
        assert "t_symbol *s, int argc, t_atom *argv" in list_method.args

    def test_message_method_args(self, external_with_methods):
        """Test MessagedMethod argument generation."""
        msg_methods = external_with_methods.message_methods

        simple = next(m for m in msg_methods if m.name == "simple")
        assert simple.args == "t_test *x"

        with_float = next(m for m in msg_methods if m.name == "with_float")
        assert "t_floatarg f0" in with_float.args


class TestYAMLProcessing:
    """Test YAML file processing and validation."""

    def test_valid_yaml_processing(self):
        """Test processing of valid YAML file."""
        yaml_content = """
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
        temp_dir = tempfile.mkdtemp()
        yaml_path = Path(temp_dir) / "simple.yml"
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)

        try:
            generator = Generator(yaml_path)
            assert generator.name == "simple"
            assert generator.fullname == "simple"
            assert generator.is_dsp == False
        finally:
            shutil.rmtree(temp_dir)

    def test_dsp_external_detection(self):
        """Test DSP external detection from filename."""
        yaml_content = """
externals:
  - namespace: test
    name: osc
    prefix: osc
    params: []
    outlets: []
    message_methods: []
    type_methods: []
"""
        temp_dir = tempfile.mkdtemp()
        yaml_path = Path(temp_dir) / "osc~.yml"
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)

        try:
            generator = Generator(yaml_path)
            assert generator.is_dsp == True
            assert generator.name == "osc"
        finally:
            shutil.rmtree(temp_dir)


class TestProjectGeneration:
    """Test end-to-end project generation."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test output."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_yaml_file(self, temp_dir):
        """Create a sample YAML file for testing."""
        yaml_content = """
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
        yaml_path = Path(temp_dir) / "testobj.yml"
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)
        return yaml_path

    def test_pd_project_generation(self, sample_yaml_file, temp_dir):
        """Test PureData project generation."""
        project = PdProject(sample_yaml_file, target_dir=temp_dir)
        project.generate()

        # Check that files were created
        project_dir = Path(temp_dir) / "testobj"
        assert project_dir.exists()
        assert (project_dir / "testobj.c").exists()
        assert (project_dir / "Makefile").exists()
        assert (project_dir / "README.md").exists()
        assert (project_dir / "Makefile.pdlibbuilder").exists()

    def test_max_project_generation(self, sample_yaml_file, temp_dir):
        """Test Max/MSP project generation."""
        project = MaxProject(sample_yaml_file, target_dir=temp_dir)
        project.generate()

        # Check that files were created
        project_dir = Path(temp_dir) / "testobj"
        assert project_dir.exists()
        assert (project_dir / "testobj.c").exists()
        assert (project_dir / "README.md").exists()

    def test_generated_c_file_content(self, sample_yaml_file, temp_dir):
        """Test that generated C file contains expected content."""
        project = PdProject(sample_yaml_file, target_dir=temp_dir)
        project.generate()

        c_file = Path(temp_dir) / "testobj" / "testobj.c"
        content = c_file.read_text()

        # Check for essential C code elements
        assert "typedef struct _testobj" in content
        assert "static t_class *testobj_class" in content
        assert "t_float value" in content  # parameter
        assert "t_outlet *out_out" in content  # outlet
        assert "A test object" in content  # description from meta


class TestHelperClasses:
    """Test the new focused helper classes."""

    def test_type_mapper(self):
        """Test TypeMapper functionality."""
        mapper = TypeMapper()

        # Test valid mappings
        assert mapper.get_pd_mapping("float") == "A_DEFFLOAT"
        assert mapper.get_func_arg("float") == "t_floatarg f"

        # Test invalid types
        with pytest.raises(AudioTypeError):
            mapper.get_pd_mapping("invalid_type")

        with pytest.raises(AudioTypeError):
            mapper.get_func_arg("invalid_type")

    def test_argument_builder(self):
        """Test ArgumentBuilder functionality."""
        mapper = TypeMapper()
        builder = ArgumentBuilder(mapper)

        # Test empty args
        assert builder.build_constructor_args([]) == "void"

        # Test type signature
        assert builder.build_type_signature([]) == ", 0"

    def test_code_generator(self):
        """Test CodeGenerator functionality."""
        mapper = TypeMapper()
        builder = ArgumentBuilder(mapper)
        generator = CodeGenerator(mapper, builder)

        # Test method generation
        method_call = generator.generate_class_addmethod("test", "bang", "bang")
        assert "class_addbang" in method_call
        assert "test_class" in method_call

        # Test message method generation
        message_call = generator.generate_message_addmethod("test", "reset", [])
        assert "class_addmethod" in message_call
        assert "reset" in message_call

    def test_helper_integration(self):
        """Test that helper classes work together correctly."""
        # Create a simple external to test integration
        external_data = {
            "name": "test",
            "namespace": "test",
            "params_data": [],
            "outlets_data": [],
            "message_methods_data": [],
            "type_methods_data": []
        }

        external = External(**external_data)

        # Test that helper objects are created
        assert external.type_mapper is not None
        assert external.arg_builder is not None
        assert external.code_generator is not None

        # Test that they work
        assert external.class_new_args == "void"
        assert external.class_type_signature == ", 0"


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_missing_yaml_file(self):
        """Test handling of missing YAML file."""
        with pytest.raises(FileNotFoundError):
            generator = Generator("nonexistent.yml")
            with open(generator.spec_yml) as f:
                yaml.safe_load(f.read())

    def test_invalid_yaml_content(self):
        """Test handling of invalid YAML content."""
        yaml_content = "invalid: yaml: content: ["
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_content)
            yaml_path = f.name

        try:
            generator = Generator(yaml_path)
            with pytest.raises(yaml.YAMLError):
                with open(generator.spec_yml) as f:
                    yaml.safe_load(f.read())
        finally:
            os.unlink(yaml_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])