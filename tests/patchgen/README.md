# py2pd



```
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
```