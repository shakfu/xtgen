/* counter.c

An external which counts via a variable step and optionally between two limits.


Features:
- integer counting
- can count in steps
- can count between a lower and upper bound

Author: gpt3
Repo: https://github.com/gpt3/counter.git

*/

#include "m_pd.h"
#include "g_canvas.h"


#define GET_OBJ(val) (t_pd *)gensym(val)->s_thing
#define UNUSED(x) (void)(x) // to suppress warnings: warning: unused parameter


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

    t_glist *mycanvas;


    /* parameters */
    t_float step;
    t_float lower;
    t_float upper;

    /* outlets */
    t_outlet *out_f;

    /* TODO: additional outlets */
    t_outlet *out_b;
    t_outlet *out_s;
    t_outlet *out_l;
    t_outlet *out_m;
} t_counter;



/*
 * counter class methods (operation-space)
 * ---------------------------------------------------------------------------
 */

// typed-methods
void counter_bang(t_counter *x)
{
    post("x->step: %f", x->step);
    post("x->lower: %f", x->lower);
    post("x->upper: %f", x->upper);

    outlet_float(x->out_f, 10.0);
    outlet_bang(x->out_b);
    outlet_symbol(x->out_s, gensym("hello"));

    int argc = 2;
    t_atom argv[argc];
    SETFLOAT(argv, (t_float)2.5);
    SETFLOAT(argv+1, (t_float)4.5);

    // outlet_list
    outlet_list(x->out_l, &s_list, argc, argv);

    // outlet_message
    outlet_symbol(x->out_m, gensym("msg"));

    // outlet_anything

    // other stuff
    // t_atom av2[1];
    // SETFLOAT(av2, (t_float)1);
    // pd_typedmess((t_pd *)gensym("pd")->s_thing, gensym("dsp"), 1, av2);

    //pd_typedmess((t_pd *)gensym("bob")->s_thing, gensym("float"), 1, av2);

    // pd_typedmess(GET_OBJ("bob"), gensym("float"), 1, av2);

    // t_atom av[6];
    // SETSYMBOL(av+0, gensym("list"));
    // SETFLOAT(av+1, (t_float)0.9);
    // SETFLOAT(av+2, (t_float)0.9);
    // SETFLOAT(av+3, (t_float)0.9);
    // SETFLOAT(av+4, (t_float)0.9);
    // SETFLOAT(av+5, (t_float)0.9);
    // pd_typedmess(GET_OBJ("array1"), gensym("list"), 6, av);

    // pd_vmess(GET_OBJ("pd"), gensym("dsp"), "i", 1); // WORKING
    // pd_vmess(t_pd *x, t_symbol *s, const char *fmt, ...);
    // pd_vmess(GET_OBJ("array1"), gensym("list"), "sfffff", "list", 0.9, 0.9, 0.9, 0.9, 0.9);

    // t_atom av[7];
    // SETSYMBOL(av+0, gensym("list"));
    // SETFLOAT(av+1, (t_float)0.9);
    // SETFLOAT(av+2, (t_float)0.9);
    // SETFLOAT(av+3, (t_float)0.9);
    // SETFLOAT(av+4, (t_float)0.9);
    // SETFLOAT(av+5, (t_float)0.9);
    // SETFLOAT(av+6, (t_float)0.9);
    // pd_forwardmess(GET_OBJ("array1"), 7, av);

    // t_atom av[6];
    // SETFLOAT(av+0, (t_float)0.9);
    // SETFLOAT(av+1, (t_float)0.9);
    // SETFLOAT(av+2, (t_float)0.9);
    // SETFLOAT(av+3, (t_float)0.9);
    // SETFLOAT(av+4, (t_float)0.9);
    // SETFLOAT(av+5, (t_float)0.9);
    // pd_list(GET_OBJ("array1"), gensym("list"), 6, av);

    // pd_symbol(GET_OBJ("mysym"), gensym("helloworld"));

    // t_atom av[1];
    // SETSYMBOL(av+0, gensym("NICE"));
    // pd_list(GET_OBJ("mysym"), gensym("set"), 1, av);
    pd_symbol(GET_OBJ("mysym"), gensym("GOOD"));
    pd_float(GET_OBJ("bob"), 15.2);
    //sys_vgui("expr 8.2 + 6\n");
    // sys_gui("expr 8.2 + 6\n");
    
    // t_glist *mycanvas = canvas_getcurrent();
    // t_atom av[4];
    // SETFLOAT(av+0, (t_float)300);
    // SETFLOAT(av+1, (t_float)10);
    // SETSYMBOL(av+2, gensym("r"));
    // SETSYMBOL(av+3, gensym("test"));
    // pd_typedmess((t_pd *)mycanvas, gensym("obj"), 4, av);

    t_atom av[4];
    SETFLOAT(av+0, (t_float)300);
    SETFLOAT(av+1, (t_float)10);
    SETSYMBOL(av+2, gensym("r"));
    SETSYMBOL(av+3, gensym("test"));
    pd_typedmess((t_pd *)x->mycanvas, gensym("obj"), 4, av);

}


