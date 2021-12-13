# Makefile for ${e.name}

lib.name = ${e.name}

class.sources = ${e.name}.c myclass2.c

datafiles = ${e.name}-help.pd README.txt LICENSE.txt

PDLIBBUILDER_DIR=pd-lib-builder
include $(PDLIBBUILDER_DIR)/Makefile.pdlibbuilder

 
