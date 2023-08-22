# Makefile for ${e.name}

lib.name = ${e.name}

class.sources = ${e.name}.c

datafiles = ${e.name}-help.pd README.md

suppress-wunused = true

include Makefile.pdlibbuilder

 
