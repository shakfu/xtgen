## Max method code shared by the mx templates: the spec's type_methods and
## message_methods. Max passes A_FLOAT arguments as double.
<%!
from xtgen.generators import TypeMapper

# Max selector -> (C parameters after the object, class_addmethod arg types)
TYPE_METHODS = {
    "bang": ("", "0"),
    "float": (", double f", "A_FLOAT, 0"),
    "symbol": (", t_symbol *s", "A_SYM, 0"),
    "list": (", t_symbol *s, long argc, t_atom *argv", "A_GIMME, 0"),
    "anything": (", t_symbol *s, long argc, t_atom *argv", "A_GIMME, 0"),
}


def message_signature(params):
    """Return (C parameters after the object, class_addmethod arg types) for a message method."""
    if TypeMapper.needs_gimme(params):
        return TYPE_METHODS["anything"]
    c_args = {"float": "double f%d", "symbol": "t_symbol *s%d"}
    a_types = {"float": "A_FLOAT", "symbol": "A_SYM"}
    args = "".join(", " + c_args[t] % i for i, t in enumerate(params))
    return args, ", ".join([a_types[t] for t in params] + ["0"])


def declared_types(e):
    return {m.type for m in e.type_methods}
%>

<%def name="prototypes(e, pfx)">\
% for m in e.type_methods:
void ${pfx}_${m.type}(t_${pfx} *x${TYPE_METHODS[m.type][0]});
% endfor
% for m in e.message_methods:
void ${pfx}_${m.name}(t_${pfx} *x${message_signature(m.params)[0]});
% endfor
</%def>

<%def name="register(e, pfx)">\
% for m in e.type_methods:
    class_addmethod(c, (method)${pfx}_${m.type}, "${m.type}", ${TYPE_METHODS[m.type][1]});
% endfor
% for m in e.message_methods:
    class_addmethod(c, (method)${pfx}_${m.name}, "${m.name}", ${message_signature(m.params)[1]});
% endfor
% if e.alias and e.alias != e.name:
    class_alias(c, gensym("${e.alias}"));
% endif
</%def>

<%def name="bodies(e, pfx)">\
% for m in e.type_methods:
void ${pfx}_${m.type}(t_${pfx} *x${TYPE_METHODS[m.type][0]})
{
    % if m.doc:
    // ${m.doc}
    % endif
    post("${m.type} body");
}

% endfor
% for m in e.message_methods:
void ${pfx}_${m.name}(t_${pfx} *x${message_signature(m.params)[0]})
{
    % if m.doc:
    // ${m.doc}
    % endif
    post("${m.name} body");
}

% endfor
</%def>
