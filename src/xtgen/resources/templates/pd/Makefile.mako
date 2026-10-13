# Makefile for ${e.name}

lib.name = ${e.name}

class.sources = ${fullname}.c
% if e.dsp:
${fullname}.class.sources += ${e.dsp.prefix}.c
% endif

# no help patch is generated; install one only if the user adds it
datafiles = $(wildcard ${fullname}-help.pd) README.md

suppress-wunused = true

include Makefile.pdlibbuilder

 
