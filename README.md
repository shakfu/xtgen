# xtgen

A tool to generate skeleton puredata and Max/MSP external files.

Has two intended purposes:

1. Generate skeleton puredata and Max/MSP external code

2. Generate related puredata and Max/MSP patch code

The idea is that an external is generically specified in a `<name>.yml` file, and then this file is used to generate one of several target formats {Max, PD, Hybrid, ...}

The external model is roughly sketched in the `model.py` file.


## Requirements

```bash
pip3 install mako
```


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

### Templates

- [ ] create hybrid dual Max/PD template
- [ ] create hybrid dual Max/PD template for audio

### Support

- [ ] Add `xtgen.h` for common helper functions

### Generator

- [ ] create/generate inlets
- [ ] create/generate outlets
- [ ] params: should be either 'anything' or alternatives.
- [ ] populate variables (switch statement)
- [ ] fixed inconsistencies in `external.yml`, especially `arg` vs `param` configuration
- [ ] rulecheck: `anything` method vs. others (especially list), can be redundant.

### Puredata

- [ ] generate pd help code
- [ ] generate pd project
- [ ] generate signal-based external
- [ ] add utility library for builtin scaling, clamp, ..., dsp functions?
