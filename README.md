# py2pd

A tool to generate skeleton puredata external files.

Has two intended purposes:

- [ ] generate skeleton puredata external code
- [ ] generate related puredata patch code


## TODO

- [ ] create/generate inlets
- [ ] create/generate outlets
- [ ] params: should be either 'anything' or alternatives.
- [ ] populate variables (switch statement)
- [ ] fixed inconsistencies in `external.yml`, especiall `arg` vs `param` configuration
- [ ] rulecheck: `anything` method vs. others (especially list), can be redundant.
- [ ] generate pd help code
- [ ] generate pd project
- [ ] generate signal-based external
- [ ] add utility library for builtin scaling, clamp, ..., dsp functions?


## Notes

```c
// key functions for sending data to objects
void pd_bang(t_pd *x);
void pd_pointer(t_pd *x, t_gpointer *gp);
void pd_float(t_pd *x, t_float f);
void pd_symbol(t_pd *x, t_symbol *s);
void pd_list(t_pd *x, t_symbol *s, int argc, t_atom *argv);
void pd_anything(t_pd *x, t_symbol *s, int argc, t_atom *argv);

// type conversions
t_float *value_get(t_symbol *s);
void value_release(t_symbol *s);
int value_getfloat(t_symbol *s, t_float *f);
int value_setfloat(t_symbol *s, t_float f);
void atom_string(const t_atom *a, char *buf, unsigned int bufsize);


// send tcl commands to gui (TK)
void sys_vgui(const char *fmt, ...);
void sys_gui(const char *s);
```