<%
from xtgen.models import c_string
desc = " ".join(str(e.meta['desc']).split())
d = e.dsp
n_in = d.n_inputs if d else e.n_channels
n_out = d.n_outputs if d else e.n_channels
%>\
/* ${e.name}.c

${desc}

Features:
% for feature in e.meta['features']:
- ${feature}
% endfor

Author: ${e.meta['author']}
Repo: ${e.meta['repo']}
% if d:

DSP: compiled by gen-dsp from ${d.source} into ${d.prefix}.c. Edit the graph and
regenerate rather than editing ${d.prefix}.c.
% endif

*/

#include <clap/clap.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
% if d:

#include "${d.prefix}.h"
% endif

#define N_IN_CHANNELS ${n_in}
#define N_OUT_CHANNELS ${n_out}

/*
 * ${e.name} descriptor
 * ---------------------------------------------------------------------------
 */

/* clap-wrapper derives the AU type from the first feature. */
static const char *${e.name}_features[] = {
% if n_in:
    CLAP_PLUGIN_FEATURE_AUDIO_EFFECT,
% else:
    CLAP_PLUGIN_FEATURE_INSTRUMENT, /* no audio input: a generator */
% endif
% if n_out == 1:
    CLAP_PLUGIN_FEATURE_MONO,
% elif n_out == 2:
    CLAP_PLUGIN_FEATURE_STEREO,
% endif
    NULL,
};

static const clap_plugin_descriptor_t ${e.name}_descriptor = {
    .clap_version = CLAP_VERSION_INIT,
    .id = ${c_string(e.namespace + "." + e.name)},
    .name = ${c_string(e.name)},
    .vendor = ${c_string(str(e.meta['author']))},
    .url = ${c_string(str(e.meta['repo']))},
    .manual_url = "",
    .support_url = "",
    .version = "0.1.0",
    .description = ${c_string(desc)},
    .features = ${e.name}_features,
};

/*
 * ${e.name} parameters
 * ---------------------------------------------------------------------------
 */

enum {
% for p in e.params:
    PARAM_${p.name.upper()},
% endfor
    PARAM_COUNT
};

typedef struct {
    const char *name;
    double min, max, initial;
} ${e.name}_param_spec_t;

static const ${e.name}_param_spec_t ${e.name}_param_specs[PARAM_COUNT + 1] = {
% for p in e.params:
    { ${c_string(p.name)}, ${repr(float(p.min))}, ${repr(float(p.max))}, ${repr(float(p.initial))} },
% endfor
    { NULL, 0, 0, 0 }, /* sentinel: keeps the array non-empty when PARAM_COUNT is 0 */
};

/* Compared at runtime instead of the enum, so PARAM_COUNT == 0 passes -Wtype-limits. */
static const uint32_t n_params = PARAM_COUNT;

/*
 * ${e.name} plugin struct
 * ---------------------------------------------------------------------------
 */

typedef struct {
    clap_plugin_t plugin;
    const clap_host_t *host;
    double sample_rate;
    /* Written on the audio thread (process/flush), read by get_value/save. */
    double params[PARAM_COUNT + 1];
% if d:
    ${d.state_type} *dsp; /* created by activate, used only on the audio thread */
% endif
} ${e.name}_t;

static ${e.name}_t *${e.name}_from(const clap_plugin_t *plugin)
{
    return (${e.name}_t *)plugin->plugin_data;
}

static void ${e.name}_handle_event(${e.name}_t *x, const clap_event_header_t *hdr)
{
    if (hdr->space_id != CLAP_CORE_EVENT_SPACE_ID)
        return;
    if (hdr->type == CLAP_EVENT_PARAM_VALUE) {
        const clap_event_param_value_t *ev = (const clap_event_param_value_t *)hdr;
        if (ev->param_id < n_params)
            x->params[ev->param_id] = ev->value;
    }
}

/*
 * ${e.name} audio ports extension
 * ---------------------------------------------------------------------------
 */

static uint32_t ${e.name}_audio_ports_count(const clap_plugin_t *plugin, bool is_input)
{
    (void)plugin;
    return is_input ? N_IN_CHANNELS > 0 : 1;
}

