# PD File Format


The PD fileformat is a genuine custom textfile format, not to be confused with XML. It consists of one ore more records.

Each record may cover multiply lines but they all have the same syntax:

```
#[data];\r\n

where
	[data] holds the record data, 
	\r represents an ASCII code 13 carriage return character, and 
	\n represents an ASCII code 10 line-feed character.
```

For example:

```
#N canvas 394 140 450 300 12;
#X msg 139 65 hello;
#X obj 139 113 osc~;
#X msg 209 66 bye;
#X connect 0 0 1 0;
#X connect 2 0 1 1;

```

canvas is the container object

```
#N canvas <x_pos> <y_pos> <x_size> <y_size> <name> <open_on_load>
```

format:

```
#<chunk-type> <element-type> <x> <y> <label>
#X obj <x> <y> <label>
#X floatatom <x> <y> <width> <lower> <upper> <label-pos> <label> <receive> <send>
```

where `<chunk-type>` is one of:
	"X" for an object, 
	"N" for a new window, and 
	"A" for array data.

for connections

```
#X connect <obj-from-id> <obj-from-outlet-n> <obj-to-id> <obj-to-inlet>

OR

#X connect [source]? [outlet_number]? [sink]? [inlet_number]?;\r\n
```

Note that object ids and outlet/inlet numbers are 0-indexed.


Let us take a closer look on the records contents.
Each record consists of a chunk type, element type and optional parameters like this: #[chunk_type]? [element_type]? [p1]? [p2]? [p3]? [...]?;\r\n


```

## Key Functions

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
