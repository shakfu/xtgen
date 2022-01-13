#include "m_pd.h"

static t_class *demo_class;

typedef struct _demo {
    t_object x_obj;
    t_glist *mycanvas;
} t_demo;

void demo_bang(t_demo *x) {
    t_atom av[4];
    SETFLOAT(av + 0, (t_float)300);
    SETFLOAT(av + 1, (t_float)10);
    SETSYMBOL(av + 2, gensym("r"));
    SETSYMBOL(av + 3, gensym("test"));
    pd_typedmess((t_pd *)x->mycanvas, gensym("obj"), 4, av);
}

void *demo_new(void) {
    t_demo *x = (t_demo *)pd_new(demo_class);
    x->mycanvas = canvas_getcurrent();
    return (void *)x;
}

void demo_setup(void) {
    demo_class = class_new(gensym("demo"), (t_newmethod)demo_new, 0,
                           sizeof(t_demo), CLASS_DEFAULT, 0);
    class_addbang(demo_class, demo_bang);
}