static bool ${e.name}_audio_ports_get(const clap_plugin_t *plugin, uint32_t index,
                                bool is_input, clap_audio_port_info_t *info)
{
    (void)plugin;
    if (index >= ${e.name}_audio_ports_count(plugin, is_input))
        return false;
    uint32_t n_ch = is_input ? N_IN_CHANNELS : N_OUT_CHANNELS;
    info->id = 0;
    snprintf(info->name, sizeof(info->name), "%s", is_input ? "in" : "out");
    info->flags = CLAP_AUDIO_PORT_IS_MAIN;
    info->channel_count = n_ch;
    info->port_type = n_ch == 1 ? CLAP_PORT_MONO : n_ch == 2 ? CLAP_PORT_STEREO : NULL;
    info->in_place_pair = CLAP_INVALID_ID;
    return true;
}

static const clap_plugin_audio_ports_t ${e.name}_audio_ports = {
    .count = ${e.name}_audio_ports_count,
    .get = ${e.name}_audio_ports_get,
};

/*
 * ${e.name} params extension
 * ---------------------------------------------------------------------------
 */

static uint32_t ${e.name}_params_count(const clap_plugin_t *plugin)
{
    (void)plugin;
    return PARAM_COUNT;
}

static bool ${e.name}_params_get_info(const clap_plugin_t *plugin, uint32_t index,
                                clap_param_info_t *info)
{
    (void)plugin;
    if (index >= n_params)
        return false;
    const ${e.name}_param_spec_t *spec = &${e.name}_param_specs[index];
    memset(info, 0, sizeof(*info));
    info->id = index;
    info->flags = CLAP_PARAM_IS_AUTOMATABLE;
    snprintf(info->name, sizeof(info->name), "%s", spec->name);
    info->min_value = spec->min;
    info->max_value = spec->max;
    info->default_value = spec->initial;
    return true;
}

static bool ${e.name}_params_get_value(const clap_plugin_t *plugin, clap_id id, double *value)
{
    if (id >= n_params)
        return false;
    *value = ${e.name}_from(plugin)->params[id];
    return true;
}

static bool ${e.name}_params_value_to_text(const clap_plugin_t *plugin, clap_id id,
                                     double value, char *out, uint32_t size)
{
    (void)plugin;
    if (id >= n_params)
        return false;
    snprintf(out, size, "%g", value);
    return true;
}

static bool ${e.name}_params_text_to_value(const clap_plugin_t *plugin, clap_id id,
                                     const char *text, double *value)
{
    (void)plugin;
    char *end;
    if (id >= n_params)
        return false;
    *value = strtod(text, &end);
    return end != text;
}

static void ${e.name}_params_flush(const clap_plugin_t *plugin,
                             const clap_input_events_t *in,
                             const clap_output_events_t *out)
{
    (void)out;
    ${e.name}_t *x = ${e.name}_from(plugin);
    uint32_t n = in->size(in);
    for (uint32_t i = 0; i < n; i++)
        ${e.name}_handle_event(x, in->get(in, i));
}

static const clap_plugin_params_t ${e.name}_params = {
    .count = ${e.name}_params_count,
    .get_info = ${e.name}_params_get_info,
    .get_value = ${e.name}_params_get_value,
    .value_to_text = ${e.name}_params_value_to_text,
    .text_to_value = ${e.name}_params_text_to_value,
    .flush = ${e.name}_params_flush,
};

/*
 * ${e.name} state extension
 *
 * Layout: uint32 param count, then that many doubles in host byte order.
 * Loading restores min(saved, PARAM_COUNT) values, so added params keep defaults.
 * ---------------------------------------------------------------------------
 */

static bool ${e.name}_write_all(const clap_ostream_t *stream, const void *buf, uint64_t size)
{
    const char *p = buf;
    while (size > 0) {
        int64_t n = stream->write(stream, p, size);
        if (n <= 0)
            return false;
        p += n;
        size -= (uint64_t)n;
    }
    return true;
}

static bool ${e.name}_read_all(const clap_istream_t *stream, void *buf, uint64_t size)
{
    char *p = buf;
    while (size > 0) {
        int64_t n = stream->read(stream, p, size);
        if (n <= 0)
            return false;
        p += n;
        size -= (uint64_t)n;
    }
    return true;
}

static bool ${e.name}_state_save(const clap_plugin_t *plugin, const clap_ostream_t *stream)
{
    ${e.name}_t *x = ${e.name}_from(plugin);
    uint32_t count = PARAM_COUNT;
    return ${e.name}_write_all(stream, &count, sizeof(count))
        && ${e.name}_write_all(stream, x->params, sizeof(double) * PARAM_COUNT);
}

