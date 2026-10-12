<% module = e.name[0].upper() + e.name[1:] %>\
#include "plugin.hpp"

Plugin *pluginInstance;

void init(Plugin *p)
{
    pluginInstance = p;
    p->addModel(model${module});
}
