"""
EXTERN t_inlet *inlet_new(t_object *owner, t_pd *dest, t_symbol *s1,
    t_symbol *s2);
EXTERN t_inlet *pointerinlet_new(t_object *owner, t_gpointer *gp);
EXTERN t_inlet *floatinlet_new(t_object *owner, t_float *fp);
EXTERN t_inlet *symbolinlet_new(t_object *owner, t_symbol **sp);
EXTERN t_inlet *signalinlet_new(t_object *owner, t_float f);
EXTERN void inlet_free(t_inlet *x);

EXTERN t_outlet *outlet_new(t_object *owner, t_symbol *s);
EXTERN void outlet_bang(t_outlet *x);
EXTERN void outlet_pointer(t_outlet *x, t_gpointer *gp);
EXTERN void outlet_float(t_outlet *x, t_float f);
EXTERN void outlet_symbol(t_outlet *x, t_symbol *s);
EXTERN void outlet_list(t_outlet *x, t_symbol *s, int argc, t_atom *argv);
EXTERN void outlet_anything(t_outlet *x, t_symbol *s, int argc, t_atom *argv);

"""


class Type:
    VALID_TYPES = []

    def __init__(self, name):
        assert name in self.VALID_TYPES
        self.name = name

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<{self.__class__.__name__}: '{self.name}'>"


class ScalarType(Type):
    VALID_TYPES = ['bang', 'float', 'symbol', 'pointer', 'signal']

    @property
    def c_type(self):
        return f't_{self.name}'

    @property
    def lookup_address(self):
        return f'&s_{self.name}'

    @property
    def lookup_routine(self):
        return f'gensym("{self.name}")'

    @property
    def type_method_arg(self):
        return {
            'bang' : '',
            'float': 't_floatarg f',
            'int': 't_floatarg f',
            'symbol': 't_symbol *s',
            'pointer': 't_gpointer *pt',
        }[self.name]


class CompoundType(Type):
    VALID_TYPES = ['list', 'anything']

    @property
    def c_type(self):
        assert self.name != 'anything' # doesn't exist for 'anything'
        return f't_{self.name}'

    @property
    def lookup_address(self):
        return f'&s_{self.name}'

    @property
    def lookup_routine(self):
        return f'gensym("{self.name}")'

    @property
    def type_method_arg(self):
        return {
            'list': 't_symbol *s, int argc, t_atom *argv',
            'anything': 't_symbol *s, int argc, t_atom *argv',
        }[self.name]

f = ScalarType('float')
l = CompoundType('list')


