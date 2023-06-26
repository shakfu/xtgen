# ${e.name}

${e.meta['desc']}

Author: ${e.meta['author']}

Repo: ${e.meta['repo']}


\## Parameters
% for p in e.params:
- ${p.name} (${p.type}) -- default: ${p.initial}
% endfor


\## Features:
% for feature in e.meta['features']:
- ${feature}
% endfor

