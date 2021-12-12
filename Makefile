# Makefile for counter

lib.name = counter

class.sources = counter.c

datafiles = 

PDLIBBUILDER_DIR=pd-lib-builder
include $(PDLIBBUILDER_DIR)/Makefile.pdlibbuilder

