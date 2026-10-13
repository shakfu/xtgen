/* ${e.name}.c

${e.meta['desc']}

Features:
% for feature in e.meta['features']:
- ${feature}
% endfor

Author: ${e.meta['author']}
Repo: ${e.meta['repo']}

*/

#include <stdlib.h>
#include <string.h>

#include "m_pd.h"

#define N_CHANNELS ${e.n_channels}

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
    t_float x_f; // main signal in
    int n; // frames per vector in buf
    t_sample *buf; // input copies: Pd may give an outlet the same vector as any inlet
    t_sample *ins[N_CHANNELS];
    t_sample *outs[N_CHANNELS];

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
 * ${e.name} dsp operaitions
 * ---------------------------------------------------------------------------
 */


t_int *${e.c_name}_perform(t_int *w)
{
    ${e.type} *x = (${e.type} *)(w[1]);
    int n = (int)(w[2]);

    // placeholder: copy each signal inlet to its signal outlet, through buf
    for (int c = 0; c < N_CHANNELS; c++)
        memcpy(x->buf + (size_t)c * n, x->ins[c], sizeof(t_sample) * n);
    for (int c = 0; c < N_CHANNELS; c++)
        memcpy(x->outs[c], x->buf + (size_t)c * n, sizeof(t_sample) * n);

    return (w + 3);
}


void ${e.c_name}_dsp(${e.type} *x, t_signal **sp)
{
    int n = sp[0]->s_n;
    if (n != x->n) {
        t_sample *buf = realloc(x->buf, sizeof(t_sample) * N_CHANNELS * (size_t)n);
        if (!buf) {
            pd_error(x, "${e.name}~: out of memory");
            return;
        }
        x->buf = buf;
        x->n = n;
    }
    // sp[0..N_CHANNELS-1]: signal inlets, then sp[N_CHANNELS..]: signal outlets
    for (int c = 0; c < N_CHANNELS; c++) {
        x->ins[c] = sp[c]->s_vec;
        x->outs[c] = sp[N_CHANNELS + c]->s_vec;
    }
    dsp_add(${e.c_name}_perform, 2, x, (t_int)n);
}


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

    // create inlets: signal inlets first, then param inlets
    for (int c = 1; c < N_CHANNELS; c++)
        inlet_new(&x->x_obj, &x->x_obj.ob_pd, &s_signal, &s_signal);
    % for i in e.inlets:
    ${i.type}inlet_new(&x->x_obj, &x->${i.name});
    % endfor

    // initialize outlets: signal outlets first, then message outlets
    for (int c = 0; c < N_CHANNELS; c++)
        outlet_new(&x->x_obj, &s_signal);
    % for o in e.outlets:
    x->out_${o.name} = outlet_new(&x->x_obj, &s_${o.type});
    % endfor

    return (void *)x;
}


void ${e.c_name}_free(${e.type} *x)
{
    free(x->buf);
}


/*
 * ${e.name} class setup
 * ---------------------------------------------------------------------------
 */

void ${e.name}_tilde_setup(void) 
{
    ${e.c_name}_class = class_new(gensym("${e.name}~"),
                            (t_newmethod)${e.c_name}_new,
                            (t_method)${e.c_name}_free,
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

    // set main signal in
    CLASS_MAINSIGNALIN(${e.c_name}_class, ${e.type}, x_f);

    /* Bind the DSP method, which is called when the DACs are turned on */
    class_addmethod(${e.c_name}_class, (t_method)${e.c_name}_dsp, gensym("dsp"), A_CANT, 0);

    % if e.alias:
    // set the alias to external
    ${e.class_addcreator};
    % endif

    % if e.help:
    // set name of default help file
    class_sethelpsymbol(${e.c_name}_class, gensym("${e.help}"));
    % endif
}

