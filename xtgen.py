#!/usr/bin/env python3
"""xtgen.py

A tool to generate skeleton puredata or max external files.

Requires the following python packages:

- mako
- pyyaml

>>> import xtgen

>>> xtgen.PdProject('counter.yml').generate()
>>> # generates a regular c pd external skeleton

>>> xtgen.PdProject('counter~.yml').generate()
>>> # generates an audio dsp pd external

>>> xtgen.MaxProject('counter.yml').generate()
>>> ... (similar as above)


"""
import argparse
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import yaml
from mako.template import Template
from mako.lookup import TemplateLookup


# ----------------------------------------------------------------------------
# CONSTANTS

TEMPLATE_DIR = os.path.join(os.getcwd(), "templates")
TEMPLATE_LOOKUP = TemplateLookup(directories=[TEMPLATE_DIR])

# ----------------------------------------------------------------------------
# UTILITY FUNCTIONS

c_type = lambda s: f"t_{s}"
lookup_address = lambda s: f"&s_{s}"
lookup_routine = lambda s: f'gensym("{s}")'


# ----------------------------------------------------------------------------
# TYPE CLASSES


class Type:
    VALID_TYPES = []

    def __init__(self, name):
        assert name in self.VALID_TYPES
        self.name = name

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<{self.__class__.__name__}: '{self.name}'>"


class ScalarType(Type):
    VALID_TYPES = ["bang", "float", "symbol", "pointer", "signal"]

    @property
    def c_type(self):
        return f"t_{self.name}"

    @property
    def lookup_address(self):
        return f"&s_{self.name}"

    @property
    def lookup_routine(self):
        return f'gensym("{self.name}")'

    @property
    def type_method_arg(self):
        return {
            "bang": "",
            "float": "t_floatarg f",
            "int": "t_floatarg f",
            "symbol": "t_symbol *s",
            "pointer": "t_gpointer *pt",
        }[self.name]


class CompoundType(Type):
    VALID_TYPES = ["list", "anything"]

    @property
    def c_type(self):
        assert self.name != "anything"  # doesn't exist for 'anything'
        return f"t_{self.name}"

    @property
    def lookup_address(self):
        return f"&s_{self.name}"

    @property
    def lookup_routine(self):
        return f'gensym("{self.name}")'

    @property
    def type_method_arg(self):
        return {
            "list": "t_symbol *s, int argc, t_atom *argv",
            "anything": "t_symbol *s, int argc, t_atom *argv",
        }[self.name]


class Object:
    def __init__(self, parent, **kwargs):
        self.parent = parent
        self.ns = SimpleNamespace(**kwargs)

    def __repr__(self):
        return f"<{self.__class__.__name__}: '{self.name}'>"


class TypeMethod(Object):
    valid_types = ["bang", "float", "int", "symbol", "pointer", "list", "anything"]

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.type = self.ns.type
        self.doc = self.ns.doc if hasattr(self.ns, "doc") else ""
        assert self.type in self.valid_types

    @property
    def name(self):
        return self.type

    @property
    def args(self):
        if self.type == "bang":
            return f"{self.parent.type} *x"

        elif self.type in ["float", "int"]:
            return f"{self.parent.type} *x, t_floatarg f"

        elif self.type == "symbol":
            return f"{self.parent.type} *x, t_symbol *s"

        elif self.type == "pointer":
            return f"{self.parent.type} *x, t_gpointer *pt"

        elif self.type in ["list", "anything"]:
            return f"{self.parent.type} *x, t_symbol *s, int argc, t_atom *argv"

        else:
            raise Exception(f"argument '{self.type}' not implemented")

    @property
    def class_addmethod(self):
        return (
            f"class_add{self.type}({self.parent.klass}, {self.parent.name}_{self.type})"
        )


class MessagedMethod(Object):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.name = self.ns.name
        self.doc = self.ns.doc if hasattr(self.ns, "doc") else ""
        self.params = self.ns.params

    @property
    def args(self):
        prefix = f"{self.parent.type} *x"

        if len(self.params) == 0:
            return prefix
        else:
            if (self.params == ["list"]) or (len(self.params) > 6):
                return f"{prefix}, t_symbol *s, int argc, t_atom *argv"
            else:
                types = []
                for i, t in enumerate(self.params):
                    types.append(self.parent.func_type_args[t] + str(i))
                type_str = ", ".join(types)
                return f"{prefix}, {type_str}"

    @property
    def class_addmethod(self):
        prefix = (
            f"class_addmethod({self.parent.name}_class, "
            f"(t_method){self.parent.name}_{self.name}, "
            f'gensym("{self.name}")'
        )

        if len(self.params) == 0:
            return f"{prefix}, 0)"
        else:
            if (self.params == ["list"]) or (len(self.params) > 6):
                return f"{prefix}, A_GIMME, 0)"
            else:
                types = []
                for t in self.params:
                    types.append(self.parent.mapping[t])
                type_str = ", ".join(types)
                return f"{prefix}, {type_str}, 0)"


# class Inlet(Object):
#     types = {
#         'bang': '&s_bang',
#         'float': '&s_float',
#         'symbol': '&s_symbol',
#         'pointer': '&s_pointer',
#         'list': '&s_list',
#         'signal': '&s_signal'
#     }
#     def __init__(self, parent, **kwargs):
#         super().__init__(parent, **kwargs)
#         # self.type = self.ns.type

