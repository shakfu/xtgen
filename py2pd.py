#!/usr/bin/env python3

""" py2pd.py

A tool to generate skeleton puredata external files.

Has two intended purposes:

- [ ] generate skeleton puredata external code
- [ ] generate related puredata patch code

"""

import sys
import os
from pathlib import Path
from types import SimpleNamespace
import yaml

from mako.template import Template

TEMPLATE_DIR = os.path.join(os.getcwd(), 'templates')


c_type = lambda s: f't_{s}'
lookup_address = lambda s: f'&s_{s}'
lookup_routine = lambda s: f'gensym("{s}")'

def create_project(path):
    if os.path.exists(path):
        raise Exception(f'{path} already exists')
    else:
        os.mkdir(path)
        os.chdir(path)
        os.system('git init')
        os.system('git submodule add https://github.com/pure-data/pd-lib-builder.git')


class Object:
    def __init__(self, parent, **kwargs):
        self.parent = parent
        self.ns = SimpleNamespace(**kwargs)

    def __repr__(self):
        return f"<{self.__class__.__name__}: '{self.name}'>"


class Type:
    TYPES = ['bang', 'float', 'symbol', 'pointer', 'list', 'signal']

    def __init__(self, name):
        assert name in self.TYPES
        self.name = name

    def __str__(self):
        return self.name}

    def __repr__(self):
        return f"<{self.__class__.__name__}: '{self.name}'>"

    @property
    def c_type(self):
        return f't_{self.name}'

    @property
    def lookup_address(self):
        return f'&s_{self.name}'

    @property
    def lookup_routine(self):
        return f'gensym("{self.name}")'


class TypeMethod(Object):
    valid_types = ['bang', 'float', 'int', 'symbol', 'pointer', 'list', 'anything']

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.type = self.ns.type
        self.doc = self.ns.doc if hasattr(self.ns, 'doc') else ''
        assert (self.type in self.valid_types)

    @property
    def name(self):
        return self.type

    @property
    def args(self):
        if self.type == 'bang':
            return f'{self.parent.type} *x'

        elif self.type in ['float', 'int']:
            return f'{self.parent.type} *x, t_floatarg f'

        elif self.type == 'symbol':
            return f'{self.parent.type} *x, t_symbol *s'

        elif self.type == 'pointer':
            return f'{self.parent.type} *x, t_gpointer *pt'

        elif self.type in ['list', 'anything']:
            return f'{self.parent.type} *x, t_symbol *s, int argc, t_atom *argv'

        else:
            raise Exception(f"argument '{self.type}' not implemented")

    @property
    def class_addmethod(self):
        return f'class_add{self.type}({self.parent.klass}, {self.parent.name}_{self.type})'


class MessagedMethod(Object):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.name = self.ns.name
        self.doc = self.ns.doc if hasattr(self.ns, 'doc') else ''
        self.params = self.ns.params

    @property
    def args(self):
        prefix = f'{self.parent.type} *x'

        if len(self.params) == 0:
            return prefix
        else:
            if (self.params == ['list']) or (len(self.params) > 6):
                return f'{prefix}, t_symbol *s, int argc, t_atom *argv'
            else:
                types = []
                for i, t in enumerate(self.params):
                    types.append(self.parent.func_type_args[t]+str(i))
                type_str = ', '.join(types)
                return f'{prefix}, {type_str}'


    @property
    def class_addmethod(self):
        prefix = f'class_addmethod({self.parent.name}_class, (t_method){self.parent.name}_{self.name}, gensym("{self.name}")'

        if len(self.params) == 0:
            return f'{prefix}, 0)'
        else:
            if (self.params == ['list']) or (len(self.params) > 6):
                return f'{prefix}, A_GIMME, 0)'
            else:
                types = []
                for t in self.params:
                    types.append(self.parent.mapping[t])
                type_str = ', '.join(types)
                return f'{prefix}, {type_str}, 0)'


class Param(Object):
    c_types = {
        'atom': 't_atom',
        'float': 't_float',
        'symbol': 't_symbol',
        'int': 't_int',
        'signal': 't_signal',
        'sample': 't_sample',
    }

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.name = self.ns.name
        self.initial = self.ns.initial
        self.type = self.ns.type
        self.is_arg = self.ns.arg
        self.has_inlet = self.ns.inlet

    @property
    def pd_type(self):
        return self.c_types[self.type]

    @property
    def struct_declaration(self):
        return f"{self.pd_type} {self.name}"


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
#         self.type = self.ns.type




class External:
    mapping = {
        'float': 'A_DEFFLOAT',
        'symbol': 'A_DEFSYMBOL',
        'anything': 'A_GIMME',
    }

    func_type_args = {
        'float': 't_floatarg f',
        'symbol': 't_symbol *s',
        'anything': 't_symbol *s, int argc, t_atom *argv',
    }

    def __init__(self, **kwargs):
        self.ns = SimpleNamespace(**kwargs)
        self.name = self.ns.name
        self.type = f"t_{self.name}"
        self.klass = f"{self.name}_class"
        self.meta = self.ns.meta
        self.help = self.ns.help
        self.alias = self.ns.alias if hasattr(self.ns, 'alias') else None

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
    def outlets(self): pass

    @property
    def type_methods(self):
        return [TypeMethod(self, **m) for m in self.ns.type_methods]

    @property
    def message_methods(self):
        return [MessagedMethod(self, **m) for m in self.ns.message_methods]

    # @property
    # def type_inlets(self): pass

    # @property
    # def message_inlets(self): pass


    @property
    def class_new_args(self):
        if len(self.args) == 0:
            return 'void'
        elif 0 < len(self.args) <= 6:
            types = []
            for i, t in enumerate(self.args):
                types.append(self.func_type_args[t.type]+str(i))
            type_str = ', '.join(types)
            return type_str
        elif self.params == 'anything' or len(self.args) > 6:
            return 't_symbol *s, int argc, t_atom *argv'
        else:
            raise Exception('cannot populate class_new_args')

    @property
    def class_type_signature(self):
        suffix = ", 0"
        if len(self.args) == 0:
            return suffix
        elif 0 < len(self.args) <= 6:
            types = [self.mapping[i.type] for i in self.args]
            return ', '.join(types) + suffix
        else:
            return "A_GIMME" + suffix

    @property
    def class_addcreator(self):
        return (f'class_addcreator((t_newmethod)'
                f'{self.name}_new, gensym("{self.alias}"), '
                f'{self.class_type_signature})')

def render(external=None, template='template.c.mako'):
    if not external:
        with open('counter.yml') as f:
            yml = yaml.safe_load(f.read())
            ext_yml = yml['externals'][0]

    templ = Template(filename=f'{TEMPLATE_DIR}/{template}')
    external = External(**ext_yml)
    rendered = templ.render(e = external)
    outfile = ext_yml['name'] + '.c'
    with open(outfile,'w') as f:
        f.write(rendered)
    print(outfile, 'rendered')


if __name__ == '__main__':
    if 0:
        render()
    else:
        template='template.c.mako'
        with open('counter.yml') as f:
            yml = yaml.safe_load(f.read())
            ext_yml = yml['externals'][0]

        templ = Template(filename=f'{TEMPLATE_DIR}/{template}')
        e = External(**ext_yml)


