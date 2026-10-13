<%
d = e.dsp
c = e.c_name
S = d.state_type
P = d.prefix
%>\
/* ${e.name}~.c

${e.meta['desc']}

Features:
% for feature in e.meta['features']:
- ${feature}
% endfor

Author: ${e.meta['author']}
Repo: ${e.meta['repo']}

DSP: compiled by gen-dsp from ${d.source} into ${P}.c. Edit the graph and
regenerate rather than editing ${P}.c.

*/

#include <stdlib.h>
#include <string.h>

#include "m_pd.h"
#include "${P}.h"

#if defined(PD_FLOATSIZE) && PD_FLOATSIZE == 64
#error "gen-dsp graphs process 32-bit floats; build against single-precision Pd"
#endif

#define N_IN ${d.n_inputs}
#define N_OUT ${d.n_outputs}
#define N_PARAMS ${len(e.params)}

static t_class *${c}_class;

typedef struct _${c} {
    t_object x_obj;
% if d.n_inputs:
    t_float x_f; // main signal inlet scalar
% endif
    ${S} *dsp; // created by the dsp method at Pd's sample rate
    t_float sr;
    t_float params[N_PARAMS + 1]; // kept here so a re-created dsp state gets them back
% if d.n_inputs:
    int n;
    t_sample *buf; // input copies: Pd may give an inlet and an outlet the same vector
    t_sample *ins[N_IN];
% endif
    t_sample *outs[N_OUT];

    /* message outlets, right of the signal outlets */
% for o in e.outlets:
    t_outlet *out_${o.name};
% endfor
} t_${c};


/*
 * ${e.name}~ params: one method per graph param, "<name> <value>"
 * ---------------------------------------------------------------------------
 */

% for i, p in enumerate(e.params):
static void ${c}_${p.name}(t_${c} *x, t_floatarg f)
{
<% lo, hi = repr(float(p.min)), repr(float(p.max)) %>\
    x->params[${i}] = f < ${lo} ? ${lo} : f > ${hi} ? ${hi} : f;
    if (x->dsp)
        ${P}_set_param(x->dsp, ${i}, x->params[${i}]);
}

% endfor

% if e.type_methods or e.message_methods:
/*
 * ${e.name}~ methods (operation-space)
 * ---------------------------------------------------------------------------
 */

% for method in e.type_methods:
void ${c}_${method.type}(${method.args})
{
    post("${method.type} body");
}

% endfor
% for method in e.message_methods:
void ${c}_${method.name}(${method.args})
{
    % if method.doc:
    // ${method.doc}
    % endif
    post("${method.name} body");
}

% endfor
% endif
/*
 * ${e.name}~ dsp
 * ---------------------------------------------------------------------------
 */

static t_int *${c}_perform(t_int *w)
{
    t_${c} *x = (t_${c} *)(w[1]);
    int n = (int)(w[2]);
% if d.n_inputs:
    float *ins[N_IN];
    for (int i = 0; i < N_IN; i++) {
        ins[i] = x->buf + (size_t)i * n;
        memcpy(ins[i], x->ins[i], sizeof(t_sample) * n);
    }
    ${P}_perform(x->dsp, ins, x->outs, n);
% else:
    ${P}_perform(x->dsp, NULL, x->outs, n);
% endif
    return (w + 3);
}

static void ${c}_dsp(t_${c} *x, t_signal **sp)
{
    int n = sp[0]->s_n;
    t_float sr = sp[0]->s_sr;

    if (!x->dsp || sr != x->sr) {
        if (x->dsp)
            ${P}_destroy(x->dsp);
        x->dsp = ${P}_create(sr);
        if (!x->dsp) {
            pd_error(x, "${e.name}~: out of memory");
            return;
        }
        x->sr = sr;
        for (int i = 0; i < N_PARAMS; i++)
            ${P}_set_param(x->dsp, i, x->params[i]);
    }
% if d.n_inputs:
    if (n != x->n) {
        t_sample *buf = realloc(x->buf, sizeof(t_sample) * N_IN * (size_t)n);
        if (!buf) {
            pd_error(x, "${e.name}~: out of memory");
            return;
        }
        x->buf = buf;
        x->n = n;
    }
    // sp[0..N_IN-1]: signal inlets, then sp[N_IN..]: signal outlets
    for (int i = 0; i < N_IN; i++)
        x->ins[i] = sp[i]->s_vec;
% endif
    for (int i = 0; i < N_OUT; i++)
        x->outs[i] = sp[N_IN + i]->s_vec;
    dsp_add(${c}_perform, 2, x, (t_int)n);
}


/*
 * ${e.name}~ constructor and destructor
 * ---------------------------------------------------------------------------
 */

static void *${c}_new(void)
{
    t_${c} *x = (t_${c} *)pd_new(${c}_class);

% for i, p in enumerate(e.params):
    x->params[${i}] = ${p.c_initial};
% endfor
    for (int i = 1; i < N_IN; i++)
        inlet_new(&x->x_obj, &x->x_obj.ob_pd, &s_signal, &s_signal);
    for (int i = 0; i < N_OUT; i++)
        outlet_new(&x->x_obj, &s_signal);
% for o in e.outlets:
    x->out_${o.name} = outlet_new(&x->x_obj, &s_${o.type});
% endfor
    return (void *)x;
}

static void ${c}_free(t_${c} *x)
{
    if (x->dsp)
        ${P}_destroy(x->dsp);
% if d.n_inputs:
    free(x->buf);
% endif
}


/*
 * ${e.name}~ class setup
 * ---------------------------------------------------------------------------
 */

void ${e.name}_tilde_setup(void)
{
    ${c}_class = class_new(gensym("${e.name}~"),
                            (t_newmethod)${c}_new,
                            (t_method)${c}_free,
                            sizeof(t_${c}),
                            CLASS_DEFAULT,
                            0);

% if d.n_inputs:
    CLASS_MAINSIGNALIN(${c}_class, t_${c}, x_f);
% endif
    class_addmethod(${c}_class, (t_method)${c}_dsp, gensym("dsp"), A_CANT, 0);
% for p in e.params:
    class_addmethod(${c}_class, (t_method)${c}_${p.name}, gensym("${p.name}"), A_FLOAT, 0);
% endfor
% for m in e.type_methods:
    ${m.class_addmethod};
% endfor
% for m in e.message_methods:
    ${m.class_addmethod};
% endfor
% if e.class_addcreator:

    // set the alias to external
    ${e.class_addcreator};
% endif
% if e.help:

    // set name of default help file
    class_sethelpsymbol(${c}_class, gensym("${e.help}"));
% endif
}