static bool ${e.name}_state_load(const clap_plugin_t *plugin, const clap_istream_t *stream)
{
    ${e.name}_t *x = ${e.name}_from(plugin);
    double values[PARAM_COUNT + 1];
    uint32_t count;
    if (!${e.name}_read_all(stream, &count, sizeof(count)))
        return false;
    if (count > n_params)
        count = n_params;
    if (!${e.name}_read_all(stream, values, sizeof(double) * count))
        return false;
    for (uint32_t i = 0; i < count; i++) {
        const ${e.name}_param_spec_t *spec = &${e.name}_param_specs[i];
        double v = values[i];
        x->params[i] = v < spec->min ? spec->min : v > spec->max ? spec->max : v;
    }
    return true;
}

static const clap_plugin_state_t ${e.name}_state = {
    .save = ${e.name}_state_save,
    .load = ${e.name}_state_load,
};

/*
 * ${e.name} plugin methods
 * ---------------------------------------------------------------------------
 */

static bool ${e.name}_init(const clap_plugin_t *plugin)
{
    ${e.name}_t *x = ${e.name}_from(plugin);
    for (uint32_t i = 0; i < n_params; i++)
        x->params[i] = ${e.name}_param_specs[i].initial;
    return true;
}

% if d:
static void ${e.name}_deactivate(const clap_plugin_t *plugin)
{
    ${e.name}_t *x = ${e.name}_from(plugin);
    if (x->dsp)
        ${d.prefix}_destroy(x->dsp);
    x->dsp = NULL;
}

static void ${e.name}_destroy(const clap_plugin_t *plugin)
{
    ${e.name}_deactivate(plugin);
    free(${e.name}_from(plugin));
}

static bool ${e.name}_activate(const clap_plugin_t *plugin, double sample_rate,
                         uint32_t min_frames, uint32_t max_frames)
{
    (void)min_frames; (void)max_frames;
    ${e.name}_t *x = ${e.name}_from(plugin);
    x->sample_rate = sample_rate;
    x->dsp = ${d.prefix}_create((float)sample_rate);
    return x->dsp != NULL;
}

/* Called on the audio thread before rendering, so the dsp state is only touched there. */
static void ${e.name}_sync_params(${e.name}_t *x)
{
    for (uint32_t i = 0; i < n_params; i++)
        ${d.prefix}_set_param(x->dsp, (int)i, (float)x->params[i]);
}
% else:
static void ${e.name}_destroy(const clap_plugin_t *plugin)
{
    free(${e.name}_from(plugin));
}

static bool ${e.name}_activate(const clap_plugin_t *plugin, double sample_rate,
                         uint32_t min_frames, uint32_t max_frames)
{
    (void)min_frames; (void)max_frames;
    ${e.name}_from(plugin)->sample_rate = sample_rate;
    return true;
}

static void ${e.name}_deactivate(const clap_plugin_t *plugin) { (void)plugin; }
% endif

static bool ${e.name}_start_processing(const clap_plugin_t *plugin)
{
    (void)plugin;
    return true;
}

static void ${e.name}_stop_processing(const clap_plugin_t *plugin) { (void)plugin; }

% if d:
static void ${e.name}_reset(const clap_plugin_t *plugin)
{
    ${e.name}_t *x = ${e.name}_from(plugin);
    if (x->dsp)
        ${d.prefix}_reset(x->dsp); /* also resets graph params; process re-syncs them */
}
% else:
static void ${e.name}_reset(const clap_plugin_t *plugin) { (void)plugin; }
% endif

