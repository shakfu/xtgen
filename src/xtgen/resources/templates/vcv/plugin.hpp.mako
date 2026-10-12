<% module = e.name[0].upper() + e.name[1:] %>\
#pragma once
#include <rack.hpp>

using namespace rack;

extern Plugin *pluginInstance;

extern Model *model${module};
