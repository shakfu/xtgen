/* Fake Max runtime api for tests/mx/graph_host.c; see fake_max.c. */
#ifndef XTGEN_TEST_FAKE_MAX_H
#define XTGEN_TEST_FAKE_MAX_H

#include "ext.h"

typedef void (*fake_perform64)(void *x, t_object *dsp64, double **ins, long numins,
                               double **outs, long numouts, long sampleframes, long flags,
                               void *userparam);

extern method fake_new, fake_free;
extern fake_perform64 fake_perform; /* set by the external's dsp64 */

method fake_find(const char *name); /* a method registered by class_addmethod */

#endif
