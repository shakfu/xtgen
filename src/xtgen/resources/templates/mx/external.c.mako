<% pfx = e.prefix or e.name %>\
/**
    @file
    ${e.namespace}.${e.name}: ${e.meta['desc']}

    Features:
    % for feature in e.meta['features']:
    - ${feature}
    % endfor

    Author: ${e.meta['author']}
    Repo: ${e.meta['repo']}
*/

#include "ext.h"
#include "ext_obex.h"

typedef struct _${pfx} {
    t_object ob;

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
void ${pfx}_bang(t_${pfx} *x);
void ${pfx}_anything(t_${pfx} *x, t_symbol *s, long argc, t_atom *argv);


// global class pointer variable
static t_class *${pfx}_class = NULL;


//-----------------------------------------------------------------------------------------------

void ext_main(void *r)
{
    t_class *c = class_new("${e.namespace}.${e.name}", (method)${pfx}_new, (method)${pfx}_free, (long)sizeof(t_${pfx}), 0L, A_GIMME, 0);

    class_addmethod(c, (method)${pfx}_anything, "anything", A_GIMME,   0);
    class_addmethod(c, (method)${pfx}_bang,     "bang",                0);
    class_addmethod(c, (method)${pfx}_assist,   "assist",   A_CANT,    0);

    class_register(CLASS_BOX, c);
    ${pfx}_class = c;
}

void *${pfx}_new(t_symbol *s, long argc, t_atom *argv)
{
    t_${pfx} *x = (t_${pfx} *)object_alloc(${pfx}_class);

    if (x) {
        % for p in e.params:
        x->${p.name} = ${p.c_initial};
        % endfor

        // Max creates outlets right to left
        % for o in reversed(e.outlets):
        x->out_${o.name} = outlet_new(x, NULL);
        % endfor
    }
    return (x);
}


void ${pfx}_free(t_${pfx} *x)
{
    ;
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

void ${pfx}_bang(t_${pfx} *x)
{
    post("bang");
}

void ${pfx}_anything(t_${pfx} *x, t_symbol *s, long argc, t_atom *argv)
{
    post("%s: %ld args", s->s_name, argc);
}
