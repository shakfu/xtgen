/* counter.c

An external which counts via a variable step and optionally between two limits.


Features:
- configurable integer counting
- can count in steps
- can count between a lower and upper bound

Author: gpt3
Repo: https://github.com/gpt3/counter.git

*/

#include "m_pd.h"

/*
 * counter class object
 * ---------------------------------------------------------------------------
 */

static t_class *counter_class;


/*
 * counter class struct (data-space)
 * ---------------------------------------------------------------------------
 */

typedef struct _counter {
    t_object x_obj;

    /* parameters */
    t_float step;
    t_float lower;
    t_float upper;

    /* outlets */
    t_outlet *out_f;
    t_outlet *out_b;
    t_outlet *out_s;
} t_counter;


/*
 * counter class methods (operation-space)
 * ---------------------------------------------------------------------------
 */

// typed-methods
void counter_bang(t_counter *x)
{
    post("bang body");
}

void counter_float(t_counter *x, t_floatarg f)
{
    post("float body");
}

void counter_symbol(t_counter *x, t_symbol *s)
{
    post("symbol body");
}

void counter_pointer(t_counter *x, t_gpointer *pt)
{
    post("pointer body");
}

void counter_list(t_counter *x, t_symbol *s, int argc, t_atom *argv)
{
    post("list body");
}

void counter_anything(t_counter *x, t_symbol *s, int argc, t_atom *argv)
{
    post("anything body");
}


// message-methods
void counter_reset(t_counter *x)
{
    // reset count to zero
    post("reset body");
}

void counter_bound(t_counter *x, t_floatarg f0, t_floatarg f1)
{
    // set (or reset) lower and uppwer boundary of counter
    post("bound body");
}

void counter_step(t_counter *x, t_floatarg f0)
{
    // set the counter increment per step
    post("step body");
}



/*
 * counter class constructor
 * ---------------------------------------------------------------------------
 */

void *counter_new(t_floatarg f0, t_floatarg f1, t_floatarg f2)
{
    t_counter *x = (t_counter *)pd_new(counter_class);

    // initialize variables
    x->step = 0.5;
    x->lower = 0.0;
    x->upper = 1.0;

    // populate variables
    // switch stmt here

    // create inlets
    // inlet_new(&x->x_obj, &x->x_obj.ob_pd, gensym("list"), gensym("bound"));
    floatinlet_new(&x->x_obj, &x->step);

    // initialize outlets
    x->out_f = outlet_new(&x->x_obj, &s_float);
    x->out_b = outlet_new(&x->x_obj, &s_bang);
    x->out_s = outlet_new(&x->x_obj, &s_symbol);

    return (void *)x;
}


/*
 * counter class setup
 * ---------------------------------------------------------------------------
 */

void counter_setup(void) 
{
    counter_class = class_new(gensym("counter"),
                            (t_newmethod)counter_new,
                            0, // destructor
                            sizeof(t_counter),
                            CLASS_DEFAULT,
                            A_DEFFLOAT, A_DEFFLOAT, A_DEFFLOAT, 0);

    // typed methods
    class_addbang(counter_class, counter_bang);
    class_addfloat(counter_class, counter_float);
    class_addsymbol(counter_class, counter_symbol);
    class_addpointer(counter_class, counter_pointer);
    class_addlist(counter_class, counter_list);
    class_addanything(counter_class, counter_anything);

    // message methods
    class_addmethod(counter_class, (t_method)counter_reset, gensym("reset"), 0);
    class_addmethod(counter_class, (t_method)counter_bound, gensym("bound"), A_DEFFLOAT, A_DEFFLOAT, 0);
    class_addmethod(counter_class, (t_method)counter_step, gensym("step"), A_DEFFLOAT, 0);


    // set name of default help file
    class_sethelpsymbol(counter_class, gensym("help-counter"));
}

