# ${e.name}

${e.meta['desc']}

Author: ${e.meta['author']}

Repo: ${e.meta['repo']}


${'##'} Parameters
% if e.dsp:

Set with a `<name> <value>` message to the left inlet. Values are clamped to the range.

% for p in e.params:
- ${p.name} [${p.min}, ${p.max}] -- default: ${p.initial}
% endfor


${'##'} DSP

`${e.dsp.prefix}.c` is compiled by gen-dsp from `${e.dsp.source}`. Add it to the
external's sources in your Max SDK build. Edit the graph and regenerate rather
than editing the C file.
% else:
% for p in e.params:
- ${p.name} (${p.type}) -- default: ${p.initial}
% endfor
% endif


${'##'} Features:
% for feature in e.meta['features']:
- ${feature}
% endfor

