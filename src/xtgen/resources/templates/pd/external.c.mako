/* ${e.name}.c

${e.meta['desc']}

Features:
% for feature in e.meta['features']:
- ${feature}
% endfor

Author: ${e.meta['author']}
Repo: ${e.meta['repo']}

*/

#include "m_pd.h"

/*
 * ${e.name} class object
 * ---------------------------------------------------------------------------
 */

static t_class *${e.c_name}_class;


/*
 * ${e.name} class struct (data-space)
 * ---------------------------------------------------------------------------
 */

typedef struct _${e.c_name} {
    t_object x_obj;

    /* parameters */
    % for p in e.params:
    ${p.struct_declaration};
    % endfor

    /* outlets */
    % for o in e.outlets:
    t_outlet *out_${o.name};
    % endfor
} ${e.type};


/*
 * ${e.name} class methods (operation-space)
 * ---------------------------------------------------------------------------
 */

// typed-methods
% for method in e.type_methods:
void ${e.c_name}_${method.type}(${method.args})
{
    post("${method.type} body");
}

% endfor

// message-methods
% for method in e.message_methods:
void ${e.c_name}_${method.name}(${method.args})
{
    % if method.doc:
    // ${method.doc}
    % endif
    post("${method.name} body");
}

% endfor


/*
 * ${e.name} class constructor
 * ---------------------------------------------------------------------------
 */

void *${e.c_name}_new(${e.class_new_args})
{
    ${e.type} *x = (${e.type} *)pd_new(${e.c_name}_class);

    // initialize variables
    % for p in e.params:
    x->${p.name} = ${p.c_initial};
    % endfor

    // populate variables from creation arguments
    % for stmt in e.class_new_assignments:
    ${stmt}
    % endfor

    // create inlets
    // inlet_new(&x->x_obj, &x->x_obj.ob_pd, gensym("list"), gensym("bound"));
    % for i in e.inlets:
    ${i.type}inlet_new(&x->x_obj, &x->${i.name});
    % endfor

    // initialize outlets
    % for o in e.outlets:
    x->out_${o.name} = outlet_new(&x->x_obj, &s_${o.type});
    % endfor

    return (void *)x;
}


/*
 * ${e.name} class setup
 * ---------------------------------------------------------------------------
 */

void ${e.name}_setup(void) 
{
    ${e.c_name}_class = class_new(gensym("${e.name}"),
                            (t_newmethod)${e.c_name}_new,
                            0, // destructor
                            sizeof(${e.type}),
                            CLASS_DEFAULT,
                            ${e.class_type_signature});

    // typed methods
    %for m in e.type_methods:
    ${m.class_addmethod};
    % endfor

    // message methods
    %for m in e.message_methods:
    ${m.class_addmethod};
    % endfor

    % if e.alias:
    // set the alias to external
    ${e.class_addcreator};
    % endif

    % if e.help:
    // set name of default help file
    class_sethelpsymbol(${e.c_name}_class, gensym("${e.help}"));
    % endif
}

