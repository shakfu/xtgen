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

typedef struct _${e.prefix} {
    t_pxobject ob;              // the object itself (t_pxobject in MSP instead of t_object)

    /* parameters */
    % for p in e.params:
    ${p.struct_declaration};    // ${p.desc}
    % endfor

    /* outlets */
    % for o in e.outlets:
    t_outlet *out_${o.name};
    % endfor

    double feedback;            // controls the reverb time, reverb tail becomes infinite when set to 1.0 (range 0.0 to 1.0)
    double lp_freq;             // controls the internal dampening filter's cutoff frequency. (range: 0.0 to sample_rate / 2)
} t_${e.prefix};


// method prototypes
void *${e.prefix}_new(t_symbol *s, long argc, t_atom *argv);
void ${e.prefix}_free(t_${e.prefix} *x);
void ${e.prefix}_assist(t_${e.prefix} *x, void *b, long m, long a, char *s);
void ${e.prefix}_bang(t_${e.prefix} *x);
void ${e.prefix}_anything(t_${e.prefix}* x, t_symbol* s, long argc, t_atom* argv);
void ${e.prefix}_dsp64(t_${e.prefix} *x, t_object *dsp64, short *count, double samplerate, long maxvectorsize, long flags);
void ${e.prefix}_perform64(t_${e.prefix} *x, t_object *dsp64, double **ins, long numins, double **outs, long numouts, long sampleframes, long flags, void *userparam);


// global class pointer variable
static t_class *${e.prefix}_class = NULL;


//-----------------------------------------------------------------------------------------------

void ext_main(void *r)
{
    // object initialization, note the use of dsp_free for the freemethod, which is required
    // unless you need to free allocated memory, in which case you should call dsp_free from
    // your custom free function.

    t_class *c = class_new("${e.namespace}.${e.name}~", (method)${e.prefix}_new, (method)${e.prefix}_free, (long)sizeof(t_${e.prefix}), 0L, A_GIMME, 0);

    class_addmethod(c, (method)${e.prefix}_anything, "anything", A_GIMME,   0);
    class_addmethod(c, (method)${e.prefix}_bang,     "bang",                0);
    class_addmethod(c, (method)${e.prefix}_dsp64,    "dsp64",    A_CANT,    0);
    class_addmethod(c, (method)${e.prefix}_assist,   "assist",   A_CANT,    0);

    class_dspinit(c);
    class_register(CLASS_BOX, c);
    ${e.prefix}_class = c;
}

void *${e.prefix}_new(t_symbol *s, long argc, t_atom *argv)
{
    t_${e.prefix} *x = (t_${e.prefix} *)object_alloc(${e.prefix}_class);

    if (x) {
        dsp_setup((t_pxobject *)x, N_CHANNELS);

        for (int i=0; i < N_CHANNELS; ++i) {
            post("signal outlet: %d", i);
            outlet_new(x, "signal");        // signal outlet (note "signal" rather than NULL)
        }
        
        x->rev = new daisysp::ReverbSc;
        x->feedback = 100.0;
        x->lp_freq = 0.5;
    }
    return (x);
}


void ${e.prefix}_free(t_${e.prefix} *x)
{
    delete x->rev;
    dsp_free((t_pxobject *)x);
}


void ${e.prefix}_assist(t_${e.prefix} *x, void *b, long m, long a, char *s)
{
    // FIXME: assign to inlets
    if (m == ASSIST_INLET) { //inlet
        sprintf(s, "I am inlet %ld", a);
    }
    else {  // outlet
        sprintf(s, "I am outlet %ld", a);
    }
}

void ${e.prefix}_bang(t_${e.prefix} *x)
{
    post("bang");
}

void ${e.prefix}_anything(t_${e.prefix}* x, t_symbol* s, long argc, t_atom* argv)
{
    if (s != gensym("") && argc > 0) {
        if (s == gensym("feedback")) {
            x->feedback = atom_getfloat(argv);

        }
        else if (s == gensym("lp_freq")) {
            x->lp_freq = atom_getfloat(argv);
        }
    }
}



void ${e.prefix}_dsp64(t_${e.prefix} *x, t_object *dsp64, short *count, double samplerate, long maxvectorsize, long flags)
{
    // post("sample rate: %f", samplerate);
    // post("maxvectorsize: %d", maxvectorsize);

    x->rev->Init(samplerate);

    object_method(dsp64, gensym("dsp_add64"), x, ${e.prefix}_perform64, 0, NULL);
}


void ${e.prefix}_perform64(t_${e.prefix} *x, t_object *dsp64, double **ins, long numins, double **outs, long numouts, long sampleframes, long flags, void *userparam)
{
    t_double *inL = ins[0];     // we get audio for each inlet of the object from the **ins argument
    t_double *inR = ins[1];     // we get audio for each inlet of the object from the **ins argument
    t_double *outL = outs[0];   // we get audio for each outlet of the object from the **outs argument
    t_double *outR = outs[1];   // we get audio for each outlet of the object from the **outs argument

    int n = sampleframes;       // n = 64

    while (n--) {
        *outL++ = *inL++;
        *outR++ = *inR++;
    }
}
