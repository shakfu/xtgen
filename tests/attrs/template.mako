${e.name} -> ${e.meta.desc | trim}

% for p in e.params:
    ${p.name}
% endfor