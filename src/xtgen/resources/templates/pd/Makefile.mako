# Makefile for ${e.name}

lib.name = ${e.name}

class.sources = ${fullname}.c

# no help patch is generated; install one only if the user adds it
datafiles = $(wildcard ${fullname}-help.pd) README.md

suppress-wunused = true

include Makefile.pdlibbuilder

 