static clap_process_status ${e.name}_process(const clap_plugin_t *plugin,
                                       const clap_process_t *process)
{
    ${e.name}_t *x = ${e.name}_from(plugin);
    const uint32_t frames = process->frames_count;
    const uint32_t n_events = process->in_events->size(process->in_events);
    uint32_t ev_index = 0;
    uint32_t next_ev_frame = n_events > 0 ? 0 : frames;

% if d:
    if (!x->dsp || process->audio_outputs_count < 1
        || process->audio_outputs[0].channel_count < N_OUT_CHANNELS)
        return CLAP_PROCESS_ERROR;
    const clap_audio_buffer_t *out = &process->audio_outputs[0];
    float *outs[N_OUT_CHANNELS];
%   if n_in:
    if (process->audio_inputs_count < 1
        || process->audio_inputs[0].channel_count < N_IN_CHANNELS)
        return CLAP_PROCESS_ERROR;
    const clap_audio_buffer_t *in = &process->audio_inputs[0];
    float *ins[N_IN_CHANNELS];
%   endif
    ${e.name}_sync_params(x);
% else:
    if (process->audio_inputs_count < 1 || process->audio_outputs_count < 1)
        return CLAP_PROCESS_CONTINUE;
    const clap_audio_buffer_t *in = &process->audio_inputs[0];
    const clap_audio_buffer_t *out = &process->audio_outputs[0];
    uint32_t n_ch = in->channel_count < out->channel_count
        ? in->channel_count : out->channel_count;
% endif

    /* Apply each event at its sample offset, then render up to the next one. */
    for (uint32_t i = 0; i < frames;) {
        while (ev_index < n_events && next_ev_frame == i) {
            const clap_event_header_t *hdr =
                process->in_events->get(process->in_events, ev_index);
            if (hdr->time != i) {
                next_ev_frame = hdr->time;
                break;
            }
            ${e.name}_handle_event(x, hdr);
% if d:
            ${e.name}_sync_params(x);
% endif
            if (++ev_index == n_events) {
                next_ev_frame = frames;
                break;
            }
        }

% if d:
        if (next_ev_frame > i) {
%   if n_in:
            for (uint32_t ch = 0; ch < N_IN_CHANNELS; ch++)
                ins[ch] = in->data32[ch] + i;
%   endif
            for (uint32_t ch = 0; ch < N_OUT_CHANNELS; ch++)
                outs[ch] = out->data32[ch] + i;
            ${d.prefix}_perform(x->dsp, ${"ins" if n_in else "NULL"}, outs, (int)(next_ev_frame - i));
            i = next_ev_frame;
        }
% else:
        for (; i < next_ev_frame; i++) {
            /* TODO: DSP. Pass-through until implemented. */
            for (uint32_t ch = 0; ch < n_ch; ch++)
                out->data32[ch][i] = in->data32[ch][i];
        }
% endif
    }
    return CLAP_PROCESS_CONTINUE;
}

static const void *${e.name}_get_extension(const clap_plugin_t *plugin, const char *id)
{
    (void)plugin;
    if (!strcmp(id, CLAP_EXT_AUDIO_PORTS))
        return &${e.name}_audio_ports;
    if (!strcmp(id, CLAP_EXT_PARAMS))
        return &${e.name}_params;
    if (!strcmp(id, CLAP_EXT_STATE))
        return &${e.name}_state;
    return NULL;
}

static void ${e.name}_on_main_thread(const clap_plugin_t *plugin) { (void)plugin; }

/*
 * ${e.name} factory and entry functions
 *
 * ${e.name}_entry.cpp exports these as clap_entry for each plugin format.
 * ---------------------------------------------------------------------------
 */

static uint32_t ${e.name}_factory_count(const clap_plugin_factory_t *factory)
{
    (void)factory;
    return 1;
}

static const clap_plugin_descriptor_t *${e.name}_factory_descriptor(
    const clap_plugin_factory_t *factory, uint32_t index)
{
    (void)factory;
    return index == 0 ? &${e.name}_descriptor : NULL;
}

static const clap_plugin_t *${e.name}_factory_create(const clap_plugin_factory_t *factory,
                                               const clap_host_t *host,
                                               const char *plugin_id)
{
    (void)factory;
    if (!clap_version_is_compatible(host->clap_version)
        || strcmp(plugin_id, ${e.name}_descriptor.id))
        return NULL;

    ${e.name}_t *x = calloc(1, sizeof(*x));
    if (!x)
        return NULL;
    x->host = host;
    x->plugin.desc = &${e.name}_descriptor;
    x->plugin.plugin_data = x;
    x->plugin.init = ${e.name}_init;
    x->plugin.destroy = ${e.name}_destroy;
    x->plugin.activate = ${e.name}_activate;
    x->plugin.deactivate = ${e.name}_deactivate;
    x->plugin.start_processing = ${e.name}_start_processing;
    x->plugin.stop_processing = ${e.name}_stop_processing;
    x->plugin.reset = ${e.name}_reset;
    x->plugin.process = ${e.name}_process;
    x->plugin.get_extension = ${e.name}_get_extension;
    x->plugin.on_main_thread = ${e.name}_on_main_thread;
    return &x->plugin;
}

static const clap_plugin_factory_t ${e.name}_factory = {
    .get_plugin_count = ${e.name}_factory_count,
    .get_plugin_descriptor = ${e.name}_factory_descriptor,
    .create_plugin = ${e.name}_factory_create,
};

bool ${e.name}_entry_init(const char *plugin_path)
{
    (void)plugin_path;
    return true;
}

void ${e.name}_entry_deinit(void) {}

const void *${e.name}_entry_get_factory(const char *factory_id)
{
    return strcmp(factory_id, CLAP_PLUGIN_FACTORY_ID) ? NULL : &${e.name}_factory;
}
