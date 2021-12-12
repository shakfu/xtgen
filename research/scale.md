# clamp and scaling funcitons

## clamp

```python
def clamp(n, smallest, largest):
    return max(smallest, min(n, largest))
```



## log scaling

see: https://stackoverflow.com/questions/19472747/convert-linear-scale-to-logarithmic

```
Given a linear scale whose values range from x0 to x1, and a logarithmic scale whose values range from y0 to y1, the mapping between x and y (in either direction) is given by the relationship shown in equation 1:

 x - x0    log(y) - log(y0)
------- = -----------------      (1)
x1 - x0   log(y1) - log(y0)

```
where
```
x1 > x0
x0 <= x <= x1

y1 > y0
y0 <= y <= y1
y1/y0 != 1   ; i.e., log(y1) - log(y0) != 0
y0, y1, y != 0
```

## linear scaling

https://stackoverflow.com/questions/5294955/how-to-scale-down-a-range-of-numbers-with-a-known-min-and-max-value


```
       (b-a)(x - min)
f(x) = --------------  + a
          max - min
```

```python
def f(x, a, b, _min, _max):
    return ((b-a)*(x - _min)/(_max - _min)) + a

def get_scale_func(a, b, _min, _max):
    def _func(x):
        return ((b-a)*(x - _min)/(_max - _min)) + a
    return _func


```


