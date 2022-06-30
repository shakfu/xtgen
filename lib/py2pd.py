"""pd.py

A pure python to pd transpiler.

The following pd file

#N canvas 530 323 450 300 12;
#X obj 166 80 osc~ 440;
#X floatatom 166 41 5 0 500 0 freq - - 0;
#X obj 166 148 *~ 0.1;
#X obj 166 226 dac~;
#X connect 0 0 2 0;
#X connect 1 0 0 0;
#X connect 2 0 3 0;
#X connect 2 0 3 1;

is constructed by:

>>> p = Patch('demo.pd')
>>> osc = p.add_obj('osc~ 440')
>>> freq = p.add_number('freq', min=0, max=500)
>>> mult = p.add_obj('~*', 0.1)
>>> dac = p.add_obj('dac~')
>>> p.link(freq, osc)
>>> p.link(osc, mult)
>>> p.link(mult, dac)
>>> p.link(mult, dac)
>>> p.save()

"""

class Mixin:
    def __repr__(self):
        return f"<{self.__class__.__name__}: '{self}'>"


class Canvas(Mixin):
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


class Subcanvas(Canvas):
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



class Msg(PdObject):
    """pd message object

    #X msg <x_pos> <y_pos> <p1> <p2> <p3> <...>

    >>> m = Msg("freq", 100)
    >>> str(m)
    '#X msg 20 30 freq 100;'

    """

    DEFAULT_X_POS = 20
    DEFAULT_Y_POS = 30

    def __init__(self, *args, **kwds):
        super().__init__("X", "msg", *args, **kwds)



class Obj(PdObject):
    """pd message object

    #X obj <x_pos> <y_pos> <name> <p1> <p2> <p3> <...>

    >>> o = Obj('osc~', 440)
    >>> str(o)
    '#X obj 20 40 osc~ 440;'

    """

    DEFAULT_X_POS = 20
    DEFAULT_Y_POS = 40

    def __init__(self, name, *args, **kwds):
        args = (name,) + args
        super().__init__("X", "obj", *args, **kwds)


if __name__ == '__main__':
    c = Canvas()
    s = Subcanvas()
    m = Msg("freq", 100)
    o = Obj('osc~', 440)


