<%namespace name="mx" file="/mx/methods.mako"/>\
<%
pfx = e.prefix or e.name
d = e.dsp
S = d.state_type
P = d.prefix
%>\
/**
    @file
    ${e.namespace}.${e.name}~: ${e.meta['desc']}

    Features:
    % for feature in e.meta['features']:
    - ${feature}
    % endfor

    Author: ${e.meta['author']}
    Repo: ${e.meta['repo']}

    DSP: compiled by gen-dsp from ${d.source} into ${P}.c. Edit the graph and
    regenerate rather than editing ${P}.c. Add ${P}.c to the external's sources.
*/

#include <stdlib.h>

#include "ext.h"
#include "ext_obex.h"
#include "z_dsp.h"

#include "${P}.h"

#define N_IN ${d.n_inputs}
#define N_OUT ${d.n_outputs}
#define N_PARAMS ${len(e.params)}

typedef struct _${pfx} {
    t_pxobject ob;
    ${S} *dsp; // created by dsp64 at Max's sample rate
    double sr;
    double params[N_PARAMS + 1]; // kept here so a re-created dsp state gets them back
    long n; // frames per vector in buf
    float *buf; // N_IN + N_OUT float vectors: perform64 passes doubles

    /* outlets */
    % for o in e.outlets:
    void *out_${o.name};
    % endfor
} t_${pfx};


// method prototypes
void *${pfx}_new(t_symbol *s, long argc, t_atom *argv);
void ${pfx}_free(t_${pfx} *x);
void ${pfx}_assist(t_${pfx} *x, void *b, long m, long a, char *s);
void ${pfx}_dsp64(t_${pfx} *x, t_object *dsp64, short *count, double samplerate, long maxvectorsize, long flags);
void ${pfx}_perform64(t_${pfx} *x, t_object *dsp64, double **ins, long numins, double **outs, long numouts, long sampleframes, long flags, void *userparam);
% for p in e.params:
void ${pfx}_${p.name}(t_${pfx} *x, double f);
% endfor
${mx.prototypes(e, pfx)}

// global class pointer variable
static t_class *${pfx}_class = NULL;


//-----------------------------------------------------------------------------------------------

void ext_main(void *r)
{
    t_class *c = class_new("${e.namespace}.${e.name}~", (method)${pfx}_new, (method)${pfx}_free, (long)sizeof(t_${pfx}), 0L, A_GIMME, 0);

    class_addmethod(c, (method)${pfx}_dsp64,    "dsp64",    A_CANT,    0);
    class_addmethod(c, (method)${pfx}_assist,   "assist",   A_CANT,    0);
    % for p in e.params:
    class_addmethod(c, (method)${pfx}_${p.name}, "${p.name}", A_FLOAT, 0);
    % endfor
${mx.register(e, pfx)}
    class_dspinit(c);
    class_register(CLASS_BOX, c);
    ${pfx}_class = c;
}

void *${pfx}_new(t_symbol *s, long argc, t_atom *argv)
{
    t_${pfx} *x = (t_${pfx} *)object_alloc(${pfx}_class);

    if (x) {
        dsp_setup((t_pxobject *)x, N_IN);

        % for i, p in enumerate(e.params):
        x->params[${i}] = ${p.c_initial};
        % endfor

        // Max creates outlets right to left: message outlets go right of the signal outlets
        % for o in reversed(e.outlets):
        x->out_${o.name} = outlet_new(x, NULL);
        % endfor
        for (int i = 0; i < N_OUT; ++i) {
            outlet_new(x, "signal");
        }
    }
    return (x);
}


void ${pfx}_free(t_${pfx} *x)
{
    dsp_free((t_pxobject *)x);
    if (x->dsp)
        ${P}_destroy(x->dsp);
    free(x->buf);
}


void ${pfx}_assist(t_${pfx} *x, void *b, long m, long a, char *s)
{
    if (m == ASSIST_INLET) {
        if (a < N_IN)
            sprintf(s, "(signal) In %ld", a + 1);
        else
            sprintf(s, "messages");
    }
    else {
        if (a < N_OUT)
            sprintf(s, "(signal) Out %ld", a + 1);
        else
            sprintf(s, "outlet %ld", a + 1);
    }
}


/*
 * params: one method per graph param, "<name> <value>"
 */

% for i, p in enumerate(e.params):
<% lo, hi = repr(float(p.min)), repr(float(p.max)) %>\
void ${pfx}_${p.name}(t_${pfx} *x, double f)
{
    x->params[${i}] = f < ${lo} ? ${lo} : f > ${hi} ? ${hi} : f;
    if (x->dsp)
        ${P}_set_param(x->dsp, ${i}, (float)x->params[${i}]);
}

% endfor

${mx.bodies(e, pfx)}
void ${pfx}_dsp64(t_${pfx} *x, t_object *dsp64, short *count, double samplerate, long maxvectorsize, long flags)
{
    if (!x->dsp || samplerate != x->sr) {
        if (x->dsp)
            ${P}_destroy(x->dsp);
        x->dsp = ${P}_create((float)samplerate);
        if (!x->dsp) {
            object_error((t_object *)x, "out of memory");
            return;
        }
        x->sr = samplerate;
        for (int i = 0; i < N_PARAMS; i++)
            ${P}_set_param(x->dsp, i, (float)x->params[i]);
    }
    if (maxvectorsize > x->n) {
        float *buf = realloc(x->buf, sizeof(float) * (N_IN + N_OUT) * (size_t)maxvectorsize);
        if (!buf) {
            object_error((t_object *)x, "out of memory");
            return;
        }
        x->buf = buf;
        x->n = maxvectorsize;
    }
    object_method(dsp64, gensym("dsp_add64"), x, ${pfx}_perform64, 0, NULL);
}


void ${pfx}_perform64(t_${pfx} *x, t_object *dsp64, double **ins, long numins, double **outs, long numouts, long sampleframes, long flags, void *userparam)
{
    float *fout[N_OUT];
    if (sampleframes > x->n || numins < N_IN || numouts < N_OUT)
        return;
% if d.n_inputs:
    float *fin[N_IN];
    for (int i = 0; i < N_IN; i++) {
        fin[i] = x->buf + (size_t)i * x->n;
        for (long k = 0; k < sampleframes; k++)
            fin[i][k] = (float)ins[i][k];
    }
% endif
    for (int i = 0; i < N_OUT; i++)
        fout[i] = x->buf + (size_t)(N_IN + i) * x->n;

    ${P}_perform(x->dsp, ${"fin" if d.n_inputs else "NULL"}, fout, (int)sampleframes);

    for (int i = 0; i < N_OUT; i++) {
        for (long k = 0; k < sampleframes; k++)
            outs[i][k] = fout[i][k];
    }
}
