<% pfx = e.prefix or e.name; declared = {m.type for m in e.type_methods} %>\
<%namespace name="mx" file="/mx/methods.mako"/>\
/**
    @file
    ${e.namespace}.${e.name}~: ${e.meta['desc']}

    Features:
    % for feature in e.meta['features']:
    - ${feature}
    % endfor

    Author: ${e.meta['author']}
    Repo: ${e.meta['repo']}
*/

#include "ext.h"
#include "ext_obex.h"
#include "z_dsp.h"

#define N_CHANNELS ${e.n_channels}

typedef struct _${pfx} {
    t_pxobject ob;              // the object itself (t_pxobject in MSP instead of t_object)

    /* parameters */
    % for p in e.params:
    ${p.struct_declaration};    // ${p.desc}
    % endfor

    /* outlets */
    % for o in e.outlets:
    void *out_${o.name};
    % endfor
} t_${pfx};


// method prototypes
void *${pfx}_new(t_symbol *s, long argc, t_atom *argv);
void ${pfx}_free(t_${pfx} *x);
void ${pfx}_assist(t_${pfx} *x, void *b, long m, long a, char *s);
% if "bang" not in declared:
void ${pfx}_bang(t_${pfx} *x);
% endif
% if "anything" not in declared:
void ${pfx}_anything(t_${pfx} *x, t_symbol *s, long argc, t_atom *argv);
% endif
${mx.prototypes(e, pfx)}
void ${pfx}_dsp64(t_${pfx} *x, t_object *dsp64, short *count, double samplerate, long maxvectorsize, long flags);
void ${pfx}_perform64(t_${pfx} *x, t_object *dsp64, double **ins, long numins, double **outs, long numouts, long sampleframes, long flags, void *userparam);


// global class pointer variable
static t_class *${pfx}_class = NULL;


//-----------------------------------------------------------------------------------------------

void ext_main(void *r)
{
    t_class *c = class_new("${e.namespace}.${e.name}~", (method)${pfx}_new, (method)${pfx}_free, (long)sizeof(t_${pfx}), 0L, A_GIMME, 0);

% if "anything" not in declared:
    class_addmethod(c, (method)${pfx}_anything, "anything", A_GIMME,   0);
% endif
% if "bang" not in declared:
    class_addmethod(c, (method)${pfx}_bang,     "bang",                0);
% endif
    class_addmethod(c, (method)${pfx}_dsp64,    "dsp64",    A_CANT,    0);
    class_addmethod(c, (method)${pfx}_assist,   "assist",   A_CANT,    0);
${mx.register(e, pfx)}
    class_dspinit(c);
    class_register(CLASS_BOX, c);
    ${pfx}_class = c;
}

void *${pfx}_new(t_symbol *s, long argc, t_atom *argv)
{
    t_${pfx} *x = (t_${pfx} *)object_alloc(${pfx}_class);

    if (x) {
        dsp_setup((t_pxobject *)x, N_CHANNELS);

        % for p in e.params:
        x->${p.name} = ${p.c_initial};
        % endfor

        // Max creates outlets right to left: message outlets go right of the signal outlets
        % for o in reversed(e.outlets):
        x->out_${o.name} = outlet_new(x, NULL);
        % endfor
        for (int i = 0; i < N_CHANNELS; ++i) {
            outlet_new(x, "signal");
        }
    }
    return (x);
}


void ${pfx}_free(t_${pfx} *x)
{
    dsp_free((t_pxobject *)x);
}


void ${pfx}_assist(t_${pfx} *x, void *b, long m, long a, char *s)
{
    // FIXME: assign to inlets
    if (m == ASSIST_INLET) { //inlet
        sprintf(s, "I am inlet %ld", a);
    }
    else {  // outlet
        sprintf(s, "I am outlet %ld", a);
    }
}

% if "bang" not in declared:
void ${pfx}_bang(t_${pfx} *x)
{
    post("bang");
}

% endif
% if "anything" not in declared:
void ${pfx}_anything(t_${pfx} *x, t_symbol *s, long argc, t_atom *argv)
{
    post("%s: %ld args", s->s_name, argc);
}

% endif
${mx.bodies(e, pfx)}


void ${pfx}_dsp64(t_${pfx} *x, t_object *dsp64, short *count, double samplerate, long maxvectorsize, long flags)
{
    object_method(dsp64, gensym("dsp_add64"), x, ${pfx}_perform64, 0, NULL);
}


void ${pfx}_perform64(t_${pfx} *x, t_object *dsp64, double **ins, long numins, double **outs, long numouts, long sampleframes, long flags, void *userparam)
{
    // pass each input channel through to its output
    for (long ch = 0; ch < numins && ch < numouts; ++ch) {
        for (long i = 0; i < sampleframes; ++i) {
            outs[ch][i] = ins[ch][i];
        }
    }
}
