# https://dev.to/taqkarim/extending-simplenamespace-for-nested-dictionaries-58e8

import yaml
from mako.template import Template


class RecursiveNamespace:
    @staticmethod
    def map_entry(entry):
        if isinstance(entry, dict):
            return RecursiveNamespace(**entry)

        return entry

    def __init__(self, **kwargs):
        for key, val in kwargs.items():
            if type(val) == dict:
                setattr(self, key, RecursiveNamespace(**val))
            elif type(val) == list:
                setattr(self, key, list(map(self.map_entry, val)))
            else:  # this is the only addition
                setattr(self, key, val)


with open("./osc~.yml") as f:
    yml = yaml.safe_load(f.read())
    external = yml["externals"][0]

templ = Template(filename="./ext.mako")
rendered = templ.render(e=RecursiveNamespace(**external))
print(rendered)
