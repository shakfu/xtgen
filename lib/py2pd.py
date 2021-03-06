"""pd.py

A pure python to pd transpiler.

"""

class Mixin:
    def __repr__(self):
        return f"<{self.__class__.__name__}: '{self}'>"


class canvas(Mixin):
    """Top-level container object in Puredata.

    #N canvas <x_pos> <y_pos> <x_size> <y_size> <font_size>
    #N canvas 394 140 445 318 12;
    """

    DEFAULT_X_POS = 394
    DEFAULT_Y_POS = 140
    DEFAULT_X_SIZE = 445
    DEFAULT_Y_SIZE = 318
    DEFAULT_FONT_SIZE = 12

    def __init__(self, x_pos=None, y_pos=None, x_size=None, y_size=None, font_size=None):
        self.chunk_type = "#N"
        self.type = "canvas"
        self.x_pos = x_pos if x_pos else self.DEFAULT_X_POS
        self.y_pos = y_pos if y_pos else self.DEFAULT_Y_POS
        self.x_size = x_size if x_size else self.DEFAULT_X_SIZE
        self.y_size = x_size if y_size else self.DEFAULT_Y_SIZE
        self.font_size = font_size if font_size else self.DEFAULT_FONT_SIZE


    @property
    def property_list(self):
        return [
            self.chunk_type,
            self.type,
            self.x_pos,
            self.y_pos,
            self.x_size,
            self.y_size,
            self.font_size,
        ]


class subcanvas(canvas):
    """child container object in Puredata.

    #N canvas <x_pos> <y_pos> <x_size> <y_size> <name> <open_on_load>
    #N canvas 401 372 450 300 inside 1
    """

    DEFAULT_OPEN_ON_LOAD = 1

    def __init__(self, name='', x_pos=None, y_pos=None, x_size=None, y_size=None, font_size=None, open_on_load=None):
        super().__init__(x_pos, y_pos, x_size, y_size, font_size)
        self.name = name
        self.open_on_load = open_on_load if open_on_load else self.DEFAULT_OPEN_ON_LOAD

    @property
    def property_list(self):
        return [
            self.chunk_type,
            self.type,
            self.x_pos,
            self.y_pos,
            self.x_size,
            self.y_size,
            self.name,
            self.open_on_load,
        ]




def pd_record(chunk_type: str, element_type: str, *args, x: int = 0, y: int = 0):
    """returns a str representation of a pure-data record in the pd file format"""
    assert chunk_type in ['X', 'N', 'A']
    params = " ".join(str(i) for i in args)
    return f'#{chunk_type} {element_type} {x} {y} {params};'



class PdObject:
    """
    General Pure-Data object class

    Can represent a pd object

    >>> p = PdObject('X', 'obj', 'osc~', 440, x=40, y=80)
    >>> str(p)
    '#X obj 40 80 osc~ 440;'

    """
    OBJ_COUNTER = 0
    DEFAULT_X_POS = 20
    DEFAULT_Y_POS = 20

    def __init__(self, chunk_type, element_type, *args, **kwds):
        PdObject.OBJ_COUNTER += 1
        assert chunk_type in ['X', 'N', 'A']
        self.chunk_type = chunk_type
        self.element_type = element_type
        self.args = args
        self.x = kwds.get('x', self.DEFAULT_X_POS)
        self.y = kwds.get('y', self.DEFAULT_Y_POS)

    def __str__(self):
        params = " ".join(str(i) for i in self.args)
        return f'#{self.chunk_type} {self.element_type} {self.x} {self.y} {params};'

    def __repr__(self):
        return f"<{self.__class__.__name__}: '{self}'>"

    @property
    def id(self):
        return PdObject.OBJ_COUNTER



class msg(PdObject):
    """pd message object

    #X msg <x_pos> <y_pos> <p1> <p2> <p3> <...>

    >>> m = msg("freq", 100)
    >>> str(m)
    '#X msg 20 30 freq 100;'

    """

    DEFAULT_X_POS = 20
    DEFAULT_Y_POS = 30

    def __init__(self, *args, **kwds):
        super().__init__("X", "msg", *args, **kwds)



class obj(PdObject):
    """pd message object

    #X obj <x_pos> <y_pos> <name> <p1> <p2> <p3> <...>

    >>> o = obj('osc~', 440)
    >>> str(o)
    '#X obj 20 40 osc~ 440;'

    """

    DEFAULT_X_POS = 20
    DEFAULT_Y_POS = 40

    def __init__(self, name, *args, **kwds):
        args = (name,) + args
        super().__init__("X", "obj", *args, **kwds)


class floatatom(PdObject):
    """defines a pd number box

    #X floatatom [x_pos] [y_pos] [width] [lower_limit] [upper_limit] [label_pos] [label] [receive] [send] [font_size];
    #X floatatom 166     41      5       0             500           0           freq    -         -      0;
    #X floatatom 152     75      5       0             0             0           -       -         -      0;

    >>> f = floatatom('freq', 10, 100)
    >>> str(f)
    '#X floatatom 20 40 5 10 100 0 freq - - 0;'

    """
    DEFAULT_X_POS = 20
    DEFAULT_Y_POS = 40

    def __init__(self, label='-', lower_limit=0, upper_limit=0,
            width=5, label_pos=0, receive='-', send='-', font_size=0, **kwds):
        args = (width, lower_limit, upper_limit, label_pos, label, receive, send, font_size)
        super().__init__("X", "floatatom", *args, **kwds)


class bng(PdObject):
    """defines a bang

    #X obj [x_pos] [y_pos] bng [size] [hold] [interrupt] [init] [send] [receive] [label] [x_offset] [y_offset] [font] [fontsize] [bg_color] [fg_color] [label_color] ;
    #X obj 181     119     bng 15     250    50          0       empty  empty    empty   17         7      0      10          #fcfcfc   #000000    #000000;


    """

if __name__ == "__main__":
    import doctest
    doctest.testmod()

    # c = canvas()
    # s = subcanvas()
    # m = msg('freq', 100)
    # o = obj('osc~', 440)
    # f = floatatom('freq', 10, 100)


