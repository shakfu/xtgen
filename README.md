# xtgen

A tool to generate skeleton puredata and Max/MSP external files.

Has two intended purposes:

- [ ] generate skeleton puredata and Max/MSP external code
- [ ] generate related puredata and Max/MSP patch code

## Status

Can generate a basic external skeleton from a `.yml` specification file (see `counter.yml`)

Run the following for a demo

```bash
python3 xtgen.py
```

A pd external project will be created in `output/counter` which should be compilable:

```bash
make -C output/counter
````


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
