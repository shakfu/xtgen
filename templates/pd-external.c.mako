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

static t_class *${e.name}_class;


/*
 * ${e.name} class struct (data-space)
 * ---------------------------------------------------------------------------
 */

typedef struct _${e.name} {
    t_object x_obj;

    /* parameters */
    % for p in e.params:
    ${p.struct_declaration};
    % endfor

    /* outlets */
    % for o in e.outlets:
    t_outlet *out_${o.name};
    % endfor
} t_${e.name};


/*
 * ${e.name} class methods (operation-space)
 * ---------------------------------------------------------------------------
 */

// typed-methods
% for method in e.type_methods:
void ${e.name}_${method.type}(${method.args})
{
    post("${method.type} body");
}

% endfor

// message-methods
% for method in e.message_methods:
void ${e.name}_${method.name}(${method.args})
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

void *${e.name}_new(${e.class_new_args})
{
    t_${e.name} *x = (t_${e.name} *)pd_new(${e.name}_class);

    // initialize variables
    % for p in e.params:
    x->${p.name} = ${p.initial};
    % endfor

    // populate variables
    % if len(e.args) > 0:
    // switch stmt here
    % endif

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
    ${e.name}_class = class_new(gensym("${e.name}"),
                            (t_newmethod)${e.name}_new,
                            0, // destructor
                            sizeof(t_${e.name}),
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

    // set name of default help file
    class_sethelpsymbol(${e.name}_class, gensym("${e.help}"));
}

