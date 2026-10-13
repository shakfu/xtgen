/* Fake Max runtime for tests: records what an external registers so a harness
 * can create the object and drive its dsp64 and perform64 methods. */

#include <stdarg.h>
#include <stdlib.h>
#include <string.h>

#include "ext.h"
#include "fake_max.h"

method fake_new, fake_free;
fake_perform64 fake_perform;
static long g_size;
static struct { const char *name; method fn; } g_methods[64];
static int g_n_methods;

t_class *class_new(const char *name, method mnew, method mfree, long size, method mmenu,
                   short type, ...)
{
    (void)name; (void)mmenu; (void)type;
    fake_new = mnew;
    fake_free = mfree;
    g_size = size;
    return (t_class *)&g_size;
}

long class_addmethod(t_class *c, method m, const char *name, ...)
{
    (void)c;
    g_methods[g_n_methods].name = name;
    g_methods[g_n_methods++].fn = m;
    return 0;
}

method fake_find(const char *name)
{
    for (int i = 0; i < g_n_methods; i++)
        if (!strcmp(g_methods[i].name, name))
            return g_methods[i].fn;
    return NULL;
}

long class_register(t_symbol *name_space, t_class *c) { (void)name_space; (void)c; return 0; }
long class_alias(t_class *c, t_symbol *aliasname) { (void)c; (void)aliasname; return 0; }
void class_dspinit(t_class *c) { (void)c; }
void *object_alloc(t_class *c) { (void)c; return calloc(1, (size_t)g_size); }
void *outlet_new(void *x, const char *s) { (void)x; (void)s; return &g_size; }
void post(const char *fmt, ...) { (void)fmt; }
void object_error(t_object *x, const char *fmt, ...) { (void)x; (void)fmt; }
void dsp_setup(t_pxobject *x, long nsignals) { (void)x; (void)nsignals; }
void dsp_free(t_pxobject *x) { (void)x; }

t_symbol *gensym(const char *s)
{
    static t_symbol syms[64];
    static int n;
    for (int i = 0; i < n; i++)
        if (!strcmp(syms[i].s_name, s))
            return &syms[i];
    syms[n].s_name = s;
    return &syms[n++];
}

/* Only dsp_add64 is called: (dsp64, "dsp_add64", x, perform, flags, userparam). */
void *object_method(void *x, t_symbol *s, ...)
{
    va_list ap;
    (void)x;
    va_start(ap, s);
    if (!strcmp(s->s_name, "dsp_add64")) {
        (void)va_arg(ap, void *);
        fake_perform = va_arg(ap, fake_perform64);
    }
    va_end(ap);
    return NULL;
}
