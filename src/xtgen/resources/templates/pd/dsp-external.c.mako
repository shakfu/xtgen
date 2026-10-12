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

static t_class *${e.name}_tilde_class;


/*
 * ${e.name} class struct (data-space)
 * ---------------------------------------------------------------------------
 */

typedef struct _${e.name}_tilde {
    t_object x_obj;
    t_float x_f; // main signal in
    t_outlet *x_out; // main signal out

    /* parameters */
    % for p in e.params:
    ${p.struct_declaration};
    % endfor

    /* outlets */
    % for o in e.outlets:
    t_outlet *out_${o.name};
    % endfor
} t_${e.name}_tilde;


/*
 * ${e.name} class methods (operation-space)
 * ---------------------------------------------------------------------------
 */

// typed-methods
% for method in e.type_methods:
void ${e.name}_tilde_${method.type}(${method.args})
{
    post("${method.type} body");
}

% endfor

// message-methods
% for method in e.message_methods:
void ${e.name}_tilde_${method.name}(${method.args})
{
    % if method.doc:
    // ${method.doc}
    % endif
    post("${method.name} body");
}

% endfor

/*
 * ${e.name} dsp operaitions
 * ---------------------------------------------------------------------------
 */


t_int *${e.name}_tilde_perform(t_int *w)
{
    // w[1] is the object (t_${e.name}_tilde *), unused by the placeholder body
    t_sample *in  = (t_sample *)(w[2]);
    t_sample *out = (t_sample *)(w[3]);
    int n = (int)(w[4]);

    // placeholder: copy the main signal inlet to the signal outlet
    while (n--) *out++ = *in++;

    return (w + 5);
}


void ${e.name}_tilde_dsp(t_${e.name}_tilde *x, t_signal **sp)
{
    // sp[0]: main signal inlet, sp[1]: signal outlet
    dsp_add(${e.name}_tilde_perform, 4, x,
            sp[0]->s_vec, sp[1]->s_vec, (t_int)sp[0]->s_n);
}


/*
 * ${e.name} class constructor
 * ---------------------------------------------------------------------------
 */

void *${e.name}_tilde_new(${e.class_new_args})
{
    t_${e.name}_tilde *x = (t_${e.name}_tilde *)pd_new(${e.name}_tilde_class);

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
    x->x_out = outlet_new(&x->x_obj, &s_signal);
    % for o in e.outlets:
    x->out_${o.name} = outlet_new(&x->x_obj, &s_${o.type});
    % endfor

    return (void *)x;
}





/*
 * ${e.name} class setup
 * ---------------------------------------------------------------------------
 */

void ${e.name}_tilde_setup(void) 
{
    ${e.name}_tilde_class = class_new(gensym("${e.name}~"),
                            (t_newmethod)${e.name}_tilde_new,
                            0, // destructor
                            sizeof(t_${e.name}_tilde),
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

    // set main signal in
    CLASS_MAINSIGNALIN(${e.name}_tilde_class, t_${e.name}_tilde, x_f);

    /* Bind the DSP method, which is called when the DACs are turned on */
    class_addmethod(${e.name}_tilde_class, (t_method)${e.name}_tilde_dsp, gensym("dsp"), 0);

    % if e.alias:
    // set the alias to external
    ${e.class_addcreator};
    % endif

    % if e.help:
    // set name of default help file
    class_sethelpsymbol(${e.name}_tilde_class, gensym("${e.help}"));
    % endif
}