// message-methods
void counter_reset(t_counter *x)
{
    // reset count to zero
    post("reset body");
    UNUSED(x);
}

void counter_bound(t_counter *x, t_floatarg f0, t_floatarg f1)
{
    // set (or reset) lower and uppwer boundary of counter
    post("bound body");
    UNUSED(x);
    UNUSED(f0);
    UNUSED(f1);
}

void counter_step(t_counter *x, t_floatarg f0)
{
    // set the counter increment per step
    post("step body");
    UNUSED(x);
    UNUSED(f0);
}



/*
 * counter class constructor
 * ---------------------------------------------------------------------------
 */

void *counter_new(t_floatarg f0, t_floatarg f1, t_floatarg f2)
{
    t_counter *x = (t_counter *)pd_new(counter_class);

    postfloat(f0);
    postfloat(f1);
    postfloat(f2);

    // initialize variables
    x->step =  (f0 == 0) ? 0.1 : f0;
    x->lower = (f1 == 0) ? 0.2 : f1;
    x->upper = (f2 == 0) ? 0.3 : f2;

    postfloat(x->step);
    postfloat(x->lower);
    postfloat(x->upper);
 
    post("step: %f", x->step);
    post("lower: %f", x->lower);
    post("upper: %f", x->upper);

    x->mycanvas = canvas_getcurrent();




    // populate variables
    // switch stmt here

    // create inlets
    inlet_new(&x->x_obj, &x->x_obj.ob_pd, gensym("list"), gensym("bound"));
    // inlet_new(&x->x_obj, &x->x_obj.ob_pd, gensym("list"), gensym("bound"));
    // floatinlet_new(&x->x_obj, &x->step);
    floatinlet_new(&x->x_obj, &x->step);
    floatinlet_new(&x->x_obj, &x->lower);

    // initialize outlets
    x->out_f = outlet_new(&x->x_obj, &s_float);
    // x->b_out = outlet_new(&x->x_obj, &s_bang);
    x->out_b = outlet_new(&x->x_obj, &s_bang);
    x->out_s = outlet_new(&x->x_obj, &s_symbol);
    x->out_l = outlet_new(&x->x_obj, &s_list);
    // x->out_l = outlet_new(&x->x_obj, &s_float);
    x->out_m = outlet_new(&x->x_obj, 0);

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
                            A_DEFFLOAT, A_DEFFLOAT, A_DEFFLOAT,
                            0);

    // typed methods
    class_addbang(counter_class, counter_bang);

    // message methods
    class_addmethod(counter_class, (t_method)counter_reset, gensym("reset"), 0);
    class_addmethod(counter_class, (t_method)counter_bound, gensym("bound"), A_DEFFLOAT, A_DEFFLOAT, 0);
    class_addmethod(counter_class, (t_method)counter_step, gensym("step"), A_DEFFLOAT, 0);

    // alias
    class_addcreator((t_newmethod)counter_new, gensym("cntr"), A_DEFFLOAT, A_DEFFLOAT, A_DEFFLOAT, 0);

    // set name of default help file
    class_sethelpsymbol(counter_class, gensym("help-counter"));
}

