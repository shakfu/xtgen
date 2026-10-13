# Path to the Rack SDK; override with `make RACK_DIR=...`.
RACK_DIR ?= ../..

SOURCES += $(wildcard src/*.cpp)
# C sources, such as a gen-dsp graph's <name>_dsp.c
SOURCES += $(wildcard src/*.c)

DISTRIBUTABLES += res
DISTRIBUTABLES += $(wildcard LICENSE*)

include $(RACK_DIR)/plugin.mk
