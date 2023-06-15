/**
    @file
    dsp.osc~: mdsp sine for Max
*/
#include "oscillator.h"
#include <cstdlib>

#include "ext.h"
#include "ext_obex.h"
#include "z_dsp.h"


enum {
    // FREQ is assigned to default left inlet
    AMP = 1, 
    PULSE_WIDTH,
    PHASE,
    MAX_INLET_INDEX // -> maximum number of inlets (0-based)
};


// struct to represent the object's state
typedef struct _mdsp {
    t_pxobject ob;              // the object itself (t_pxobject in MSP instead of t_object)
    daisysp::Oscillator* osc;   // daisy osc object
    double freq;                // Changes the frequency of the Oscillator, and recalculates phase increment.
    double amp;                 // Sets the amplitude of the waveform.
    int waveform;               // Sets the waveform to be synthesized by the Process() function.
    double pulse_width;         // Sets the pulse width for WAVE_SQUARE and WAVE_POLYBLEP_SQUARE (range 0 - 1)
    double phase;               // Adds a value 0.0-1.0 (mapped to 0.0-TWO_PI) to the current phase. Useful for PM and "FM" synthesis.
    long m_in;                  // space for the inlet number used by all the proxies
    void *inlets[MAX_INLET_INDEX];
    // t_outlet *outlet; 
} t_mdsp;


// method prototypes
void *mdsp_new(t_symbol *s, long argc, t_atom *argv);
void mdsp_free(t_mdsp *x);
void mdsp_assist(t_mdsp *x, void *b, long m, long a, char *s);
void mdsp_bang(t_mdsp *x);
void mdsp_anything(t_mdsp* x, t_symbol* s, long argc, t_atom* argv);
void mdsp_float(t_mdsp *x, double f);
void mdsp_int(t_mdsp *x, long i);
void mdsp_dsp64(t_mdsp *x, t_object *dsp64, short *count, double samplerate, long maxvectorsize, long flags);
void mdsp_perform64(t_mdsp *x, t_object *dsp64, double **ins, long numins, double **outs, long numouts, long sampleframes, long flags, void *userparam);


// global class pointer variable
static t_class *mdsp_class = NULL;


//-----------------------------------------------------------------------------------------------

void ext_main(void *r)
{
    // object initialization, note the use of dsp_free for the freemethod, which is required
    // unless you need to free allocated memory, in which case you should call dsp_free from
    // your custom free function.

    t_class *c = class_new("dsp.osc~", (method)mdsp_new, (method)mdsp_free, (long)sizeof(t_mdsp), 0L, A_GIMME, 0);

    class_addmethod(c, (method)mdsp_float,    "float",    A_FLOAT,   0);
    class_addmethod(c, (method)mdsp_int,      "int",      A_DEFLONG, 0);    
    class_addmethod(c, (method)mdsp_anything, "anything", A_GIMME,   0);
    class_addmethod(c, (method)mdsp_bang,     "bang",                0);
    class_addmethod(c, (method)mdsp_dsp64,    "dsp64",    A_CANT,    0);
    class_addmethod(c, (method)mdsp_assist,   "assist",   A_CANT,    0);

    class_dspinit(c);
    class_register(CLASS_BOX, c);
    mdsp_class = c;
}

void *mdsp_new(t_symbol *s, long argc, t_atom *argv)
{
    t_mdsp *x = (t_mdsp *)object_alloc(mdsp_class);

    if (x) {
        dsp_setup((t_pxobject *)x, 1);  // MSP inlets: arg is # of signal inlets and is REQUIRED!
        // use 0 if you don't need signal inlets

        // x->outlet = bangout(x);      // optional outlet to bang out at end of cycle
        outlet_new(x, "signal");        // signal outlet (note "signal" rather than NULL)
        

        for(int i = (MAX_INLET_INDEX - 1); i > 0; i--) {
            x->inlets[i] = proxy_new((t_object *)x, i, &x->m_in);
        }

        x->osc = new daisysp::Oscillator;
        x->freq = 100.0;
        x->amp = 0.5;
        x->waveform = daisysp::Oscillator::WAVE_SIN;
        x->pulse_width = 0.5;
        x->phase = 0.0;        
    }
    return (x);
}


void mdsp_free(t_mdsp *x)
{
    delete x->osc;
    dsp_free((t_pxobject *)x);
    for(int i = (MAX_INLET_INDEX - 1); i > 0; i--) {
        object_free(x->inlets[i]);
    }

}


void mdsp_assist(t_mdsp *x, void *b, long m, long a, char *s)
{
    // FIXME: assign to inlets
    if (m == ASSIST_INLET) { //inlet
        sprintf(s, "I am inlet %ld", a);
    }
    else {  // outlet
        sprintf(s, "I am outlet %ld", a);
    }
}

void mdsp_bang(t_mdsp *x)
{
    post("bang");
}

void mdsp_anything(t_mdsp* x, t_symbol* s, long argc, t_atom* argv)
{

    if (s != gensym("")) {
        post("symbol: %s", s->s_name);
    }
}


void mdsp_float(t_mdsp *x, double f)
{
    switch (proxy_getinlet((t_object *)x)) {
        case 0:
            x->freq = f;
            break;
        case 1:
            x->amp = f;
            break;
        case 2:
            x->pulse_width = f;
            break;
        case 3:
            x->phase = f;
            break;
    }
}

void mdsp_int(t_mdsp *x, long i)
{
    // post("long: %d", i);
    x->osc->SetWaveform(i);
}

void mdsp_dsp64(t_mdsp *x, t_object *dsp64, short *count, double samplerate, long maxvectorsize, long flags)
{
    post("sample rate: %f", samplerate);
    post("maxvectorsize: %d", maxvectorsize);

    x->osc->Init(samplerate);
    x->osc->Reset();

    object_method(dsp64, gensym("dsp_add64"), x, mdsp_perform64, 0, NULL);
}


void mdsp_perform64(t_mdsp *x, t_object *dsp64, double **ins, long numins, double **outs, long numouts, long sampleframes, long flags, void *userparam)
{
    t_double *inL = ins[0];     // we get audio for each inlet of the object from the **ins argument
    t_double *outL = outs[0];   // we get audio for each outlet of the object from the **outs argument
    int n = sampleframes;       // n = 64
    x->osc->SetFreq(x->freq);
    x->osc->SetAmp(x->amp);
    x->osc->SetPw(x->pulse_width);
    x->osc->PhaseAdd(x->phase);

    while (n--) {
        *outL++ = x->osc->Process();
        // if (x->osc->IsEOC()) {
        //     outlet_bang(x->outlet);
        // }
    }
}
