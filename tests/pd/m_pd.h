/* Minimal stand-in for Pd's m_pd.h, used to syntax-check generated sources.
 * Declares only the api the pd templates call, with Pd's signatures. */
#ifndef XTGEN_TEST_M_PD_H
#define XTGEN_TEST_M_PD_H

#include <stddef.h>

typedef float t_float;
typedef float t_floatarg;
typedef float t_sample;
typedef long t_int;
typedef struct _symbol { const char *s_name; } t_symbol;
typedef struct _atom { int a_type; } t_atom;
typedef struct _gpointer t_gpointer;
typedef struct _class t_class;
typedef t_class *t_pd;
typedef struct _text { t_pd ob_pd; } t_object;
typedef struct _inlet t_inlet;
typedef struct _outlet t_outlet;
typedef struct _signal { int s_n; t_sample *s_vec; t_float s_sr; } t_signal;
typedef void (*t_method)(void);
typedef void *(*t_newmethod)(void);
typedef t_int *(*t_perfroutine)(t_int *w);

typedef enum { A_NULL, A_FLOAT, A_SYMBOL, A_POINTER, A_GIMME = 10, A_DEFFLOAT = 6,
               A_DEFSYMBOL = 7, A_CANT = 11 } t_atomtype;
#define CLASS_DEFAULT 0

extern t_symbol s_bang, s_float, s_symbol, s_list, s_anything, s_signal;

t_class *class_new(t_symbol *name, t_newmethod newmethod, t_method freemethod,
                   size_t size, int flags, t_atomtype arg1, ...);
void class_addcreator(t_newmethod newmethod, t_symbol *s, t_atomtype type1, ...);
void class_addmethod(t_class *c, t_method fn, t_symbol *sel, t_atomtype arg1, ...);
void class_addbang(t_class *c, t_method fn);
void class_addpointer(t_class *c, t_method fn);
void class_doaddfloat(t_class *c, t_method fn);
void class_addsymbol(t_class *c, t_method fn);
void class_addlist(t_class *c, t_method fn);
void class_addanything(t_class *c, t_method fn);
void class_sethelpsymbol(t_class *c, t_symbol *s);
void class_domainsignalin(t_class *c, int onset);
#define class_addbang(x, y) class_addbang((x), (t_method)(y))
#define class_addpointer(x, y) class_addpointer((x), (t_method)(y))
#define class_addfloat(x, y) class_doaddfloat((x), (t_method)(y))
#define class_addsymbol(x, y) class_addsymbol((x), (t_method)(y))
#define class_addlist(x, y) class_addlist((x), (t_method)(y))
#define class_addanything(x, y) class_addanything((x), (t_method)(y))
#define CLASS_MAINSIGNALIN(c, type, field) \
    class_domainsignalin(c, (int)offsetof(type, field))

t_pd *pd_new(t_class *cls);
t_symbol *gensym(const char *s);
t_outlet *outlet_new(t_object *owner, t_symbol *s);
t_inlet *inlet_new(t_object *owner, t_pd *dest, t_symbol *s1, t_symbol *s2);
t_inlet *floatinlet_new(t_object *owner, t_float *fp);
t_inlet *symbolinlet_new(t_object *owner, t_symbol **sp);
t_float atom_getfloatarg(int which, int argc, const t_atom *argv);
t_symbol *atom_getsymbolarg(int which, int argc, const t_atom *argv);
void dsp_add(t_perfroutine f, int n, ...);
void post(const char *fmt, ...);
void pd_error(const void *object, const char *fmt, ...);

#endif
