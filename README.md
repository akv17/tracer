# About
a tool for runtime tracing of a particular value as any function argument.

# Example
- this is an extremely useful module `foo.py`. 
```
def foo(val):
    return -val


def bar(val, pw=2):
    return val ** pw


def baz(val):
    val = foo(val)
    val = bar(val)
    return val
```
- this is an extremely useful tracing of integer value `2` when calling `foo.baz(x=-2)`.
```
>>> python cli.py -e "foo.baz(val=-2)" -t 2 --ttype int
{
  "2": [
    {
      "obj_name": "foo.bar",
      "args_spec": "args",
      "arg_id": 0,
      "target": 2,
      "value": 2,
      "matcher_type": "<class 'tracer.EqualsMatcher'>",
      "timestamp": "2020-07-19 02:13:38.241883",
      "arg_type": "<class 'int'>",
      "stack": null
    }
  ]
}
```