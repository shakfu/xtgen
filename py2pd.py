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

class TypedMethod(Object):
    valid_types = ['bang', 'float', 'int', 'symbol', 'pointer', 'list', 'anything']

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.type = self.ns.type
        assert (self.type in self.valid_types)

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
        self.params = self.ns.params

    @property
    def args(self):
        return 'typed-args'

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
        'signal': 't_signale',
        'sample': 't_sample',
    }

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.name = self.ns.name
        self.initial = self.ns.initial

    # @property
    # def name(self):
    #     return self.ns.name

    @property
    def pd_type(self):
        return self.c_types[self.ns.type]

    @property
    def struct_declaration(self):
        return f"{self.pd_type} {self.name}"

class External:
    mapping = {
        'float': 'A_DEFFLOAT',
        'symbol': 'A_DEFSYMBOL',
        'anything': 'A_GIMME',
    }

    constructer_args = {
        'A_DEFFLOAT': 't_floatarg f',
        'A_DEFSYMBOL': 't_symbol *s',
        'A_GIMME': 't_symbol *s, int argc, t_atom *argv',
    }

    def __init__(self, **kwargs):
        self.ns = SimpleNamespace(**kwargs)
        self.name = self.ns.name
        self.type = f"t_{self.name}"
        self.klass = f"{self.name}_class"
        self.meta = self.ns.meta
        self.help = self.ns.help

    @property
    def parameters(self):
        return [Param(self, **p) for p in self.ns.params]

    @property
    def args(self):
        return [Param(self, **p) for p in self.ns.params if p['arg']]

    @property
    def typed_methods(self):
        return [TypedMethod(self, **m) for m in self.ns.type_methods]

    @property
    def message_methods(self):
        return [MessagedMethod(self, **m) for m in self.ns.message_methods]

def render(external=None, template='template.c.mako', outfile='out.c'):
    if not external:
        with open('external.yml') as f:
            yml = yaml.safe_load(f.read())
            ext_yml = yml['externals'][0]

    templ = Template(filename=f'{TEMPLATE_DIR}/{template}')
    rendered = templ.render(e = External(**ext_yml))
    with open(outfile,'w') as f:
        f.write(rendered)
    print(outfile, 'rendered')


if __name__ == '__main__':
    render()

