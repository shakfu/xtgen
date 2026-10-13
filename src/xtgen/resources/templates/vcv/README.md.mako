<% module = e.name[0].upper() + e.name[1:] %>\
# ${e.name}

${e.meta['desc']}

Author: ${e.meta['author']}

Repo: ${e.meta['repo']}


${'##'} Build

A [VCV Rack 2](https://vcvrack.com/manual/PluginDevelopmentTutorial) plugin with one module, `${module}`.

```sh
make RACK_DIR=/path/to/Rack-SDK
make RACK_DIR=/path/to/Rack-SDK install
```

`res/${module}.svg` is a blank panel; replace it with your design.


${'##'} Parameters
% for p in e.params:
- ${p.name} [${p.min}, ${p.max}] -- default: ${p.initial}${" (CV input)" if p.has_inlet else ""}
% endfor
% if e.dsp:


${'##'} DSP

`src/${e.dsp.prefix}.c` is compiled by gen-dsp from `${e.dsp.source}`. Edit the graph and
regenerate rather than editing the C file.

The graph is mono: it reads channel 0 of each input and writes one channel per output.
Audio is scaled from +-5 V to +-1 for the graph and back.
% endif


${'##'} Features:
% for feature in e.meta['features']:
- ${feature}
% endfor