#     @property
#     def typed_inlet_new(self):
#         assert 'bang' != self.name # doesn't exist for 'bang'
#         if self.name == 'pointer':
#             return 't_inlet *pointerinlet_new(t_object *owner, t_gpointer *gp)'


class Param(Object):
    c_types = {
        "atom": "t_atom",
        "float": "t_float",
        "symbol": "t_symbol",
        "int": "t_int",
        "signal": "t_signal",
        "sample": "t_sample",
    }

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.name = self.ns.name
        self.initial = self.ns.initial
        self.type = self.ns.type
        self.is_arg = self.ns.arg
        self.has_inlet = self.ns.inlet

    # def as_inlet(self):
    #     return Inlet(self.parent, vars(self.ns))

    @property
    def pd_type(self):
        return self.c_types[self.type]

    @property
    def struct_declaration(self):
        return f"{self.pd_type} {self.name}"


class Outlet(Object):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.name = self.ns.name
        self.type = self.ns.type


class External:
    mapping = {
        "float": "A_DEFFLOAT",
        "symbol": "A_DEFSYMBOL",
        "anything": "A_GIMME",
    }

    func_type_args = {
        "float": "t_floatarg f",
        "symbol": "t_symbol *s",
        "anything": "t_symbol *s, int argc, t_atom *argv",
    }

    def __init__(self, **kwargs):
        self.ns = SimpleNamespace(**kwargs)
        self.name = self.ns.name
        self.type = f"t_{self.name}"
        self.klass = f"{self.name}_class"
        self.meta = self.ns.meta
        self.help = self.ns.help
        self.alias = self.ns.alias if hasattr(self.ns, "alias") else None

    def __repr__(self):
        return f"<{self.__class__.__name__}: '{self.name}'>"

    @property
    def params(self):
        return [Param(self, **p) for p in self.ns.params]

    @property
    def args(self):
        return [p for p in self.params if p.is_arg]

    @property
    def inlets(self):
        return [p for p in self.params if p.has_inlet]

    @property
    def outlets(self):
        return [Outlet(self, **o) for o in self.ns.outlets]

    @property
    def type_methods(self):
        return [TypeMethod(self, **m) for m in self.ns.type_methods]

    @property
    def message_methods(self):
        return [MessagedMethod(self, **m) for m in self.ns.message_methods]

    @property
    def class_new_args(self):
        if len(self.args) == 0:
            return "void"
        elif 0 < len(self.args) <= 6:
            types = []
            for i, t in enumerate(self.args):
                types.append(self.func_type_args[t.type] + str(i))
            type_str = ", ".join(types)
            return type_str
        elif self.params == "anything" or len(self.args) > 6:
            return "t_symbol *s, int argc, t_atom *argv"
        else:
            raise Exception("cannot populate class_new_args")

    @property
    def class_type_signature(self):
        suffix = ", 0"
        if len(self.args) == 0:
            return suffix
        elif 0 < len(self.args) <= 6:
            types = [self.mapping[i.type] for i in self.args]
            return ", ".join(types) + suffix
        else:
            return "A_GIMME" + suffix

    @property
    def class_addcreator(self):
        return (
            f"class_addcreator((t_newmethod)"
            f'{self.name}_new, gensym("{self.alias}"), '
            f"{self.class_type_signature})"
        )


# ----------------------------------------------------------------------------
# MAIN CLASS


class PdProject:
    """main class to manage external projects and related files."""

    def __init__(self, spec_yml, target_dir="output"):
        self.spec_yml = Path(spec_yml)
        self.fullname = Path(spec_yml).stem
        self.name = self.fullname.strip("~")
        self.is_dsp = self.fullname.endswith("~")
        self.target_dir = Path(target_dir)
        self.project_path = self.target_dir / self.fullname

    def cmd(self, shell, *args, **kwds):
        os.system(shell.format(*args, **kwds))

    def generate(self):
        try:
            Path("output").mkdir(exist_ok=True)
            self.project_path.mkdir(exist_ok=True)
        except OSError:
            print(f"{self.project_path} already exists")
            return

        self.cmd(f"cp -rf resources/pd/Makefile.pdlibbuilder {self.project_path}")
        if self.is_dsp:
            self.render("pd-dsp-external.c.mako")
        else:
            self.render("pd-external.c.mako")
        self.render("pd-Makefile.mako", "Makefile")
        self.render("README.md.mako", "README.md")

    def render(self, template, outfile=None):
        with open(self.spec_yml) as f:
            yml = yaml.safe_load(f.read())
            ext_yml = yml["externals"][0]

        templ = Template(filename=os.path.join(TEMPLATE_DIR, template))
        external = External(**ext_yml)
        rendered = templ.render(e=external)
        if not outfile:
            outfile = self.fullname + ".c"
        target = self.project_path / outfile
        with open(target, "w") as f:
            f.write(rendered)
        print(target, "rendered")


# ----------------------------------------------------------------------------
# MAIN CLASS

if __name__ == "__main__":
    p = PdProject("counter.yml")
    p.generate()
