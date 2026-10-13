/* Minimal CLAP host for tests: links a generated plugin and exercises it.
 *
 * Usage: host <plugin-id> [pass | finite | gain G0 G1 | mod G0 G1]. Prints "ok"
 * and exits 0 on success. The mode sets the expected audio, with param 0 set to
 * its max at FRAMES / 2: pass (default) copies input to output; finite only
 * requires finite output (generators have no input port); gain expects input * G0
 * before the event and input * G1 from it on. mod is gain, but param 0 must be
 * modulatable and reaches its max by a CLAP_EVENT_PARAM_MOD, which leaves its
 * value unchanged.
 */

#include <clap/clap.h>

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(cond)                                                  \
    do {                                                             \
        if (!(cond)) {                                               \
            fprintf(stderr, "%s:%d: CHECK(%s)\n", __FILE__, __LINE__, #cond); \
            return 1;                                                \
        }                                                            \
    } while (0)

#define FRAMES 16
#define MAX_CH 8

extern const clap_plugin_entry_t clap_entry;

/* Event list holding at most one param event. */
static union {
    clap_event_header_t header;
    clap_event_param_value_t value;
    clap_event_param_mod_t mod;
} g_event;
static uint32_t g_n_events;

static uint32_t events_size(const clap_input_events_t *list)
{
    (void)list;
    return g_n_events;
}

static const clap_event_header_t *events_get(const clap_input_events_t *list, uint32_t i)
{
    (void)list;
    return i < g_n_events ? &g_event.header : NULL;
}

static const clap_input_events_t g_in_events = {NULL, events_size, events_get};

static bool out_try_push(const clap_output_events_t *list, const clap_event_header_t *ev)
{
    (void)list; (void)ev;
    return true;
}

static const clap_output_events_t g_out_events = {NULL, out_try_push};

static void set_event(uint32_t time, clap_id id, double value)
{
    memset(&g_event, 0, sizeof(g_event));
    g_event.header.size = sizeof(g_event.value);
    g_event.header.time = time;
    g_event.header.space_id = CLAP_CORE_EVENT_SPACE_ID;
    g_event.header.type = CLAP_EVENT_PARAM_VALUE;
    g_event.value.param_id = id;
    g_event.value.value = value;
    g_n_events = 1;
}

static void set_mod_event(uint32_t time, clap_id id, double amount)
{
    memset(&g_event, 0, sizeof(g_event));
    g_event.header.size = sizeof(g_event.mod);
    g_event.header.time = time;
    g_event.header.space_id = CLAP_CORE_EVENT_SPACE_ID;
    g_event.header.type = CLAP_EVENT_PARAM_MOD;
    g_event.mod.param_id = id;
    g_event.mod.note_id = -1;
    g_event.mod.port_index = -1;
    g_event.mod.channel = -1;
    g_event.mod.key = -1;
    g_event.mod.amount = amount;
    g_n_events = 1;
}

/* Memory streams; reads return one byte per call to test short reads. */
static char g_buf[4096];
static uint64_t g_len, g_pos;

static int64_t mem_write(const clap_ostream_t *s, const void *buf, uint64_t size)
{
    (void)s;
    if (g_len + size > sizeof(g_buf))
        return -1;
    memcpy(g_buf + g_len, buf, size);
    g_len += size;
    return (int64_t)size;
}

static int64_t mem_read(const clap_istream_t *s, void *buf, uint64_t size)
{
    (void)s;
    if (size == 0 || g_pos >= g_len)
        return 0;
    ((char *)buf)[0] = g_buf[g_pos++];
    return 1;
}

static const void *host_get_extension(const clap_host_t *h, const char *id)
{
    (void)h; (void)id;
    return NULL;
}

static void host_noop(const clap_host_t *h) { (void)h; }

static const clap_host_t g_host = {
    CLAP_VERSION_INIT, NULL, "test", "xtgen", "", "0",
    host_get_extension, host_noop, host_noop, host_noop,
};

int main(int argc, char **argv)
{
    CHECK(argc == 2 || argc == 3 || argc == 5);
    const char *mode = argc > 2 ? argv[2] : "pass";
    const bool mod = !strcmp(mode, "mod");
    const bool gain = mod || !strcmp(mode, "gain");
    CHECK(!strcmp(mode, "pass") || !strcmp(mode, "finite") || (gain && argc == 5));
    CHECK(clap_entry.init("."));
    const clap_plugin_factory_t *factory = clap_entry.get_factory(CLAP_PLUGIN_FACTORY_ID);
    CHECK(factory && factory->get_plugin_count(factory) == 1);
    CHECK(!strcmp(factory->get_plugin_descriptor(factory, 0)->id, argv[1]));
    CHECK(factory->create_plugin(factory, &g_host, "wrong.id") == NULL);

    const clap_plugin_t *plugin = factory->create_plugin(factory, &g_host, argv[1]);
    CHECK(plugin && plugin->init(plugin));
    const clap_plugin_params_t *params = plugin->get_extension(plugin, CLAP_EXT_PARAMS);
    const clap_plugin_state_t *state = plugin->get_extension(plugin, CLAP_EXT_STATE);
    const clap_plugin_audio_ports_t *ports = plugin->get_extension(plugin, CLAP_EXT_AUDIO_PORTS);
    CHECK(params && state && ports);

    /* Params start at their defaults. */
    uint32_t n_params = params->count(plugin);
    clap_param_info_t info0;
    for (uint32_t i = 0; i < n_params; i++) {
        clap_param_info_t info;
        double v;
        CHECK(params->get_info(plugin, i, &info));
        CHECK(info.min_value < info.max_value);
        CHECK(params->get_value(plugin, info.id, &v) && v == info.default_value);
        if (i == 0)
            info0 = info;
    }
    CHECK(!params->get_info(plugin, n_params, &info0) || n_params == 0);

    clap_audio_port_info_t port;
    uint32_t n_in_ports = ports->count(plugin, true);
    CHECK(n_in_ports <= 1 && ports->count(plugin, false) == 1);
    CHECK(!ports->get(plugin, n_in_ports, true, &port));
    CHECK(ports->get(plugin, 0, false, &port));
    uint32_t n_ch = port.channel_count;
    CHECK(n_ch >= 1 && n_ch <= MAX_CH);
    if (n_in_ports) {
        CHECK(ports->get(plugin, 0, true, &port));
        CHECK(port.channel_count == n_ch);
    }
    CHECK(n_in_ports == 1 || !strcmp(mode, "finite"));

    /* Process: pass-through audio; a param event mid-block is applied. */
    static float in_data[MAX_CH][FRAMES], out_data[MAX_CH][FRAMES];
    float *in_ptrs[MAX_CH], *out_ptrs[MAX_CH];
    for (uint32_t c = 0; c < n_ch; c++) {
        for (uint32_t i = 0; i < FRAMES; i++)
            in_data[c][i] = (float)(c * FRAMES + i);
        in_ptrs[c] = in_data[c];
        out_ptrs[c] = out_data[c];
    }
    clap_audio_buffer_t in_buf = {in_ptrs, NULL, n_ch, 0, 0};
    clap_audio_buffer_t out_buf = {out_ptrs, NULL, n_ch, 0, 0};
    clap_process_t proc = {
        -1, FRAMES, NULL, &in_buf, &out_buf, n_in_ports, 1, &g_in_events, &g_out_events,
    };
    if (mod) {
        CHECK(n_params > 0 && (info0.flags & CLAP_PARAM_IS_MODULATABLE));
        set_mod_event(FRAMES / 2, info0.id, info0.max_value - info0.default_value);
    } else if (n_params > 0) {
        set_event(FRAMES / 2, info0.id, info0.max_value);
    }

    CHECK(plugin->activate(plugin, 48000.0, 1, FRAMES));
    CHECK(plugin->start_processing(plugin));
    CHECK(plugin->process(plugin, &proc) == CLAP_PROCESS_CONTINUE);
    plugin->stop_processing(plugin);
    plugin->deactivate(plugin);
    for (uint32_t c = 0; c < n_ch; c++) {
        if (!strcmp(mode, "pass"))
            CHECK(!memcmp(in_data[c], out_data[c], sizeof(in_data[c])));
        for (uint32_t i = 0; i < FRAMES; i++) {
            CHECK(isfinite(out_data[c][i]));
            if (gain) {
                float g = (float)atof(argv[i < FRAMES / 2 || n_params == 0 ? 3 : 4]);
                CHECK(fabsf(out_data[c][i] - in_data[c][i] * g) <= 1e-6f * fabsf(in_data[c][i] * g));
            }
        }
    }

    if (n_params > 0) {
        /* Modulation is an offset; the value stays where it was. */
        const double set = mod ? info0.default_value : info0.max_value;
        double v;
        CHECK(params->get_value(plugin, info0.id, &v) && v == set);

        /* State round trip: save, change via flush, load restores. */
        CHECK(state->save(plugin, &(clap_ostream_t){NULL, mem_write}));
        set_event(0, info0.id, info0.min_value);
        params->flush(plugin, &g_in_events, &g_out_events);
        CHECK(params->get_value(plugin, info0.id, &v) && v == info0.min_value);
        g_pos = 0;
        CHECK(state->load(plugin, &(clap_istream_t){NULL, mem_read}));
        CHECK(params->get_value(plugin, info0.id, &v) && v == set);

        /* Truncated state is rejected. */
        g_pos = 0;
        g_len -= 1;
        CHECK(!state->load(plugin, &(clap_istream_t){NULL, mem_read}));
    }

    plugin->destroy(plugin);
    clap_entry.deinit();
    puts("ok");
    return 0;
}
