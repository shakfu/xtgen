"""pd.py

A pure python to pd transpiler.

For examples:

>>> p = Patch('demo.pd')
>>> osc = p.add_obj('osc~ 440')
>>> mult = p.add_obj('~*')
>>> dac = p.add_obj('dac~')
>>> p.link(osc, mult)
>>> p.link(mult, dac)
>>> p.save()

OR

>>> p = Patch('demo.pd')
>>> osc = p.add('osc~ 440')
>>> mult = p.add('~*')
>>> dac = p.add('dac~')
>>> p.link(osc, mult)
>>> p.link(mult, dac)
>>> p.save()

"""

class PdObject:
    def __repr__(self):
        return f"<{self.__class__.__name__}: '{self}'>"

    def __str__(self):
        return " ".join(str(i) for i in self.property_list)



class Canvas(PdObject):
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


class Msg(PdObject):
    """pd message object

    #X msg <x_pos> <y_pos> <p1> <p2> <p3> <...>
    """

    DEFAULT_X_POS = 20
    DEFAULT_Y_POS = 20

    def __init__(self, content, x_pos=None, y_pos=None):
        self.chunk_type = "#X"
        self.type = "msg"
        self.content = content
        self.x_pos = x_pos if x_pos else self.DEFAULT_X_POS
        self.y_pos = y_pos if y_pos else self.DEFAULT_Y_POS


    @property
    def property_list(self):
        return [
            self.chunk_type,
            self.type,
            self.x_pos,
            self.y_pos,
        ] + self.content.split()


class Obj(PdObject):
    """pd message object

    #X obj <x_pos> <y_pos> <name> <p1> <p2> <p3> <...>
    """

    DEFAULT_X_POS = 20
    DEFAULT_Y_POS = 20

    def __init__(self, content, x_pos=None, y_pos=None):
        self.chunk_type = "#X"
        self.type = "obj"
        self.name, *self.params = content.split()
        self.x_pos = x_pos if x_pos else self.DEFAULT_X_POS
        self.y_pos = y_pos if y_pos else self.DEFAULT_Y_POS


    @property
    def property_list(self):
        return [
            self.chunk_type,
            self.type,
            self.x_pos,
            self.y_pos,
            self.name,
        ] + self.params


c = Canvas()
s = Subcanvas()
m = Msg("nice one please")
o = Obj("osc~ 440")