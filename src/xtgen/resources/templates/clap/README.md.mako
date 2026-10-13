# ${e.name}

${e.meta['desc']}

Author: ${e.meta['author']}

Repo: ${e.meta['repo']}


${'##'} Build

A CLAP plugin. [clap-wrapper](https://github.com/free-audio/clap-wrapper) builds VST3 from it, plus AUv2 on macOS.

```sh
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --target ${e.name}_all
```

The first configure downloads CLAP, clap-wrapper and the VST3/AU SDKs.
Set the AUv2 codes in `CMakeLists.txt` before shipping an AU.


${'##'} Parameters
% for p in e.params:
- ${p.name} [${p.min}, ${p.max}] -- default: ${p.initial}${" (modulatable)" if p.has_inlet else ""}
% endfor
% if e.dsp:


${'##'} DSP

`${e.dsp.prefix}.c` is compiled by gen-dsp from `${e.dsp.source}`. Edit the graph and
regenerate rather than editing the C file.
% endif


${'##'} Features:
% for feature in e.meta['features']:
- ${feature}
% endfor
