/* Runs a generated VCV Rack module headless, linked against the SDK's libRack.
 *
 * Usage: rack_host N_IN N_OUT [G0 G1]. Compile with -DMODEL=model<Module>.
 * Prints "ok" and exits 0 on success. Input i gets i + 1 volts. With G0 G1,
 * expects output i = input i * G0, then input i * G1 after param 0 is set to
 * G1; without them, only finite output.
 */

#include <rack.hpp>

#include <cmath>
#include <cstdio>
#include <cstdlib>

using namespace rack;

extern Model *MODEL;

#define CHECK(cond)                                                  \
    do {                                                             \
        if (!(cond)) {                                               \
            fprintf(stderr, "%s:%d: CHECK(%s)\n", __FILE__, __LINE__, #cond); \
            return 1;                                                \
        }                                                            \
    } while (0)

static int render(engine::Module *m, int n_in, int n_out, float gain, bool check_gain)
{
    engine::Module::ProcessArgs args;
    args.sampleRate = 48000.f;
    args.sampleTime = 1.f / args.sampleRate;
    args.frame = 0;
    for (int i = 0; i < n_in; i++)
        m->inputs[i].setVoltage((float)(i + 1));
    m->process(args);
    for (int i = 0; i < n_out; i++) {
        float v = m->outputs[i].getVoltage();
        CHECK(std::isfinite(v));
        if (check_gain)
            CHECK(std::fabs(v - (float)(i + 1) * gain) <= 1e-5f * std::fabs((float)(i + 1) * gain));
    }
    return 0;
}

int main(int argc, char **argv)
{
    CHECK(argc == 3 || argc == 5);
    int n_in = atoi(argv[1]), n_out = atoi(argv[2]);
    engine::Module *m = MODEL->createModule();
    CHECK(m && (int)m->inputs.size() == n_in && (int)m->outputs.size() == n_out);

    if (argc == 3) {
        CHECK(!render(m, n_in, n_out, 0.f, false));
    } else {
        CHECK(!m->params.empty());
        CHECK(!render(m, n_in, n_out, (float)atof(argv[3]), true));
        m->params[0].setValue((float)atof(argv[4]));
        CHECK(!render(m, n_in, n_out, (float)atof(argv[4]), true));
    }
    delete m;
    puts("ok");
    return 0;
}
