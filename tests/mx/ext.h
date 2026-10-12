/* Minimal stand-in for the Max SDK headers, used to syntax-check generated
 * sources. Declares only the api the mx templates call. */
#ifndef XTGEN_TEST_EXT_H
#define XTGEN_TEST_EXT_H

#include <stdio.h>

typedef float t_float;
typedef long t_int;
typedef struct _symbol { const char *s_name; } t_symbol;
typedef struct _atom { long a_type; } t_atom;
typedef struct _object { void *o_messlist; } t_object;
typedef struct _pxobject { t_object z_ob; } t_pxobject;
typedef struct _class t_class;
typedef void *(*method)(void *, ...);

enum { A_GIMME = 8, A_CANT = 9 };
#define CLASS_BOX gensym("box")
#define ASSIST_INLET 1

t_class *class_new(const char *name, method mnew, method mfree, long size, method mmenu, short type, ...);
long class_addmethod(t_class *c, method m, const char *name, ...);
long class_register(t_symbol *name_space, t_class *c);
void class_dspinit(t_class *c);
void *object_alloc(t_class *c);
void *object_method(void *x, t_symbol *s, ...);
void *outlet_new(void *x, const char *s);
void post(const char *fmt, ...);
t_symbol *gensym(const char *s);
void dsp_setup(t_pxobject *x, long nsignals);
void dsp_free(t_pxobject *x);

#endif
