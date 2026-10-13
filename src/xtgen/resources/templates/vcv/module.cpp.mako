<%
from xtgen.models import c_string
module = e.name[0].upper() + e.name[1:]
d = e.dsp
n_in = d.n_inputs if d else e.n_channels
n_out = d.n_outputs if d else e.n_channels
up = lambda s: s.upper()
def value(p):
    """C++ expression for a param's value: the knob, plus CV for a modulated param."""
    knob = f"params[{up(p.name)}_PARAM].getValue()"
    if not p.has_inlet:
        return knob
    # 10 V of CV spans the full parameter range.
    return (f"clamp({knob} + inputs[{up(p.name)}_CV_INPUT].getVoltage() / 10.f * {float(p.max - p.min)!r}f,\n"
            f"                {float(p.min)!r}f, {float(p.max)!r}f)")
# Layout: one row per param (knob, CV input) then per channel (in, out).
# Columns of 7 rows; each column pair is 4 HP wide.
rows = [("param", p) for p in e.params] + [("audio", i) for i in range(1, max(n_in, n_out) + 1)]
def pos(r):
    """Return mm coordinates (left x, right x, y) of row r as C++ literals."""
    pair, row = divmod(r, 7)
    x = 7.62 + 20.32 * pair
    return f"{x:.2f}", f"{x + 10.16:.2f}", f"{22.0 + 14.0 * row:.2f}"
%>\
/* ${module}.cpp

${" ".join(str(e.meta['desc']).split())}

Author: ${e.meta['author']}
Repo: ${e.meta['repo']}
% if d:

DSP: compiled by gen-dsp from ${d.source} into ${d.prefix}.c. Edit the graph and
regenerate rather than editing ${d.prefix}.c.
% endif

*/

#include "plugin.hpp"
% if d:
#include "${d.prefix}.h"
% endif


struct ${module} : Module {
    enum ParamId {
% for p in e.params:
        ${up(p.name)}_PARAM,
% endfor
        PARAMS_LEN
    };
    enum InputId {
% for p in e.params:
% if p.has_inlet:
        ${up(p.name)}_CV_INPUT,
% endif
% endfor
% for i in range(1, n_in + 1):
        IN_${i}_INPUT,
% endfor
        INPUTS_LEN
    };
    enum OutputId {
% for i in range(1, n_out + 1):
        OUT_${i}_OUTPUT,
% endfor
        OUTPUTS_LEN
    };
    enum LightId {
        LIGHTS_LEN
    };

    ${module}()
    {
        config(PARAMS_LEN, INPUTS_LEN, OUTPUTS_LEN, LIGHTS_LEN);
% for p in e.params:
        configParam(${up(p.name)}_PARAM, ${repr(float(p.min))}f, ${repr(float(p.max))}f, ${repr(float(p.initial))}f, ${c_string(p.name)});
% if p.has_inlet:
        configInput(${up(p.name)}_CV_INPUT, ${c_string(p.name + " CV")});
% endif
% endfor
% for i in range(1, n_in + 1):
        configInput(IN_${i}_INPUT, "In ${i}");
% endfor
% for i in range(1, n_out + 1):
        configOutput(OUT_${i}_OUTPUT, "Out ${i}");
% endfor
    }
% if d:

    ${d.state_type} *dsp = nullptr;
    float sr = 0.f;

    ~${module}()
    {
        if (dsp)
            ${d.prefix}_destroy(dsp);
    }

    void onReset(const ResetEvent &e) override
    {
        Module::onReset(e);
        if (dsp)
            ${d.prefix}_reset(dsp);
    }

    // The graph is mono: it reads channel 0 of each input and writes one channel.
    void process(const ProcessArgs &args) override
    {
        // Allocates on the audio thread, but only on first use and on a sample-rate change.
        if (!dsp || args.sampleRate != sr) {
            if (dsp)
                ${d.prefix}_destroy(dsp);
            dsp = ${d.prefix}_create(args.sampleRate);
            sr = args.sampleRate;
            if (!dsp)
                return;
        }
% for i, p in enumerate(e.params):
        ${d.prefix}_set_param(dsp, ${i}, ${value(p)});
% endfor

        // Rack audio is +-5 V; the graph works on +-1.
% if n_in:
        float in[${n_in}];
        float *ins[${n_in}];
% for i in range(n_in):
        in[${i}] = inputs[IN_${i + 1}_INPUT].getVoltage() / 5.f;
        ins[${i}] = &in[${i}];
% endfor
% endif
        float out[${n_out}];
        float *outs[${n_out}];
        for (int i = 0; i < ${n_out}; i++)
            outs[i] = &out[i];
        ${d.prefix}_perform(dsp, ${"ins" if n_in else "nullptr"}, outs, 1);
% for i in range(n_out):
        outputs[OUT_${i + 1}_OUTPUT].setChannels(1);
        outputs[OUT_${i + 1}_OUTPUT].setVoltage(5.f * out[${i}]);
% endfor
    }
% else:

    void process(const ProcessArgs &args) override
    {
% for p in e.params:
        float ${p.name} = ${value(p)};
        (void)${p.name};
% endfor

        // TODO: DSP. Pass-through until implemented.
% for i in range(1, n_in + 1):
        {
            int channels = inputs[IN_${i}_INPUT].getChannels();
            outputs[OUT_${i}_OUTPUT].setChannels(channels);
            for (int c = 0; c < channels; c++)
                outputs[OUT_${i}_OUTPUT].setVoltage(inputs[IN_${i}_INPUT].getVoltage(c), c);
        }
% endfor
    }
% endif
};


struct ${module}Widget : ModuleWidget {
    ${module}Widget(${module} *module)
    {
        setModule(module);
        setPanel(createPanel(asset::plugin(pluginInstance, "res/${module}.svg")));

        addChild(createWidget<ScrewSilver>(Vec(RACK_GRID_WIDTH, 0)));
        addChild(createWidget<ScrewSilver>(Vec(box.size.x - 2 * RACK_GRID_WIDTH, 0)));
        addChild(createWidget<ScrewSilver>(Vec(RACK_GRID_WIDTH, RACK_GRID_HEIGHT - RACK_GRID_WIDTH)));
        addChild(createWidget<ScrewSilver>(Vec(box.size.x - 2 * RACK_GRID_WIDTH, RACK_GRID_HEIGHT - RACK_GRID_WIDTH)));

% for r, (kind, item) in enumerate(rows):
<% x, x2, y = pos(r) %>\
% if kind == "param":
        addParam(createParamCentered<RoundBlackKnob>(mm2px(Vec(${x}, ${y})), module, ${module}::${up(item.name)}_PARAM));
% if item.has_inlet:
        addInput(createInputCentered<PJ301MPort>(mm2px(Vec(${x2}, ${y})), module, ${module}::${up(item.name)}_CV_INPUT));
% endif
% else:
% if item <= n_in:
        addInput(createInputCentered<PJ301MPort>(mm2px(Vec(${x}, ${y})), module, ${module}::IN_${item}_INPUT));
% endif
% if item <= n_out:
        addOutput(createOutputCentered<PJ301MPort>(mm2px(Vec(${x2}, ${y})), module, ${module}::OUT_${item}_OUTPUT));
% endif
% endif
% endfor
    }
};


Model *model${module} = createModel<${module}, ${module}Widget>("${module}");
