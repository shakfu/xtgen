<%
from xtgen.models import c_string
module = e.name[0].upper() + e.name[1:]
n = e.n_channels
up = lambda s: s.upper()
# Layout: one row per param (knob, CV input) then per channel (in, out).
# Columns of 7 rows; each column pair is 4 HP wide.
rows = [("param", p) for p in e.params] + [("audio", i) for i in range(1, n + 1)]
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

*/

#include "plugin.hpp"


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
% for i in range(1, n + 1):
        IN_${i}_INPUT,
% endfor
        INPUTS_LEN
    };
    enum OutputId {
% for i in range(1, n + 1):
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
% for i in range(1, n + 1):
        configInput(IN_${i}_INPUT, "In ${i}");
        configOutput(OUT_${i}_OUTPUT, "Out ${i}");
% endfor
    }

    void process(const ProcessArgs &args) override
    {
% for p in e.params:
        float ${p.name} = params[${up(p.name)}_PARAM].getValue();
% if p.has_inlet:
        // 10 V of CV spans the full parameter range.
        ${p.name} = clamp(${p.name} + inputs[${up(p.name)}_CV_INPUT].getVoltage() / 10.f * ${repr(float(p.max - p.min))}f,
                ${repr(float(p.min))}f, ${repr(float(p.max))}f);
% endif
        (void)${p.name};
% endfor

        // TODO: DSP. Pass-through until implemented.
% for i in range(1, n + 1):
        {
            int channels = inputs[IN_${i}_INPUT].getChannels();
            outputs[OUT_${i}_OUTPUT].setChannels(channels);
            for (int c = 0; c < channels; c++)
                outputs[OUT_${i}_OUTPUT].setVoltage(inputs[IN_${i}_INPUT].getVoltage(c), c);
        }
% endfor
    }
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
        addInput(createInputCentered<PJ301MPort>(mm2px(Vec(${x}, ${y})), module, ${module}::IN_${item}_INPUT));
        addOutput(createOutputCentered<PJ301MPort>(mm2px(Vec(${x2}, ${y})), module, ${module}::OUT_${item}_OUTPUT));
% endif
% endfor
    }
};


Model *model${module} = createModel<${module}, ${module}Widget>("${module}");
