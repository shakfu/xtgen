/* Drives a generated Max graph external through tests/mx/fake_max.c.
 *
 * Usage: graph_host N_IN N_OUT [PARAM G0 G1]. Prints "ok" and exits 0 on success.
 * Inputs and outputs share buffers, as Max may pass them. With PARAM, expects
 * output = input * G0, then input * G1 after the message "PARAM G1"; without
 * it, only finite output.
 */

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "ext.h"
#include "fake_max.h"

#define CHECK(cond)                                                  \
    do {                                                             \
        if (!(cond)) {                                               \
            fprintf(stderr, "%s:%d: CHECK(%s)\n", __FILE__, __LINE__, #cond); \
            return 1;                                                \
        }                                                            \
    } while (0)

#define FRAMES 64
#define MAX_CH 8

void ext_main(void *r);

static double g_buf[MAX_CH][FRAMES], g_src[MAX_CH][FRAMES];
static double *g_ptrs[MAX_CH];

/* Fill the shared buffers with a ramp per channel, then run one perform64. */
static void render(void *x, long n_in, long n_out)
{
    for (long c = 0; c < MAX_CH; c++) {
        for (long i = 0; i < FRAMES; i++)
            g_src[c][i] = g_buf[c][i] = (double)(c * FRAMES + i + 1);
        g_ptrs[c] = g_buf[c];
    }
    fake_perform(x, NULL, g_ptrs, n_in, g_ptrs, n_out, FRAMES, 0, NULL);
}

static int check(long n_out, double gain, int finite_only)
{
    for (long c = 0; c < n_out; c++) {
        for (long i = 0; i < FRAMES; i++) {
            CHECK(isfinite(g_buf[c][i]));
            if (!finite_only)
                CHECK(fabs(g_buf[c][i] - g_src[c][i] * gain) <= 1e-6 * fabs(g_src[c][i] * gain));
        }
    }
    return 0;
}

int main(int argc, char **argv)
{
    CHECK(argc == 3 || argc == 6);
    long n_in = atol(argv[1]), n_out = atol(argv[2]);
    CHECK(n_out >= 1 && n_in <= MAX_CH && n_out <= MAX_CH);

    ext_main(NULL);
    CHECK(fake_new && fake_free && fake_find("dsp64"));
    void *x = ((void *(*)(t_symbol *, long, t_atom *))fake_new)(NULL, 0, NULL);
    CHECK(x);
    ((void (*)(void *, t_object *, short *, double, long, long))fake_find("dsp64"))(
        x, NULL, NULL, 48000.0, FRAMES, 0);
    CHECK(fake_perform);

    if (argc == 3) {
        render(x, n_in, n_out);
        CHECK(!check(n_out, 0, 1));
    } else {
        method set = fake_find(argv[3]);
        CHECK(set);
        render(x, n_in, n_out);
        CHECK(!check(n_out, atof(argv[4]), 0));
        ((void (*)(void *, double))set)(x, atof(argv[5]));
        render(x, n_in, n_out);
        CHECK(!check(n_out, atof(argv[5]), 0));
    }

    ((void (*)(void *))fake_free)(x);
    free(x);
    puts("ok");
    return 0;
}
